import networking as nw
import msgcreation as mc
from qdrecognizer import QDRecognizer
from enum import Enum
import random
import logging
import threading
import time


class GameAlreadyStartedException(Exception):
    pass


class StartedNotByOwnerException(Exception):
    pass


class NotEnaughPlayersException(Exception):
    pass


class UsernameTakenException(Exception):
    pass


class StateErrorException(Exception):
    pass


class WordSelectionRespNotFromArtistException(Exception):
    pass


class RoomState(Enum):
    PREGAME = 0
    STARTING_GAME = 1
    WORD_SELECTION = 2
    DRAWING = 3
    POSTGAME = 4


class RoundTimeController:
    def __init__(self, room, round_time):
        self._round_finished = False
        self._round_time = round_time
        self._room = room
        self._timer = None
        self._start_time_stamp = None
        self._drawing_queue = None
        self._current_word = None

    def finish_round(self):
        end_time_stamp = time.time()
        self._round_finished = True
        return end_time_stamp - self._start_time_stamp

    def start_round(self):
        self._timer = threading.Timer(self._round_time / 2, self._half_time_passed)
        self._timer.start()
        self._start_time_stamp = time.time()

    def _half_time_passed(self):
        if not self._round_finished:
            half_time_notification = mc.build_chat_msg_bc(
                'SERVER',
                'Half time - {} seconds left'.format(str(self._round_time / 2))
            )
            
            with self._room.lock:
                self._room.broadcast_message(half_time_notification)
                self._room.send_hint(2)

            self._timer = threading.Timer(self._round_time / 2, self._full_time_passed)
            self._timer.start()

    def _full_time_passed(self):
        if not self._round_finished:
            with self._room.lock:
                self._room.finish_round_after_timeout()


def replace_at_index(s, newstring, index, nofail=False):
    if not nofail and index not in range(len(s)):
        raise ValueError("index outside given string")

    if index < 0:
        return newstring + s
    if index > len(s):
        return s + newstring

    return s[:index] + newstring + s[index + 1:]


class Room:
    def __init__(self, owner_name, owner_connection, room_code, words, score_limit=500, round_time=60.0):
        self._owner = owner_name
        self._joined_clients = {owner_name : owner_connection}
        self._score_awarded = {owner_name: 0, 'BOT': 0}
        self._game_bot = QDRecognizer()
        self._room_code = room_code
        self._state = RoomState.PREGAME
        self.lock = threading.Lock()
        self._round_time = round_time
        self._words = words
        self._score_limit = score_limit
        logging.info('[ROOM ID: {}] Room created'.format(room_code))

    def is_started(self):
        return self._state not in [RoomState.PREGAME, RoomState.POSTGAME]

    def get_room_info(self):
        info = {
            'owner_name': self._owner,
            'num_of_players': len(self._joined_clients),
            'room_code': self._room_code
        }
        return info

    def num_of_members(self):
        return len(self._joined_clients)

    def add_client(self, user_name, user_conn):
        if self._state not in [RoomState.PREGAME, RoomState.POSTGAME]:
            raise GameAlreadyStartedException()
        self._joined_clients[user_name] = user_conn
        self._score_awarded[user_name] = 0
        
    def _choice_new_owner(self):
        playser_list = list(self._joined_clients.keys())
        new_owner = random.choice(playser_list)
        self._owner = new_owner
        
        owner_changed_bc = {'msg_name': 'OwnerChangedBc', 'owner': new_owner}
        self.broadcast_message(owner_changed_bc)

    def _finish_game_with_info(self, info='Game finished!'):
        self._round_time_controller.finish_round()
        game_interrupted_notification = mc.build_chat_msg_bc('SERVER', info)

        self.broadcast_message(game_interrupted_notification)
        self._finish_game()

    def _remove_user_from_drawing_queue(self, user_name):
        self._drawing_queue.remove(user_name)
        if user_name == self._artist:
            self._round_time_controller.finish_round()
            self._game_bot.clear_drawing()
            round_finished_notification = mc.build_chat_msg_bc(
                    'SERVER',
                    'Round interrupted - artist left the game - word: {}'.format(self._current_word))

            self.broadcast_message(round_finished_notification)
            self._select_artist_and_send_words()

    def remove_client_by_name_if_exists(self, user_name):
        try:
            del self._joined_clients[user_name]
            del self._score_awarded[user_name]

        except KeyError:
            return False

        leave_notification = mc.build_leave_notification(user_name)
        self.broadcast_message(leave_notification)

        update_score_board_bc = {'msg_name': 'UpdateScoreboardBc', 'users_in_room': self._score_awarded}
        self.broadcast_message(update_score_board_bc)

        logging.info('[ROOM ID: {}] Removed user {}'.format(self._room_code, user_name))

        if user_name == self._owner:
            self._choice_new_owner()

        if self.num_of_members() < 2:
            self._finish_game_with_info('Game Interrupted - less than {} human players left!'.format(2))
            
        if self._state not in [RoomState.PREGAME, RoomState.POSTGAME]:
            self._remove_user_from_drawing_queue(user_name)

        return True

    def remove_client_by_connection_if_exists(self, user_conn):
        for user_name, value in self._joined_clients.items():
            if value == user_conn:
                removed = self.remove_client_by_name_if_exists(user_name)
                return removed

    def broadcast_message(self, msg):
        for client in self._joined_clients.items():
            try:
                client[1].send(msg)
            except:
                logging.warn('[ROOM ID: {}] Unable to send message {} to {}!'
                             .format(self._room_code, msg['msg_name'], client[0]))

    def start_game(self, user_name):
        if user_name != self._owner:
            raise StartedNotByOwnerException()

        if self._state not in [RoomState.PREGAME, RoomState.POSTGAME]:
            raise StateErrorException()

        if self.num_of_members() < 2:
            raise NotEnaughPlayersException()

        logging.info('[ROOM ID: {}] Attempting to start a game!'.format(self._room_code))
        self._state = RoomState.STARTING_GAME

        self._score_awarded = {player[0]: 0 for player in self._joined_clients.items()}
        self._score_awarded['BOT'] = 0

        self._drawing_queue = list(self._joined_clients.keys())
        random.shuffle(self._drawing_queue)

    def finish_round_after_timeout(self):
        round_finished_notification = mc.build_chat_msg_bc(
                'SERVER',
                'Time is over - word: {}'.format(self._current_word))
        
        self._game_bot.clear_drawing()
        self.broadcast_message(round_finished_notification)
        self._select_artist_and_send_words()
    
    def _enter_word_selection_state(self):
        logging.info('[ROOM ID: {}] Entering WORD_SELECTION state!'.format(self._room_code))
        self._state = RoomState.WORD_SELECTION

        words_to_select = random.sample(self._words, 3)

        self._current_word = None
        self._artist = self._drawing_queue[0]
        del self._drawing_queue[0]
        self._drawing_queue.append(self._artist)
        
        logging.debug('[ROOM ID: {}] Word draw result for artist {} : {}!'
                      .format(self._room_code, self._artist, words_to_select))

        self._round_time_controller = RoundTimeController(self, self._round_time)
        self._round_time_controller.start_round()

        return words_to_select
    
    def _select_artist_and_send_words(self):
        self._game_bot.clear_drawing()
        words_to_select = self._enter_word_selection_state()
        artist_pick_bc = {
            'msg_name': 'ArtistPickBc',
            'artist': self._artist
        }
        self.broadcast_message(artist_pick_bc)
        self.send_words_to_select_to_artist(words_to_select)

    def _finish_game(self):
        logging.info('[ROOM ID: {}] Finishing game. Scoreboard: {}'.format(self._room_code, self._score_awarded))
        self._state = RoomState.POSTGAME
        msg_bc = mc.build_game_finished_bc()
        self.broadcast_message(msg_bc)

    def _announce_word_guessed(self, msg):
        word_guessed_bc = mc.build_word_guessed_bc(msg['user_name'],
                                                   self._current_word,
                                                   self._score_awarded)
        
        self.broadcast_message(word_guessed_bc)
        if max(list(self._score_awarded.values())) >= self._score_limit:
            self._finish_game()
        else:
            self._select_artist_and_send_words()

    def _recalculate_score(self, user_name, time_passed):
        try:
            self._score_awarded[user_name] += 50
            self._score_awarded[self._artist] += round(self._round_time - time_passed)
        except:
            logging.error('[ROOM ID: {}] Unknown error occurred when recalculating scoreboard'.format(self._room_code))

    def handle_ChatMessageReq(self, msg, sender_conn):
        if self._state == RoomState.DRAWING:
            if msg['user_name'] == self._artist:
                artist_info = mc.build_chat_msg_bc(
                    'SERVER',
                    'As an artist, you can\'t use chat!')
                sender_conn.send(artist_info)

            elif msg['message'] == self._current_word:
                time_passed = self._round_time_controller.finish_round()
                self._recalculate_score(msg['user_name'], time_passed)
                self._announce_word_guessed(msg)

            else:
                chat_msg = mc.build_chat_msg_bc(msg['user_name'], msg['message'])
                self.broadcast_message(chat_msg)

        else:
            chat_msg = mc.build_chat_msg_bc(msg['user_name'], msg['message'])
            self.broadcast_message(chat_msg)

    def handle_JoinRoomReq(self, msg, sender_conn):
        try:
            if msg['user_name'] in self._joined_clients:
                raise UsernameTakenException()

            if msg['user_name'] == 'BOT':
                raise UsernameTakenException()

            self.add_client(msg['user_name'], sender_conn)
            resp = mc.build_ok_join_room_resp(self._owner, self._score_awarded)
            sender_conn.send(resp)
            join_notification = mc.build_join_notification(msg['user_name'])
            self.broadcast_message(join_notification)

            update_score_board_bc = {'msg_name': 'UpdateScoreboardBc', 'users_in_room': self._score_awarded}
            self.broadcast_message(update_score_board_bc)

            logging.debug('[ROOM ID: {}] User {} joined'.format(self._room_code, msg['user_name']))

        except GameAlreadyStartedException:
            info = 'Game already started!'
            nw.send_NOT_OK_JoinRoomResp_with_info(sender_conn, info)

        except UsernameTakenException:
            info = 'Username {} already taken in room with code {}'.format(msg['user_name'], msg['room_code'])
            nw.send_NOT_OK_JoinRoomResp_with_info(sender_conn, info)
        
    def handle_ExitClientReq(self, msg, sender_conn):
        user_name = msg['user_name']
        self.remove_client_by_name_if_exists(user_name)

    def send_words_to_select_to_artist(self, words_to_select):
        self._state = RoomState.WORD_SELECTION
        word_selection_req = mc.build_word_selection_req(self._artist, self._room_code, words_to_select)
        artist_connection = self._joined_clients[self._artist]
        artist_connection.send(word_selection_req)

    def _start_bot_thread_timer(self):
        timer = threading.Timer(self._round_time / 10, self._game_bot_thread_function)
        timer.start()

    def _game_bot_thread_function(self):
        with self.lock:
            if self._state not in [RoomState.PREGAME, RoomState.POSTGAME]:
                self._start_bot_thread_timer()

                if self._state == RoomState.DRAWING:
                    bot_guess = self._game_bot.guess()
                    chat_msg_req = {
                        'msg_name': 'ChatMessageReq',
                        'user_name': 'BOT',
                        'room_code': self._room_code,
                        'message': bot_guess
                    }
                    self.handle_ChatMessageReq(chat_msg_req, None)

    def handle_StartGameReq(self, msg, sender_conn):
        try:
            if self._state not in [RoomState.PREGAME, RoomState.POSTGAME]:
                raise StateErrorException()
            
            user_name = msg['user_name']
            self.start_game(user_name)
            resp = mc.build_start_game_resp_ok()
            sender_conn.send(resp)

            words_to_select = self._enter_word_selection_state()

            self._start_bot_thread_timer()

            start_game_bc = {'msg_name': 'StartGameBc', 'artist': self._artist, 'score_awarded' : self._score_awarded}
            self.broadcast_message(start_game_bc)
            self.send_words_to_select_to_artist(words_to_select)

        except StartedNotByOwnerException:
            resp = mc.build_start_game_resp_not_ok('Only room owner can start the game!')
            sender_conn.send(resp)
        
        except StateErrorException:
            resp = mc.build_start_game_resp_not_ok('Trying to start game not in PREGAME state')
            sender_conn.send(resp)
    
        except NotEnaughPlayersException:
            resp = mc.build_start_game_resp_not_ok('There must be at least 2 players to start the game!')
            sender_conn.send(resp)

    def send_hint(self, num_of_letters=0):
        if self._state != RoomState.DRAWING:
            return

        hint = '_' * len(self._current_word)

        letters_left = num_of_letters

        for idx, val in enumerate(self._current_word):
            if val == ' ':
                hint = replace_at_index(hint, ' ', idx)
            elif letters_left > 0:
                hint = replace_at_index(hint, self._current_word[idx], idx)
                letters_left = letters_left - 1

        word_hint_bc = {
            'msg_name': 'WordHintBc',
            'word_hint': hint
        }
        self.broadcast_message(word_hint_bc)

    def handle_WordSelectionResp(self, msg):
        try:
            if self._state != RoomState.WORD_SELECTION:
                raise StateErrorException()

            if self._artist != msg['user_name']:
                raise WordSelectionRespNotFromArtistException()

            self._state = RoomState.DRAWING
            self._current_word = msg['selected_word']
            self.send_hint()

        except WordSelectionRespNotFromArtistException:
            logging.warn('[ROOM ID: {}] Received WordSelectionResp from {} - not artist'
                         .format(self._room_code, msg['user_name']))
        
        except StateErrorException:
            logging.warn('[ROOM ID: {}] Received WordSelectionResp from {} not in state WORD_SELECTION'
                         .format(self._room_code, msg['user_name']))
        
    def handle_DrawStrokeReq(self, msg):
        try:
            if self._state != RoomState.DRAWING:
                raise StateErrorException()
            
            if msg['user_name'] != self._artist:
                raise RuntimeError()
            
            self._game_bot.add_stroke(msg['stroke_coordinates'])
            draw_stroke_bc = {
                'msg_name': 'DrawStrokeBc',
                'stroke_coordinates': msg['stroke_coordinates']
            }
            self.broadcast_message(draw_stroke_bc)
            
        except StateErrorException:
            logging.warn('[ROOM ID: {}] Received WordSelectionResp from {} not in state DRAWING'
                         .format(self._room_code, msg['user_name']))
        
        except:
            logging.error('[ROOM ID: {}] Unknown error occurred when handling message {}'.format(self._room_code, msg))

    def handle_UndoLastStrokeReq(self, msg):
        try:
            if self._state != RoomState.DRAWING:
                raise StateErrorException()
            
            if msg['user_name'] != self._artist:
                raise RuntimeError()
            
            self._game_bot.undo_stroke()
            undo_last_stroke_bc = {'msg_name': 'UndoLastStrokeBc'}
            self.broadcast_message(undo_last_stroke_bc)

        except StateErrorException:
            logging.warn('[ROOM ID: {}] Received UndoLastStrokeReq from {} not in state DRAWING'
                         .format(self._room_code, msg['user_name']))
        
        except:
            logging.error('[ROOM ID: {}] Unknown error occurred when handling message {}'.format(self._room_code, msg))
    
    def handle_ClearCanvasReq(self, msg):
        try:
            if self._state != RoomState.DRAWING:
                raise StateErrorException()
            
            if msg['user_name'] != self._artist:
                raise RuntimeError()
            
            self._game_bot.clear_drawing()
            clear_canvas_bc = {'msg_name': 'ClearCanvasBc'}
            self.broadcast_message(clear_canvas_bc)

        except StateErrorException:
            logging.warn('[ROOM ID: {}] Received ClearCanvasReq from {} not in state DRAWING'
                         .format(self._room_code, msg['user_name']))
        
        except:
            logging.error('[ROOM ID: {}] Unknown error occurred when handling message {}'.format(self._room_code, msg))

import socket
import threading
import logging
import json
import sys
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from . import SocketMsgHandler
from Utils.PopUpWindow import PopUpWindow
from Application.GameWindow import GameWindow


class ConnectionHandler(QtCore.QObject):
    room_created_signal = QtCore.pyqtSignal(dict)
    room_joined_signal = QtCore.pyqtSignal(dict)
    chat_message_signal = QtCore.pyqtSignal(dict)
    scoreboard_update_signal = QtCore.pyqtSignal(dict)
    switch_window = QtCore.pyqtSignal(str)
    start_game_signal = QtCore.pyqtSignal(dict)
    word_selection_signal = QtCore.pyqtSignal(dict)
    word_hint_signal = QtCore.pyqtSignal(dict)
    player_left_signal = QtCore.pyqtSignal(dict)
    player_joined_signal = QtCore.pyqtSignal(dict)
    draw_stroke_signal = QtCore.pyqtSignal(dict)
    undo_last_stroke_signal = QtCore.pyqtSignal()
    clear_canvas_signal = QtCore.pyqtSignal()
    guess_correct_signal = QtCore.pyqtSignal(dict)
    artist_change_signal = QtCore.pyqtSignal(dict)
    game_over_signal = QtCore.pyqtSignal(dict)
    room_list_signal = QtCore.pyqtSignal(dict)
    owner_changed_signal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.connectedReceiverStatus = True

        self.server_config = self._load_config_file()
        self.SERVER = self.server_config['SERVER']
        self.PORT = self.server_config['PORT']
        self.ADDR = (self.SERVER, self.PORT)
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect(self.ADDR)

        self.receiver_thread = threading.Thread(
            target=self.receive, args=(self.conn, self.server_config)
        )
        self.receiver_thread.deamon = True
        self.receiver_thread.start()

    def kill_receiver(self):
        try:
            self.connectedReceiverStatus = False
            self.conn.shutdown(socket.SHUT_RDWR)
            self.conn.close()
            self.receiver_thread.join()
        except:
            logging.debug('[SOCKET RECEIVER] Unsuccessful socket shutdown!')
        logging.debug('[EXITING CONFIRMED] Killing all threads and exiting the client window')

    def _load_config_file(self):
        try:
            config_path = sys.argv[1]
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except:
            logging.error('[LOADING CONFIG FILE] Error occurred when loading configuration file!')
            exit()

    def is_connection_receiver_connected(self):
        return self.connectedReceiverStatus

    def receive(self, conn, server_config):
        while self.connectedReceiverStatus:
            logging.debug('[SOCKET RECEIVER] Awaiting for incoming messages ...')
            received_msg_name = None
            received_msg = None
            try:
                received_msg_name, received_msg = SocketMsgHandler.receive(conn, server_config)
                if not received_msg:
                    continue
            except:
                logging.debug('[SOCKET RECEIVER] Shutting down and closing socket connection')

            if received_msg_name == 'DrawStrokeBc':
                logging.debug('[SOCKET RECEIVER] Received Message: {}'.format('DrawStrokeBc'))
            else:
                logging.debug('[SOCKET RECEIVER] Received Message: {}'.format(received_msg))
            self.dispatch_received_message(received_msg)

    def dispatch_received_message(self, received_msg):
        message_dispatcher = {
            'CreateRoomResp': self.handle_CreateRoomResp,
            'JoinRoomResp': self.handle_JoinRoomResp,
            'ChatMessageBc': self.handle_ChatMessageBc,
            'StartGameResp': self.handle_StartGameResp,
            'StartGameBc': self.handle_StartGameBc,
            'ArtistPickBc': self.handle_ArtistPickBc,
            'WordSelectionReq': self.handle_WordSelectionReq,
            'DrawStrokeBc': self.handle_DrawStrokeBc,
            'UndoLastStrokeBc': self.handle_UndoLastStrokeBc,
            'ClearCanvasBc': self.handle_ClearCanvasBc,
            'WordGuessedBc': self.handle_WordGuessedBc,
            'FinishGameResp': self.handle_FinishGameResp,
            'GameFinishedBc': self.handle_GameFinishedBc,
            'GameRoomListResp': self.handle_GameRoomListResp,
            'WordHintBc': self.handle_WordHintBc,
            'UpdateScoreboardBc': self.handle_UpdateScoreboardBc,
            'OwnerChangedBc': self.handle_OwnerChangedBc,
        }
        return message_dispatcher.get(received_msg['msg_name'], self.handle_UnrecognizedMessage)(
            received_msg
        )

    def handle_CreateRoomResp(self, received_msg):
        if received_msg['status'] == 'OK':
            self.switch_window.emit(received_msg['room_code'])
            self.room_created_signal.emit(received_msg)
        else:
            PopUpWindow('Room could not be created!', 'ERROR')
            logging.debug('[MESSAGE DISPATCHER] handling CreateRoomResp failed, STATUS NOK')
        logging.debug('[MESSAGE DISPATCHER] handling CreateRoomResp Successful, STATUS OK')

    def handle_JoinRoomResp(self, received_msg):
        with GameWindow.thread_lock:
            if received_msg['status'] == 'OK':
                # TODO: enhance window switching
                self.switch_window.emit('Joining')
                self.room_joined_signal.emit(received_msg)
            else:
                PopUpWindow('Could not join to room!\n{}'.format(received_msg['info']), 'ERROR')
                logging.debug('[MESSAGE DISPATCHER] handling JoinRoomResp failed, STATUS NOK')
            logging.debug('[MESSAGE DISPATCHER] handling JoinRoomResp Successful, STATUS OK')

    def handle_ChatMessageBc(self, received_msg):
        with GameWindow.thread_lock:
            logging.debug(
                '[MESSAGE DISPATCHER] handling ChatMessageBc {}: {}'.format(
                    received_msg['author'], received_msg['message']
                )
            )
            self.chat_message_signal.emit(received_msg)

    def handle_ExitClientReq(self, received_msg):
        self.kill_receiver()
        self.chat_message_signal.emit('{} has left the game'.format(received_msg['user_name']))
        logging.debug('[MESSAGE DISPATCHER] handling ExitClientReq Successful, STATUS OK')

    def handle_StartGameResp(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] handling StartGameResp, STATUS {}'.format(received_msg['status'])
        )
        if received_msg['status'] == 'NOT_OK':
            PopUpWindow(received_msg['info'], 'ERROR')

    def handle_StartGameBc(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] handling StartGameBc, Artist: {}'.format(received_msg['artist'])
        )
        self.start_game_signal.emit(received_msg)
        self.artist_change_signal.emit(received_msg)

    def handle_ArtistPickBc(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] handling ArtistPickBc, Artist: {}'.format(received_msg['artist'])
        )
        self.artist_change_signal.emit(received_msg)

    def handle_WordSelectionReq(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] handling WordSelectionReq, Word List: {}'.format(
                received_msg['word_list']
            )
        )
        self.word_selection_signal.emit(received_msg)

    def handle_DrawStrokeBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling DrawStrokeBc')
        self.draw_stroke_signal.emit(received_msg)

    def handle_UndoLastStrokeBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling UndoStrokeDrawBc')
        self.undo_last_stroke_signal.emit()

    def handle_ClearCanvasBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling ClearCanvasBc')
        self.clear_canvas_signal.emit()

    def handle_WordGuessedBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling WordGuessedBc')
        self.guess_correct_signal.emit(received_msg)
        logging.debug(
            '[GUESS CORRECT] {} has guessed the word and gained {} points'.format(
                received_msg['user_name'], received_msg['score_awarded'][received_msg['user_name']]
            )
        )

    def handle_FinishGameResp(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling FinishGameResp')
        self.game_over_signal.emit(received_msg)

    def handle_GameFinishedBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling GameFinishedBc')
        self.game_over_signal.emit(received_msg)

    def handle_GameRoomListResp(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling GameRoomListResp')
        self.room_list_signal.emit(received_msg)

    def handle_WordHintBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling WordHintBc')
        self.word_hint_signal.emit(received_msg)

    def handle_OwnerChangedBc(self, received_msg):
        logging.debug('[MESSAGE DISPATCHER] handling handle_OwnerChangedBc {}'.format(received_msg))
        self.owner_changed_signal.emit(received_msg)

    def handle_UpdateScoreboardBc(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] handling handle_UpdateScoreboardBc {}'.format(received_msg)
        )
        self.scoreboard_update_signal.emit(received_msg)

    def handle_UnrecognizedMessage(self, received_msg):
        logging.debug(
            '[MESSAGE DISPATCHER] No defined handler for message: {}'.format(received_msg)
        )

    def send_create_room_req(self, user_name):
        send_create_room_req_msg = {'msg_name': 'CreateRoomReq', 'user_name': user_name}
        SocketMsgHandler.send(self.conn, send_create_room_req_msg, self.server_config)

    def send_join_room_req(self, user_name, room_code):
        send_join_room_req_msg = {
            'msg_name': 'JoinRoomReq',
            'user_name': user_name,
            'room_code': room_code,
        }

        SocketMsgHandler.send(self.conn, send_join_room_req_msg, self.server_config)

    def send_chat_msg_req(self, user_name, room_code, message):
        logging.debug('[CHAT MESSAGE] Sending message {}: {}'.format(user_name, message))
        send_char_msg = {
            'msg_name': 'ChatMessageReq',
            'user_name': user_name,
            'room_code': room_code,
            'message': message,
        }
        SocketMsgHandler.send(self.conn, send_char_msg, self.server_config)

    def send_exit_client_req(self, user_name, room_code):
        notify_server_about_leaving = {
            'msg_name': 'ExitClientReq',
            'user_name': user_name,
            'room_code': room_code,
        }
        SocketMsgHandler.send(self.conn, notify_server_about_leaving, self.server_config)

    def send_socket_disconnect_req(self):
        socket_disconnect_req = {'msg_name': 'DisconnectSocketReq'}
        SocketMsgHandler.send(self.conn, socket_disconnect_req, self.server_config)

    def send_start_game_req(self, user_name, room_code):
        start_game_req = {
            'msg_name': 'StartGameReq',
            'user_name': user_name,
            'room_code': room_code,
        }
        SocketMsgHandler.send(self.conn, start_game_req, self.server_config)

    def send_word_selection_resp(self, user_name, room_code, selected_word):
        logging.debug(
            '[SENDING MESSAGE] WordSelectionResp, selected word = {}'.format(selected_word)
        )
        word_selection_resp = {
            'msg_name': 'WordSelectionResp',
            'user_name': user_name,
            'room_code': room_code,
            'selected_word': selected_word,
        }
        SocketMsgHandler.send(self.conn, word_selection_resp, self.server_config)

    def send_draw_stroke_req(self, user_name, room_code, stroke_coordinates):
        draw_stroke_req = {
            'msg_name': 'DrawStrokeReq',
            'user_name': user_name,
            'room_code': room_code,
            'stroke_coordinates': stroke_coordinates,
        }
        SocketMsgHandler.send(self.conn, draw_stroke_req, self.server_config)

    def send_undo_last_stroke_req(self, user_name, room_code):
        undo_last_stroke_req = {
            'msg_name': 'UndoLastStrokeReq',
            'user_name': user_name,
            'room_code': room_code,
        }
        SocketMsgHandler.send(self.conn, undo_last_stroke_req, self.server_config)

    def send_clear_canvas_req(self, user_name, room_code):
        clear_canvas_req = {
            'msg_name': 'ClearCanvasReq',
            'user_name': user_name,
            'room_code': room_code,
        }
        SocketMsgHandler.send(self.conn, clear_canvas_req, self.server_config)

    def send_finish_game_req(self, user_name, room_code):
        finish_game_req = {
            'msg_name': 'FinishGameReq',
            'user_name': user_name,
            'room_code': room_code,
        }
        SocketMsgHandler.send(self.conn, finish_game_req, self.server_config)

    def send_game_room_list_req(self):
        game_room_list_req = {'msg_name': 'GameRoomListReq'}
        SocketMsgHandler.send(self.conn, game_room_list_req, self.server_config)


if __name__ == '__main__':
    pass

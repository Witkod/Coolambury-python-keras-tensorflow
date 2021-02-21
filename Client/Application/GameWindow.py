import logging
import operator
import threading
import bleach
from enum import Enum
from PyQt5 import QtCore, QtWidgets, QtGui
from .WordSelectionWindow import WordSelectionWindow
from .DrawingHistoryWindow import DrawingHistoryWindow
from Utils.PopUpWindow import PopUpWindow
from enum import Enum
from copy import deepcopy
from PyQt5 import QtCore, QtWidgets, QtGui
from .DrawingHistoryWindow import DrawingHistoryWindow


class GameState(Enum):
    PREGAME = 0
    WORD_SELECTION = 1
    DRAWING = 2
    POSTGAME = 3


class GameWindow(QtWidgets.QWidget):
    thread_lock = threading.Lock()
    switch_window = QtCore.pyqtSignal()
    key_pressed_signal = QtCore.pyqtSignal(QtCore.QEvent)
    word_locally_selected_signal = QtCore.pyqtSignal(dict)

    def __init__(self, connection_handler):
        QtWidgets.QWidget.__init__(self)
        with self.thread_lock:
            logging.debug('[GameWindow] Creating Game Window instance...')

            self.client_context = None
            self.connection_handler = connection_handler

            # Game
            # Contains a dict of all player names and their scores, ex. {"Atloas": 100, "loska": 110}
            # Player drawing order enforced by server?
            self.game_state = None
            self.player = ""
            self.owner = ""
            self.players = {}
            self.players[self.player] = 0
            self.players['BOT'] = 0
            self.artist = None
            # The hint text, modifiable on server request.
            # For the painter, should display the full word. Placeholder for now.
            self.hint = '_ _ _ _'

            self.word_selection_window = None
            self.drawing_history_window = None

            # Drawing
            self.previous_x = None
            self.previous_y = None
            self.drawings = []
            self.strokes = []
            self.stroke = []

            # Window
            self.root_vBox = QtWidgets.QVBoxLayout()
            self.top_hBox = QtWidgets.QHBoxLayout()
            self.bottom_hBox = QtWidgets.QHBoxLayout()
            self.game_and_controls_vBox = QtWidgets.QVBoxLayout()
            self.controls_hBox = QtWidgets.QHBoxLayout()
            self.chat_vBox = QtWidgets.QVBoxLayout()
            self.chat_bottom_hBox = QtWidgets.QHBoxLayout()

            self.disconnect_button = QtWidgets.QPushButton('Disconnect')
            self.disconnect_button.setMaximumSize(100, 50)
            self.disconnect_button.clicked.connect(self.disconnect_clicked)
            self.top_hBox.addWidget(self.disconnect_button)

            self.start_button = QtWidgets.QPushButton('Start')
            self.start_button.setMaximumSize(100, 50)
            self.start_button.clicked.connect(self.start_clicked)
            self.start_button.setDisabled(True)
            self.top_hBox.addWidget(self.start_button)

            self.hints = QtWidgets.QLabel('')
            self.top_hBox.addWidget(self.hints)

            self.scoreboard_column_labels = ['Nickname', 'Score']
            self.scoreboard = QtWidgets.QTableWidget()
            self.scoreboard.verticalHeader().hide()
            self.scoreboard.setColumnCount(len(self.scoreboard_column_labels))
            self.scoreboard.setHorizontalHeaderLabels(self.scoreboard_column_labels)
            for column in range(len(self.scoreboard_column_labels)):
                self.scoreboard.setColumnWidth(column, 125)
            self.bottom_hBox.addWidget(self.scoreboard)

            self.canvas = QtGui.QPixmap(400, 400)
            self.canvas.fill(QtGui.QColor('white'))

            self.canvas_container = QtWidgets.QLabel()
            self.canvas_container.setPixmap(self.canvas)
            self.game_and_controls_vBox.addWidget(self.canvas_container)

            self.undo_button = QtWidgets.QPushButton('Undo')
            self.undo_button.setDisabled(True)
            self.undo_button.clicked.connect(self.undo_clicked)
            self.controls_hBox.addWidget(self.undo_button)

            self.clear_canvas_button = QtWidgets.QPushButton('Clear')
            self.clear_canvas_button.setDisabled(True)
            self.clear_canvas_button.clicked.connect(self.clear_canvas_clicked)
            self.controls_hBox.addWidget(self.clear_canvas_button)

            self.game_and_controls_vBox.addLayout(self.controls_hBox)

            self.chat = QtWidgets.QTextEdit()
            self.chat.setReadOnly(True)

            self.chat_entry_line = QtWidgets.QLineEdit()
            self.chat_entry_line.setPlaceholderText('Have a guess!')
            self.chat_entry_line.returnPressed.connect(self.new_chat_message)

            self.chat_entry_button = QtWidgets.QPushButton('Send')
            self.chat_entry_button.clicked.connect(self.new_chat_message)

            self.chat_bottom_hBox.addWidget(self.chat_entry_line)
            self.chat_bottom_hBox.addWidget(self.chat_entry_button)

            self.chat_vBox.addWidget(self.chat)
            self.chat_vBox.addLayout(self.chat_bottom_hBox)

            self.bottom_hBox.addLayout(self.game_and_controls_vBox)
            self.bottom_hBox.addLayout(self.chat_vBox)

            self.root_vBox.addLayout(self.top_hBox)
            self.root_vBox.addLayout(self.bottom_hBox)

            self.setLayout(self.root_vBox)
            self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

            self.update_scoreboard()

            self.connect_signals()

            logging.debug('[GameWindow] Game Window created...')

    def connect_signals(self):
        self.connection_handler.room_created_signal.connect(self.handle_room_created_signal)
        self.connection_handler.room_joined_signal.connect(self.handle_room_joined_signal)
        self.connection_handler.chat_message_signal.connect(self.display_message)
        self.connection_handler.start_game_signal.connect(self.handle_start_game_signal)
        self.connection_handler.word_selection_signal.connect(self.handle_word_selection_signal)
        self.connection_handler.player_joined_signal.connect(self.handle_player_joined_signal)
        self.connection_handler.player_left_signal.connect(self.handle_player_left_signal)
        self.connection_handler.word_hint_signal.connect(self.handle_word_hint_signal)
        self.connection_handler.draw_stroke_signal.connect(self.handle_stroke_signal)
        self.connection_handler.undo_last_stroke_signal.connect(self.handle_undo_signal)
        self.connection_handler.clear_canvas_signal.connect(self.handle_clear_canvas_signal)
        self.connection_handler.guess_correct_signal.connect(self.handle_guess_correct_signal)
        self.connection_handler.artist_change_signal.connect(self.handle_artist_changed_signal)
        self.connection_handler.game_over_signal.connect(self.handle_game_over_signal)
        self.connection_handler.scoreboard_update_signal.connect(self.handle_scoreboard_update_signal)
        self.connection_handler.owner_changed_signal.connect(self.handle_owner_changed_signal)

    # Do not rename
    def closeEvent(self, event):
        logging.debug('[GameWindow Exit] Client is requesting for client exit')
        if self.connection_handler.is_connection_receiver_connected():
            self.connection_handler.send_exit_client_req(
                self.client_context['username'], self.client_context['roomCode']
            )
            self.connection_handler.send_socket_disconnect_req()
            self.connection_handler.kill_receiver()

    def display_system_message(self, message):
        self.chat.append('<b>{}</b>'.format(message))

    def display_user_message(self, message):
        sanitized_message = bleach.clean(message['message'], tags=[])
        self.chat.append('{}: {}'.format(message['author'], sanitized_message))

    def display_message(self, message):
        if message['author'] == 'SERVER':
            self.display_system_message(message['message'])
        else:
            self.display_user_message(message)

    # Do not rename
    def mouseMoveEvent(self, event):
        if self.artist != self.player:
            return

        x = event.x() - self.canvas_container.x()
        y = event.y() - self.canvas_container.y()

        if self.previous_x is None:
            self.previous_x = x
            self.previous_y = y

        painter = QtGui.QPainter(self.canvas_container.pixmap())
        self.configure_pen(painter)
        painter.drawLine(self.previous_x, self.previous_y, x, y)
        painter.end()
        self.update()

        self.previous_x = x
        self.previous_y = y

        self.stroke.append((x, y))

    # Do not rename
    def mouseReleaseEvent(self, event):
        if self.artist != self.player:
            return

        self.strokes.append(self.stroke.copy())
        self.previous_x = None
        self.previous_y = None

        self.connection_handler.send_draw_stroke_req(
            self.client_context['username'], self.client_context['roomCode'], self.stroke.copy()
        )
        self.stroke = []

    def initialize_room(self, client_context):
        logging.debug('[GameWindow] Initializing Game Window...')
        self.client_context = client_context
        self.setWindowTitle(
            'Coolambury [{}] {}'.format(
                self.client_context['username'], self.client_context['roomCode']
            )
        )

        self.chat.clear()

        logging.debug('[GameWindow] Game Window initialized!')

    def handle_room_created_signal(self, message):
        logging.debug('[GameWindow] Handling room_created_signal')
        self.game_state = None
        self.player = self.client_context['username']
        self.owner = self.player
        self.players = {}
        self.players[self.player] = 0
        self.players['BOT'] = 0
        self.artist = None
        # The hint text, modifiable on server request.
        # For the painter, should display the full word. Placeholder for now.
        self.hint = '_ _ _ _'

        self.word_selection_window = None
        self.drawing_history_window = None

        # Drawing
        self.previous_x = None
        self.previous_y = None
        self.drawings = []
        self.strokes = []
        self.stroke = []

        if len(self.players) > 2:
            self.start_button.setDisabled(False)

        self.clear_canvas()
        self.update_scoreboard()
        self.update()

        logging.debug("[GameWindow] Room created. Player = {}, Owner = {}".format(self.player, self.owner))

    def handle_room_joined_signal(self, message):
        logging.debug('[GameWindow] Handling room_joined_signal')
        logging.debug('[GameWindow] Owner = {}', message['owner'])
        self.game_state = None
        self.player = self.client_context['username']
        self.owner = message['owner']
        self.players = message['users_in_room']
        self.artist = None
        # The hint text, modifiable on server request.
        # For the painter, should display the full word. Placeholder for now.
        self.hint = '_ _ _ _'

        self.word_selection_window = None
        self.drawing_history_window = None

        # Drawing
        self.previous_x = None
        self.previous_y = None
        self.drawings = []
        self.strokes = []
        self.stroke = []

        self.start_button.setDisabled(True)

        self.clear_canvas()
        self.update_scoreboard()
        self.update()

    def handle_start_game_signal(self, message):
        logging.debug('[GameWindow] Handling start_game_signal')
        self.start_button.setDisabled(True)
        self.display_system_message('Game started!')
        self.players = message['score_awarded']
        self.update_scoreboard()

    def handle_player_joined_signal(self, message):
        logging.debug('[GameWindow] Handling player_joined_signal')
        logging.debug('[GameWindow] Owner = {}, player = {}'.format(self.owner, self.player))
        self.display_system_message('{} joined the room.'.format(message['player']))
        self.players[message['player']] = 0
        if len(self.players) > 2 and self.owner == self.player:
            self.start_button.setDisabled(False)
        self.update_scoreboard()
        self.update()

    def handle_player_left_signal(self, message):
        logging.debug('[GameWindow] Handling player_left_signal')
        self.display_system_message('{} left the room.'.format(message['player']))
        del self.players[message['player']]
        if len(self.players) < 3 and self.owner == self.player:
            self.start_button.setDisabled(True)
        self.update_scoreboard()

    def handle_artist_changed_signal(self, message):
        logging.debug('[GameWindow] Handling artist_changed_signal')
        if self.word_selection_window is not None:
            self.word_selection_window.close()
        self.display_system_message('{} is now the artist.'.format(message['artist']))
        self.artist = message['artist']
        if self.player == self.artist:
            self.undo_button.setDisabled(False)
            self.clear_canvas_button.setDisabled(False)
        else:
            self.undo_button.setDisabled(True)
            self.clear_canvas_button.setDisabled(True)
        self.stroke = []
        self.strokes = []
        self.clear_canvas()
        self.game_state = GameState.WORD_SELECTION

    def handle_word_selection_signal(self, message):
        logging.debug('[GameWindow] Handling word_selection_signal')
        self.word_selection_window = WordSelectionWindow(message['word_list'])
        self.word_selection_window.prompt_locally_selected_signal.connect(
            self.handle_word_locally_selected_signal
        )
        self.game_state = GameState.WORD_SELECTION

    def handle_word_locally_selected_signal(self, message):
        logging.debug('[GameWindow] Handling word_locally_selected_signal')
        logging.debug(
            '[GameWindow] [Word Selection] Selected word = {}'.format(message['selected_word'])
        )
        self.hints.setText(message['selected_word'])

        self.connection_handler.send_word_selection_resp(
            self.client_context['username'],
            self.client_context['roomCode'],
            message['selected_word'],
        )

    def handle_word_hint_signal(self, message):
        logging.debug('[GameWindow] Handling word_hint_signal')
        if self.player == self.artist:
            return
        else:
            self.hint = ''
            for i in range(len(message['word_hint']) - 1):
                self.hint += message['word_hint'][i] + ' '
            self.hint += '_'
            self.hints.setText(self.hint)
        self.game_state = GameState.DRAWING

    def handle_stroke_signal(self, message):
        logging.debug('[GameWindow] Handling draw_stroke_signal')
        stroke = message['stroke_coordinates']
        self.strokes.append(stroke.copy())

        painter = QtGui.QPainter(self.canvas_container.pixmap())
        self.configure_pen(painter)
        if len(stroke) == 1:
            painter.drawLine(stroke[0][0], stroke[0][1], stroke[0][0], stroke[0][1])
        else:
            for i in range(len(stroke) - 1):
                painter.drawLine(stroke[i][0], stroke[i][1], stroke[i + 1][0], stroke[i + 1][1])
        painter.end()
        self.update()

    def handle_undo_signal(self):
        logging.debug('[GameWindow] Handling undo_last_stroke_signal')
        self.undo()

    def handle_clear_canvas_signal(self):
        logging.debug('[GameWindow] Handling clear_canvas_signal')
        self.stroke = []
        self.strokes = []
        self.clear_canvas()

    def handle_guess_correct_signal(self, message):
        logging.debug('[GameWindow] Handling guess_correct_signal')
        self.display_system_message(
            '{} guessed the word: {}!'.format(message['user_name'], message['word'])
        )
        self.drawings.append(self.strokes.copy())
        self.players = message['score_awarded']
        self.update_scoreboard()

    def handle_game_over_signal(self, message):
        logging.debug('[GameWindow] Handling game_over_signal')
        self.game_state = GameState.POSTGAME
        self.undo_button.setDisabled(True)
        self.clear_canvas_button.setDisabled(True)
        if len(self.players) > 2 and self.player == self.owner:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)
        self.artist = ''
        self.update_scoreboard()
        tie = False
        top_score = 0
        winner = ''
        for player in self.players:
            if self.players[player] > top_score:
                top_score = self.players[player]
                winner = player
                tie = False
            elif self.players[player] == top_score:
                tie = True
        if tie:
            self.display_system_message("It's a tie!")
        else:
            self.display_system_message('{} has won!'.format(winner))
        if self.drawings:
            self.drawing_history_window = DrawingHistoryWindow(self.drawings)
        self.drawings = []

    def handle_owner_changed_signal(self, message):
        logging.debug('[GameWindow] Handling owner_changed_signal')
        self.owner = message['owner']
        self.display_system_message('{} is the new room owner!'.format(self.owner))
        if (
            self.game_state == GameState.PREGAME or self.game_state == GameState.POSTGAME
        ) and self.player == self.owner:
            self.start_button.setDisabled(False)

    def undo_clicked(self):
        self.undo()
        self.connection_handler.send_undo_last_stroke_req(
            self.client_context['username'], self.client_context['roomCode']
        )

    def clear_canvas_clicked(self):
        self.stroke = []
        self.strokes = []
        self.clear_canvas()
        self.connection_handler.send_clear_canvas_req(
            self.client_context['username'], self.client_context['roomCode']
        )

    def redraw(self):
        self.clear_canvas()
        painter = QtGui.QPainter(self.canvas_container.pixmap())
        self.configure_pen(painter)
        for stroke in self.strokes:
            if len(stroke) == 1:
                painter.drawLine(stroke[0][0], stroke[0][1], stroke[0][0], stroke[0][1])
            else:
                for i in range(len(stroke) - 1):
                    painter.drawLine(stroke[i][0], stroke[i][1], stroke[i + 1][0], stroke[i + 1][1])
        painter.end()
        self.update()

    def undo(self):
        self.stroke = []
        if len(self.strokes) > 0:
            self.strokes.pop()
        self.redraw()

    def clear_canvas(self):
        painter = QtGui.QPainter(self.canvas_container.pixmap())
        painter.eraseRect(0, 0, self.canvas.width(), self.canvas.height())
        painter.end()
        self.update()

    def configure_pen(self, painter):
        pen = painter.pen()
        pen.setWidth(4)
        pen.setColor(QtGui.QColor('black'))
        painter.setPen(pen)

    def handle_scoreboard_update_signal(self, message):
        logging.debug('[GameWindow] Handling scoreboard_update_signal')
        self.players = message['users_in_room']
        if len(self.players) > 2 and self.owner == self.player:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)
        self.update_scoreboard()

    def update_scoreboard(self):
        # TODO: consider renaming players to scoreboardData
        self.scoreboard.setRowCount(len(self.players))
        player_number = 0
        sorted_players = sorted(self.players.items(), reverse=True, key=operator.itemgetter(1))
        for player in sorted_players:
            player_name = player[0]
            score = player[1]
            name_item = QtWidgets.QTableWidgetItem(player_name)
            score_item = QtWidgets.QTableWidgetItem(str(score))
            self.scoreboard.setItem(player_number, 0, name_item)
            self.scoreboard.setItem(player_number, 1, score_item)
            player_number += 1

    def new_chat_message(self):
        message = self.chat_entry_line.text()
        self.chat_entry_line.clear()
        self.connection_handler.send_chat_msg_req(
            self.client_context['username'], self.client_context['roomCode'], message
        )

    def disconnect_clicked(self):
        self.connection_handler.send_exit_client_req(
            self.client_context['username'], self.client_context['roomCode']
        )
        self.switch_window.emit()

    def start_clicked(self):
        self.connection_handler.send_start_game_req(
            self.client_context['username'], self.client_context['roomCode']
        )


if __name__ == '__main__':
    pass

from PyQt5 import QtWidgets, QtCore, QtGui
import socket
import threading
import logging
from Utils.PopUpWindow import PopUpWindow
from Communication import SocketMsgHandler, ConnectionHandler
from Communication.ConnectionHandler import ConnectionHandler


class StartWindow(QtWidgets.QWidget):
    def __init__(self, connection_handler, client_context):
        super().__init__()

        self.client_context = client_context
        self.connection_handler = connection_handler
        self.connection_handler.room_list_signal.connect(self.handle_game_room_list_resp)

        self.setMinimumSize(250, 100)
        self.setMaximumSize(350, 300)
        self.setWindowTitle('Coolambury')

        self.root_vBox = QtWidgets.QVBoxLayout()

        self.nickname_label = QtWidgets.QLabel('Enter your nickname:')
        self.root_vBox.addWidget(self.nickname_label)

        self.nickname_field = QtWidgets.QLineEdit()
        self.nickname_field.maxLength = 15
        self.root_vBox.addWidget(self.nickname_field)

        self.room_code_label = QtWidgets.QLabel('Enter room code:')
        self.root_vBox.addWidget(self.room_code_label)

        self.room_code_field = QtWidgets.QLineEdit()
        self.room_code_field.maxLength = 8
        self.root_vBox.addWidget(self.room_code_field)

        self.room_list = QtWidgets.QListWidget()
        self.room_list.setMinimumSize(200, 100)
        self.room_list.addItem('no available rooms :(')
        self.room_list.itemDoubleClicked.connect(self.room_list_element_clicked)
        self.update_room_list()
        self.root_vBox.addWidget(self.room_list)

        self.refresh_room_list_button = QtWidgets.QPushButton('Refresh List')
        self.refresh_room_list_button.clicked.connect(self.update_room_list)
        self.root_vBox.addWidget(self.refresh_room_list_button)

        self.join_button = QtWidgets.QPushButton('Join room')
        self.join_button.clicked.connect(self.delegate_room_join_to_handler)
        self.root_vBox.addWidget(self.join_button)

        self.create_room_button = QtWidgets.QPushButton('Create Room')
        self.create_room_button.clicked.connect(self.delegate_room_creation_to_handler)
        self.root_vBox.addWidget(self.create_room_button)

        self.setLayout(self.root_vBox)
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

    # TODO: Add validation for special characters!
    def validate_nickname(self):
        is_nickname_valid = not self.nickname_field.text() == ''

        logging.debug('[NICKNAME VALIDATION] Given nickname is valid: {}'.format(is_nickname_valid))
        if is_nickname_valid:
            return True
        return False

    def validate_room_code(self):
        is_room_code_valid = not self.room_code_field.text() == ''
        is_room_code_valid = len(self.room_code_field.text()) == 8

        logging.debug('[ROOM CODE VALIDATION] Room code specified: {}'.format(is_room_code_valid))
        if is_room_code_valid:
            return True
        return False

    # Do not rename
    def closeEvent(self, event):
        logging.debug('[EXITING ATTEMPT] Client is requesting for application exit')
        if self.connection_handler.is_connection_receiver_connected():
            self.connection_handler.send_socket_disconnect_req()
            self.connection_handler.kill_receiver()

    def delegate_room_creation_to_handler(self):
        if self.validate_nickname():
            self.client_context['username'] = self.nickname_field.text()
            self.connection_handler.send_create_room_req(self.client_context['username'])
        else:
            PopUpWindow('Nickname not valid!', 'ERROR')

    def delegate_room_join_to_handler(self):
        is_nickname_valid = self.validate_nickname()
        is_room_code_valid = self.validate_room_code()
        if is_nickname_valid and is_room_code_valid:
            self.client_context['username'] = self.nickname_field.text()
            self.client_context['roomCode'] = self.room_code_field.text()
            self.connection_handler.send_join_room_req(
                self.client_context['username'], self.client_context['roomCode']
            )
        elif not is_nickname_valid:
            PopUpWindow('Nickname not valid!', 'ERROR')
        if not is_room_code_valid:
            PopUpWindow('Room code not valid!', 'ERROR')

    def handle_game_room_list_resp(self, message):
        logging.debug('[ROOM LIST] Handling RoomListResp: {}'.format(message))
        available_rooms = message['room_list']

        self.room_list.clear()
        if not available_rooms:
            self.room_list.addItem('no available rooms :(')

        for room in available_rooms:
            self.room_list.addItem(
                QtWidgets.QListWidgetItem(
                    '{} - {}players - {}'.format(
                        room['owner_name'], room['num_of_players'], room['room_code']
                    )
                )
            )

    def room_list_element_clicked(self, item):
        fetched_room_code = item.text()[-8:]
        logging.debug(
            '[ROOM LIST CLICKED] clicked: {},'.format(item.text()[-8:], fetched_room_code)
        )

        is_nickname_valid = self.validate_nickname()
        if is_nickname_valid:
            self.client_context['username'] = self.nickname_field.text()
            self.client_context['roomCode'] = fetched_room_code
            self.connection_handler.send_join_room_req(
                self.client_context['username'], self.client_context['roomCode']
            )
        else:
            PopUpWindow('Nickname not valid!', 'ERROR')

    def update_room_list(self):
        self.connection_handler.send_game_room_list_req()


if __name__ == '__main__':
    pass

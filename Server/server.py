import logging
import threading
from qdrecognizer import QDRecognizer
import sys
import json
import msghandling as mh
import networking as nw
import csv


class Server:
    def __init__(self):
        self._resources = {}
        self._resources['rooms'] = {}
        self._resources['clients'] = []
        self._load_config_file()
        self._prepare_list_of_words()
        self._server_socket = nw.create_and_bind_socket(self._resources['config'])
        self._map_message_handlers()
        config = self._resources['config']
        QDRecognizer.prepare_model(config['model_path'], config['labels_path'])
        logging.debug('Initializing server...')

    def _load_config_file(self):
        try:
            config_path = sys.argv[1]
            with open(config_path, 'r') as config_file:
                self._resources['config'] = json.load(config_file)
        except:
            logging.error('Error occurred when loading configuration file!')
            exit()

    def _prepare_list_of_words(self):
        self._resources['words'] = []
        try:
            with open(self._resources['config']['labels_path']) as f:
                reader = csv.reader(f, delimiter=',')
                for row in reader:
                    self._resources['words'].append(row[1])
        except:
            logging.error('Error occurred when loading list of words!')
            exit()
                
    def _map_message_handlers(self):
        self._msg_mapping = {
            'CreateRoomReq': mh.handle_CreateRoomReq,
            'JoinRoomReq': mh.handle_JoinRoomReq,
            'ChatMessageReq': mh.handle_ChatMessageReq,
            'ExitClientReq': mh.handle_ExitClientReq,
            'StartGameReq': mh.handle_StartGameReq,
            'WordSelectionResp': mh.handle_WordSelectionResp,
            'DrawStrokeReq': mh.handle_DrawStrokeReq,
            'UndoLastStrokeReq': mh.handle_UndoLastStrokeReq,
            'ClearCanvasReq': mh.handle_ClearCanvasReq,
            'GameRoomListReq': mh.handle_GameRoomListReq,
            'DisconnectSocketReq' : mh.handle_DisconnectSocketReq
        }

    def start(self):
        logging.debug('Server is starting...')
        self._server_socket.listen()

        while True:
            conn, addr = self._server_socket.accept()

            new_client = nw.ClientConnection(conn, addr, self._resources, self._msg_mapping)
            self._resources['clients'].append(new_client)
            thread = threading.Thread(target=new_client.handle_client_messages)
            thread.start()

            logging.debug('Active connections: {}'.format(len(self._resources['clients'])))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d](%(funcName)s)  %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.DEBUG)

    coolambury_server = Server()
    coolambury_server.start()

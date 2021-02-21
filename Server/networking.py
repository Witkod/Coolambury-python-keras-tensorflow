import logging
import msghandling as mh
import msgcreation as mc
import pickle
import socket


def create_and_bind_socket(config):
    ADDR = ('', config['PORT'])
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(ADDR)

    return server_socket


def send_NOT_OK_JoinRoomResp_with_info(conn, info):
    logging.debug('{}'.format(info))
    resp = mc.build_not_ok_join_room_resp(info=info)
    conn.send(resp)


class ClientConnection:
    id_counter = 0

    def __init__(self, conn, addr, resources, msg_mapping):
        self._resources = resources
        self._conn = conn
        self._addr = addr
        self._msg_mapping = msg_mapping
        self._connected = True
        self._config = resources['config']
        self._id = ClientConnection.id_counter
        ClientConnection.id_counter += 1
        logging.debug('[CLIENT ID: {}] connected'.format(self._id))
    
    def _receive_bytes(self, bytes_no):
        bytes_left = bytes_no
        received_bytes = []

        while bytes_left != 0:
            received_part = self._conn.recv(bytes_left)
            bytes_left = bytes_left - len(received_part)
            received_bytes.append(received_part)

        received_bytes_word = b''.join(received_bytes)
        return received_bytes_word

    def _remove_client_after_connection_error(self):
        rooms = self._resources['rooms']
        for room_code in rooms:
            room = rooms[room_code]
            with room.lock:
                is_removed = room.remove_client_by_connection_if_exists(self)
                if is_removed:
                    if room.num_of_members() == 0:
                        del self._resources['rooms'][room_code]
                        logging.info('Room with code {} deleted (0 players)'.format(room_code))
                    break

    def _receive(self):
        try:
            msg_header_bytes = self._receive_bytes(self._config['HEADER_LEN'])
            if msg_header_bytes != b'':
                msg_header = pickle.loads(msg_header_bytes)
                msg_body_bytes = self._receive_bytes(msg_header['length'])
                msg_body = pickle.loads(msg_body_bytes)

                return msg_header['name'], msg_body

            return '', None

        except ConnectionResetError:
            self._remove_client_after_connection_error()
            self.close_connection()

            return '', None

    def send(self, msg_body):
        try:
            msg_body_bytes = pickle.dumps(msg_body)
            msg_header = {'length': len(msg_body_bytes), 'name': msg_body['msg_name']}
            msg_header_bytes = pickle.dumps(msg_header)
            msg_header_string_len = len(msg_header_bytes)

            msg_header_bytes += b' ' * (self._config['HEADER_LEN'] - msg_header_string_len)

            self._conn.send(msg_header_bytes)
            self._conn.send(msg_body_bytes)

        except ConnectionResetError:
            self._remove_client_after_connection_error()
            self.close_connection()

    def handle_client_messages(self):
        while self._connected:
            msg_name, msg_body = self._receive()
            if msg_body:
                logging.debug('[CLIENT ID: {}] dispatching message {}'.format(self._id, msg_name))
                try:
                    handling_func = self._msg_mapping[msg_name]
                    handling_func(self._resources, self, msg_body)
                except KeyError:
                    logging.error('[CLIENT ID: {}] Handlind function not found for {}'.format(self._id, msg_name))
                except:
                    logging.error('[CLIENT ID: {}] Unknown error occurred when handling msg {} = {}'.format(self._id, msg_name, msg_body))

    def close_connection(self):
        try:
            self._resources['clients'].remove(self)
            self._connected = False
            self._conn.close()
        except:
            logging.error('[CLIENT ID: {}] Unknown error occurred when closing connection!'.format(self._id))

        logging.debug('[CLIENT ID: {}] Connection closed'.format(self._id))

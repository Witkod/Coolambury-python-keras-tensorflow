import pickle
import logging


def send(conn, msg_body, config):
    msg_body_bytes = pickle.dumps(msg_body)
    msg_header = {'length': len(msg_body_bytes), 'name': msg_body['msg_name']}
    msg_header_bytes = pickle.dumps(msg_header)
    msg_header_string_len = len(msg_header_bytes)

    msg_header_bytes += b' ' * (config['HEADER_LEN'] - msg_header_string_len)

    conn.send(msg_header_bytes)
    conn.send(msg_body_bytes)


def receive_bytes(conn, bytes_no):
    bytes_left = bytes_no
    received_bytes = []

    while bytes_left != 0:
        received_part = conn.recv(bytes_left)
        bytes_left = bytes_left - len(received_part)
        received_bytes.append(received_part)

    received_bytes_word = b''.join(received_bytes)
    return received_bytes_word


def receive(conn, config):

    msg_header_bytes = receive_bytes(conn, config['HEADER_LEN'])
    if msg_header_bytes != b'':
        msg_header = pickle.loads(msg_header_bytes)
        msg_body_bytes = receive_bytes(conn, msg_header['length'])
        msg_body = pickle.loads(msg_body_bytes)

        return msg_header['name'], msg_body

    return '', None

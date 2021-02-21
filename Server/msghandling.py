import logging
import gameroom as gr
import networking as nw
import msgcreation as mc


class RoomNotExistsException(Exception):
    pass


def find_room(resources, room_code):
    try:
        rooms = resources['rooms']
        room = rooms[room_code]
        return room

    except KeyError:
        raise RoomNotExistsException()

    except:
        raise RuntimeError()


def handle_ChatMessageReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])
        with room.lock:
            room.handle_ChatMessageReq(msg, sender_conn)

    except RoomNotExistsException:
        logging.error('Room with code {} not found'.format(msg['room_code']))
    
    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))


def handle_CreateRoomReq(resources, sender_conn, msg):
    try:
        rooms = resources['rooms']

        room_code = mc.generate_unique_code(8, rooms)
        room = gr.Room(msg['user_name'], sender_conn, room_code, resources['words'])

        resp = mc.build_ok_create_room_resp(room_code)
        rooms[room_code] = room
        sender_conn.send(resp)

    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))

        resp = mc.build_not_ok_create_room_resp()
        sender_conn.send(resp)


def handle_JoinRoomReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])
        with room.lock:
            room.handle_JoinRoomReq(msg, sender_conn)

    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        nw.send_NOT_OK_JoinRoomResp_with_info(sender_conn, info)

    except:
        logging.error('Unknown error occurred when handling message{}'.format(msg))
        nw.send_NOT_OK_JoinRoomResp_with_info(sender_conn, 'Unknown error occurred when joining room!')


def handle_ExitClientReq(resources, sender_conn, msg):
    try:
        room_code = msg['room_code']
        room = find_room(resources, room_code)

        with room.lock:
            room.handle_ExitClientReq(msg, sender_conn)

        if room.num_of_members() == 0:
            del resources['rooms'][room_code]
            logging.info('Room with code {} deleted (0 players)'.format(room_code))

    except RoomNotExistsException:
        logging.debug('Room with code {} not found'.format(room_code))

    except:
        logging.error('Error occurred when handling message {}'.format(msg))


def handle_DisconnectSocketReq(resources, sender_conn, msg):
    try:
       sender_conn.close_connection()
    except:
        logging.error('Error occurred when handling message {}'.format(msg))


def handle_StartGameReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])

        with room.lock:
            room.handle_StartGameReq(msg, sender_conn)
    
    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        logging.debug(info)
        resp = mc.build_start_game_resp_not_ok(info)
        sender_conn.send(resp)

    except:
        logging.error('Error occurred when handling message {}'.format(msg))
        resp = mc.build_start_game_resp_not_ok()
        sender_conn.send(resp)


def handle_WordSelectionResp(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])

        with room.lock:
            room.handle_WordSelectionResp(msg)
    
    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        logging.error(info)
    
    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))


def handle_DrawStrokeReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])

        with room.lock:
            room.handle_DrawStrokeReq(msg)

    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        logging.error(info)
        
    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))


def handle_UndoLastStrokeReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])

        with room.lock:
            room.handle_UndoLastStrokeReq(msg)

    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        logging.error(info)

    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))


def handle_ClearCanvasReq(resources, sender_conn, msg):
    try:
        room = find_room(resources, msg['room_code'])

        with room.lock:
            room.handle_ClearCanvasReq(msg)
            
    except RoomNotExistsException:
        info = 'Room with code {} not found'.format(msg['room_code'])
        logging.error(info)

    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))


def handle_GameRoomListReq(resources, sender_conn, msg):
    try:
        info_list = []
        for room_code in resources['rooms']:
            room = find_room(resources, room_code)
            if not room.is_started():
                info_list.append(room.get_room_info())

        resp = mc.build_game_room_list_resp(info_list)
        sender_conn.send(resp)
    except:
        logging.error('Unknown error occurred when handling message {}'.format(msg))

import pytest
from Application.GameWindow import GameWindow
from Communication.ConnectionHandler import ConnectionHandler

# TODO: Replace unittest.mock with PyTestMock
from unittest.mock import Mock
import pytest


# for UT on windows(PowerShell):
# $env:PYTHONPATH = ".\Client\"
#
# pytest .\Client\Tests\
@pytest.fixture
def gameWindowFixutre(qtbot):
    connHandlerMock = Mock(spec=ConnectionHandler)
    client_context_dummy = {}
    client_context_dummy['username'] = 'test_user'
    client_context_dummy['roomCode'] = 'abcdefgh'
    sut = GameWindow(connHandlerMock)
    sut.initialize_room(client_context_dummy)
    qtbot.addWidget(sut)
    return sut


def _assert_that_chat_contains_message(message_content: dict, gameWindowFixutre):
    message_text = '{}: {}'.format(message_content['author'], message_content['message'])

    actual_chat_contents_after_first_chat_msg = '{}'.format(message_text)

    assert gameWindowFixutre.chat.toPlainText() == actual_chat_contents_after_first_chat_msg


def _assert_that_chat_contains_text(message_content: str, gameWindowFixutre):
    actual_chat_contents_after_first_chat_msg = '{}'.format(message_content)

    assert gameWindowFixutre.chat.toPlainText() == actual_chat_contents_after_first_chat_msg


def test_should_properly_display_user_msg_in_chat_and_clear_chat_entry_line(gameWindowFixutre):
    # fmt: off
    message_content = {
        'author': gameWindowFixutre.client_context['username'],
        'message': 'Hello Everybody'
    }
    # fmt: on

    message_text = '{}: {}'.format(message_content['author'], message_content['message'])

    gameWindowFixutre.chat_entry_line.setText(message_text)
    gameWindowFixutre.display_message(message_content)

    _assert_that_chat_contains_message(message_content, gameWindowFixutre)


def test_should_properly_display_server_announcement_message(gameWindowFixutre):
    # fmt: off
    message_from_server = {
        'author': 'SERVER',
        'message': 'A VERY IMPORTANT ANNOUNCEMENT FROM THE SERVER',
    }
    # fmt: on
    gameWindowFixutre.display_message(message_from_server)


def test_chat_entry_line_clears_after_adding_message_to_chat(gameWindowFixutre):
    # fmt: off
    chat_entry = {
        'author': gameWindowFixutre.client_context['username'],
        'message': 'Cat!'
    }
    # fmt: on
    gameWindowFixutre.chat_entry_line.setText(chat_entry['message'])
    gameWindowFixutre.display_user_message(chat_entry)

    _assert_that_chat_contains_message(chat_entry, gameWindowFixutre)


def test_game_start_displays_proper_chat_message(gameWindowFixutre):
    game_start_message = 'Game started!'
    gameWindowFixutre.display_system_message(game_start_message)
    _assert_that_chat_contains_text(game_start_message, gameWindowFixutre)

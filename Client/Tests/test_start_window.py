from Application.StartWindow import StartWindow
from Communication.ConnectionHandler import ConnectionHandler

# TODO: Replace unittest.mock with PyTestMock
from unittest.mock import Mock
import pytest

# for UT on windows(PowerShell):
# $env:PYTHONPATH = ".\Client\"
#
# pytest .\Client\Tests\


@pytest.fixture
def startWindowFixutre(qtbot):
    connHandlerMock = Mock(spec=ConnectionHandler)
    client_context_dummy = {}
    client_context_dummy['username'] = ''
    client_context_dummy['roomCode'] = ''
    sut = StartWindow(connHandlerMock, client_context_dummy)
    qtbot.addWidget(sut)
    return sut


def test_should_validate_nickname_and_fail_due_to_empty_value(startWindowFixutre, qtbot):
    assert startWindowFixutre.validate_nickname() == False


def test_should_successfully_validate_nickname(startWindowFixutre, qtbot):
    startWindowFixutre.nickname_field.setText('username')
    assert startWindowFixutre.validate_nickname() == True


def test_should_validate_room_code_and_fail_due_to_empty_value(startWindowFixutre, qtbot):
    assert startWindowFixutre.validate_room_code() == False


def test_should_validate_room_code_and_fail_due_to_code_too_short(startWindowFixutre, qtbot):
    startWindowFixutre.room_code_field.setText('abcde')
    assert startWindowFixutre.validate_room_code() == False


def test_should_successfully_validate_room_code(startWindowFixutre, qtbot):
    startWindowFixutre.room_code_field.setText('abcdefgh')
    assert startWindowFixutre.validate_room_code() == True

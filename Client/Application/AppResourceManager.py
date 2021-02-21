from .GameWindow import GameWindow
from .StartWindow import StartWindow


class AppResourceManager:
    def __init__(self, connection_handler):
        self.connection_handler = connection_handler
        self.client_context = {}
        self.client_context['username'] = ''
        self.client_context['roomCode'] = ''
        self.start_window = StartWindow(self.connection_handler, self.client_context)
        self.game_window = GameWindow(self.connection_handler)
        self.connection_handler.switch_window.connect(self.show_game)
        self.start_window.show()

    def show_start(self):
        if self.start_window is not None:
            if self.game_window is not None and self.game_window.isVisible():
                self.game_window.hide()
            self.start_window.setVisible(True)

    def show_game(self, room_code):
        if room_code != 'Joining':
            self.client_context['roomCode'] = room_code

        self.game_window.initialize_room(self.client_context)
        self.game_window.switch_window.connect(self.show_start)
        self.start_window.hide()
        self.game_window.show()


if __name__ == '__main__':
    pass

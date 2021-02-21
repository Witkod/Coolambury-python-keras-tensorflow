from PyQt5 import QtWidgets, QtCore
import logging


class WordSelectionWindow(QtWidgets.QWidget):
    prompt_locally_selected_signal = QtCore.pyqtSignal(dict)

    def __init__(self, words):
        super().__init__()
        self.words = words
        logging.debug(
            '[WordSelectionWindow] Window Initialization with words: {}'.format(self.words)
        )
        self.setWindowTitle('Choose your word')

        self.root_hBox = QtWidgets.QHBoxLayout()

        # This could be done better, like with a list of buttons. Similarly the event handlers for button clicks
        self.word_button_0 = QtWidgets.QPushButton(self.words[0])
        self.word_button_0.clicked.connect(self.word_button_0_clicked)
        self.root_hBox.addWidget(self.word_button_0)

        self.word_button_1 = QtWidgets.QPushButton(self.words[1])
        self.word_button_1.clicked.connect(self.word_button_1_clicked)
        self.root_hBox.addWidget(self.word_button_1)

        self.word_button_2 = QtWidgets.QPushButton(self.words[2])
        self.word_button_2.clicked.connect(self.word_button_2_clicked)
        self.root_hBox.addWidget(self.word_button_2)

        self.show()

        self.setLayout(self.root_hBox)
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

    # Do not rename
    def closeEvent(self, event):
        logging.debug('[WordSelectionWindow] Closing...')

    def word_button_0_clicked(self):
        self.prompt_locally_selected_signal.emit({'selected_word': self.words[0]})
        self.close()

    def word_button_1_clicked(self):
        self.prompt_locally_selected_signal.emit({'selected_word': self.words[1]})
        self.close()

    def word_button_2_clicked(self):
        self.prompt_locally_selected_signal.emit({'selected_word': self.words[2]})
        self.close()

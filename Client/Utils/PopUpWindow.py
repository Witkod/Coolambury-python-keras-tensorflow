from PyQt5 import QtWidgets, QtCore


class PopUpWindow(QtWidgets.QDialog):
    def __init__(self, message: str, type='WARNING'):
        super().__init__()
        self.setMinimumSize(200, 50)
        self.setWindowTitle(type)
        self.vBox = QtWidgets.QVBoxLayout()
        self.warningLabel = QtWidgets.QLabel(message)
        self.setLayout(self.vBox)
        self.vBox.addWidget(self.warningLabel)
        self.exec_()

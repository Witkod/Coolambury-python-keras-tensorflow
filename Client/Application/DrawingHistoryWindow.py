from PyQt5 import QtWidgets, QtGui


class DrawingHistoryWindow(QtWidgets.QWidget):
    def __init__(self, drawings):
        QtWidgets.QWidget.__init__(self)

        self.setWindowTitle('Drawing history')

        # Assumes drawings isn't empty
        # copy()?
        self.drawings = drawings
        self.index = 0

        # Window
        self.root_vBox = QtWidgets.QVBoxLayout()

        self.canvas = QtGui.QPixmap(400, 400)
        self.canvas.fill(QtGui.QColor('white'))

        self.canvas_container = QtWidgets.QLabel()
        self.canvas_container.setPixmap(self.canvas)
        self.root_vBox.addWidget(self.canvas_container)

        self.controls_hBox = QtWidgets.QHBoxLayout()
        self.root_vBox.addLayout(self.controls_hBox)

        self.previous_button = QtWidgets.QPushButton('<')
        self.previous_button.clicked.connect(self.previous_clicked)
        self.previous_button.setDisabled(True)
        self.controls_hBox.addWidget(self.previous_button)

        self.save_button = QtWidgets.QPushButton('Save')
        self.save_button.clicked.connect(self.save_clicked)
        self.controls_hBox.addWidget(self.save_button)

        self.next_button = QtWidgets.QPushButton('>')
        self.next_button.clicked.connect(self.next_clicked)
        if len(self.drawings) == 1:
            self.next_button.setDisabled(True)
        self.controls_hBox.addWidget(self.next_button)

        self.setLayout(self.root_vBox)
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        self.draw()

        self.show()

    # TODO: in stead of a label as canvasContainer make a Canvas(QtWidgets.Label) class that handles all drawing?
    def draw(self):
        strokes = self.drawings[self.index]
        painter = QtGui.QPainter(self.canvas_container.pixmap())
        self.configurePen(painter)
        painter.eraseRect(0, 0, self.canvas.width(), self.canvas.height())
        for stroke in strokes:
            for i in range(len(stroke) - 1):
                painter.drawLine(stroke[i][0], stroke[i][1], stroke[i + 1][0], stroke[i + 1][1])
        painter.end()
        self.update()

    def configurePen(self, painter):
        pen = painter.pen()
        pen.setWidth(4)
        pen.setColor(QtGui.QColor('black'))
        painter.setPen(pen)

    def previous_clicked(self):
        self.index -= 1
        if self.index == 0:
            self.previous_button.setDisabled(True)
        self.next_button.setDisabled(False)
        self.draw()

    def next_clicked(self):
        self.index += 1
        if self.index == len(self.drawings) - 1:
            self.next_button.setDisabled(True)
        self.previous_button.setDisabled(False)
        self.draw()

    def save_clicked(self):
        # TODO: fix up the PNG filtering thing
        dialog_result = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Drawing', '.', 'PNG', 'PNG'
        )
        filename = dialog_result[0] + '.png'
        self.canvas_container.pixmap().save(filename, 'png')

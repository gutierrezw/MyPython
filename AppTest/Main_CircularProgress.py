import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Mainwindow(QMainWindow):
    def __int__(self):
        QMainWindow.__init__(self)
        self.resize(500, 500)

        self.container = QFrame()
        self.container.style("background-color=#222222")
        self.layout = QVBoxLayout()

        self.progress = CircularProgress()

        self.layout.addWidget(self.progress, Qt.AlignCenter, Qt.AlignCenter)

        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        self.show()


if __name__ == "__main__":
    app =QApplication(sys.argv)
    window = Mainwindow()
    sys.exit(app.exec())

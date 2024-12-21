import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from circular_progress import *


class CircularProgress(QWidget):
    def __int__(self):
        QWidget.__init__(self)

        self.value = 0
        self.width = 200
        self.height = 200
        self.progress_width = 10
        self.progress_rounded_cap = True
        self.progress_color = 0x498BD1
        self.max_value = 100
        self.font_family = "Segoe UI"
        self.suffix = "%"
        self.size = 12
        self.text_color = 0x498BD1
        self.enable_shadow = True

        self.resize(self.width, self.height)

    def paintEvent(self, *args, **kwargs):
        pass

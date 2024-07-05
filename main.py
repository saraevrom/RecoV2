#!/usr/bin/env python3
from application import PADAMOReco
from PyQt6.QtWidgets import QApplication
import sys


if __name__=="__main__":
    app = QApplication(sys.argv)
    main_window = PADAMOReco()
    main_window.show()
    app.exec()

import sys
from PyQt6.QtWidgets import QApplication

from lada.gui.qt_window import MainWindow
from lada import VERSION

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lada")
    app.setApplicationVersion(VERSION)
    
    window = MainWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 
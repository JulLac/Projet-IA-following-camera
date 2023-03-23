import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

from interfaceQT import InterfaceQT

if __name__ == '__main__':
    app = QApplication(sys.argv)
    my_interface = InterfaceQT()
    my_interface.show()
    sys.exit(app.exec_())


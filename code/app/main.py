import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

# tell interpreter where to look
sys.path.insert(0,"..")
from gui.interfaceQT import InterfaceQT


if __name__ == '__main__':
    app = QApplication(sys.argv)
    my_interface = InterfaceQT()
    my_interface.show()
    sys.exit(app.exec_())


from MainWindow import *
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QDialog,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QToolButton, QFormLayout, QScrollArea, QFrame,
    QCheckBox
)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
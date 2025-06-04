from PyQt6.QtWidgets import QPushButton

class StyledButton(QPushButton):
    """Стилизованная кнопка для повторного использования"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #E9967A;
                border: 2px solid #E9967A;
                margin: 5px;
                min-width: 100px;
                min-height: 30px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
            }
        """)
from PyQt6.QtWidgets import QToolButton

class HelpToolButton(QToolButton):
    """Кнопка с вопросиком для подсказки"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("?")
        self.setStyleSheet("""
            QToolButton {
                background-color: #1E1E1E;
                color: #FF69B4;
                border: 1px solid #FF69B4;
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #2E2E2E;
            }
        """)
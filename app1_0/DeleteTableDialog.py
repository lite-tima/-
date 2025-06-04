from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QDialog,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QToolButton, QFormLayout, QScrollArea, QFrame,
    QCheckBox
)
from PyQt6.QtCore import Qt
import sqlite3
from StyledButton import *

class DeleteTableDialog(QDialog):
    """Диалоговое окно для удаления таблицы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Удаление таблицы")
        # Увеличиваем размер окна (было 400x200, стало 500x250)
        self.setFixedSize(500, 250)  # <-- Изменение размера здесь
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #E9967A;
            }
            QLabel {
                font-size: 14px;
            }
            QComboBox {
                background-color: #252525;
                color: #E0E0E0;
                border: 1px solid #E9967A;
                padding: 5px;
                min-height: 25px;
                min-width: 200px;  # <-- Добавлено для увеличения комбобокса
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        # Увеличиваем отступы (было 20, стало 30)
        layout.setContentsMargins(30, 30, 30, 30)  # <-- Изменение отступов здесь
        layout.setSpacing(20)

        # Заголовок
        title_label = QLabel("Выберите таблицу для удаления:")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")  # <-- Увеличена надпись
        layout.addWidget(title_label)

        # Выбор таблицы
        self.table_combo = QComboBox()
        self.table_combo.addItems(self.get_existing_tables())
        self.table_combo.setPlaceholderText("Выберите таблицу")
        layout.addWidget(self.table_combo, alignment=Qt.AlignmentFlag.AlignCenter)  # <-- Центрирование
        # Предупреждение - теперь многострочное с увеличенным шрифтом
        warning_label = QLabel(
            "ВНИМАНИЕ! Это действие невозможно отменить.\n\n"
            "Все данные в выбранной таблице будут\n"
            "безвозвратно утеряны."
        )
        warning_label.setStyleSheet("""
            color: #FF4500; 
            font-style: italic;
            font-size: 15px;  # <-- Увеличен шрифт
            qproperty-alignment: AlignCenter;
        """)
        warning_label.setWordWrap(True)  # <-- Перенос слов
        layout.addWidget(warning_label)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.delete_button = StyledButton("Удалить")
        self.delete_button.clicked.connect(self.confirm_deletion)
        cancel_button = StyledButton("Отмена")
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def get_existing_tables(self):
        """Получает список существующих таблиц"""
        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall() if table[0] != "sqlite_sequence"]
            conn.close()
            return tables
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка таблиц: {e}")
            return []

    def confirm_deletion(self):
        """Запрашивает подтверждение удаления"""
        table_name = self.table_combo.currentText()
        if not table_name:
            return

        # Создаем кастомное окно подтверждения с увеличенными кнопками
        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Подтверждение удаления")
        confirm_box.setText(
            f"Вы точно хотите удалить таблицу '{table_name}'?\n"
            "Это действие нельзя отменить!"
        )
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)


        # Увеличиваем размер текста
        confirm_box.setStyleSheet("""
            QLabel {
                font-size: 15px;
            }
            QPushButton {
                min-width: 80px;
                min-height: 30px;
                font-size: 14px;
            }
        """)

        if confirm_box.exec() == QMessageBox.StandardButton.Yes:
            bd_file = 'school_schedule.db'
            conn = sqlite3.connect(bd_file)
            cursor = conn.cursor()
            cursor.execute(f'DROP TABLE {table_name}')
            conn.commit()
            conn.close()
            self.accept()
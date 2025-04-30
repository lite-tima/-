import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QDialog,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QToolButton, QFormLayout, QScrollArea, QFrame,
    QCheckBox
)
from PyQt6.QtCore import Qt
from HelpToolButton import *
from StyledButton import *

class AddTableWindow(QDialog):
    """Окно для добавления новой таблицы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить таблицу")
        self.setFixedSize(700, 500)

        # Инициализируем переменные
        self.current_column_count = 0  # Добавляем инициализацию счетчика
        self.column_widgets = []  # Инициализируем список виджетов
        self.available_tables = self.get_existing_tables()

        self.setup_ui()
        self.setup_styles()
    def setup_ui(self):
        """Настройка интерфейса окна"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.scroll_layout = QVBoxLayout(content_widget)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)

        # Секция названия таблицы
        table_name_layout = QFormLayout()
        table_name_layout.setHorizontalSpacing(15)
        table_name_layout.setVerticalSpacing(15)

        self.table_name_input = QLineEdit()
        self.table_name_input.setPlaceholderText("название таблицы")
        table_name_layout.addRow("Название таблицы:", self.table_name_input)
        self.scroll_layout.addLayout(table_name_layout)

        # Чекбокс для связей таблиц
        self.relations_checkbox = QCheckBox("Связки таблиц")
        self.relations_checkbox.stateChanged.connect(self.toggle_relations_visibility)
        self.scroll_layout.addWidget(self.relations_checkbox)

        # Заголовок "Столбцы таблицы"
        columns_label = QLabel("Столбцы таблицы:")
        columns_label.setStyleSheet("font-weight: bold;")
        self.scroll_layout.addWidget(columns_label)

        # Кнопка "Добавить столбец"
        add_row_btn = StyledButton("Добавить столбец")
        add_row_btn.clicked.connect(self.add_new_column)
        self.scroll_layout.addWidget(add_row_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Добавляем первый столбец
        self.add_column_row()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        ok_button = StyledButton("Создать")
        ok_button.clicked.connect(self.accept)
        cancel_button = StyledButton("Отмена")
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def setup_styles(self):
        """Настройка стилей окна"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #FF69B4;
            }
            QLineEdit, QComboBox {
                background-color: #252525;
                color: #E0E0E0;
                border: 1px solid #FF69B4;
                padding: 5px;
                min-height: 25px;
            }
            QLabel {
                min-width: 180px;
            }
            QScrollArea {
                border: none;
            }
            QFrame#separator {
                border: 1px solid #FF69B4;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QCheckBox {
                spacing: 5px;
            }
        """)

    def get_existing_tables(self):
        """Получает список существующих таблиц из базы данных"""
        try:
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            conn.close()
            return tables
        except:
            return []

    def get_table_columns(self, table_name):
        """Получает список столбцов для указанной таблицы"""
        try:
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            conn.close()
            return columns
        except:
            return []

    def toggle_relations_visibility(self, state):
        """Показывает/скрывает поля для связей"""
        for widget in self.column_widgets:
            if 'relations_widget' in widget:
                widget['relations_widget'].setVisible(state == Qt.CheckState.Checked.value)

    def add_column_row(self):
        """Добавляет строку для нового столбца"""
        self.current_column_count += 1
        column_number = self.current_column_count

        # Создаем layout для одной строки столбца
        column_layout = QVBoxLayout()
        column_layout.setSpacing(5)

        # Верхний ряд (название и тип)
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Поле для названия столбца
        column_name_input = QLineEdit()
        column_name_input.setPlaceholderText(f"название столбца {column_number}")

        # Выбор типа данных
        column_type_combo = QComboBox()
        column_type_combo.addItems(["NULL", "INTEGER", "REAL", "TEXT", "BLOB", "NUMERIC"])
        column_type_combo.setCurrentIndex(3)
        column_type_combo.setPlaceholderText("тип данных")

        # Кнопка помощи
        help_button = HelpToolButton()
        help_button.setToolTip(
            "NULL — отсутствие значения\n"
            "INTEGER — целое число (1, 2, 3, 4, 6 или 8 байт)\n"
            "REAL — число с плавающей точкой (8 байт)\n"
            "TEXT — строка текста (UTF-8/UTF-16)\n"
            "BLOB — двоичные данные (изображения, аудио и др.)\n"
            "NUMERIC — может хранить данные всех типов"
        )
        help_button.setToolTipDuration(10000)

        top_row.addWidget(column_name_input)
        top_row.addWidget(column_type_combo)
        top_row.addWidget(help_button)

        column_layout.addLayout(top_row)

        # Секция для связей (изначально скрыта)
        relations_widget = QWidget()
        relations_widget.setVisible(False)
        relations_layout = QHBoxLayout()
        relations_layout.setContentsMargins(20, 0, 0, 0)
        relations_layout.setSpacing(10)

        relations_label = QLabel("Связи:")
        relations_label.setStyleSheet("font-style: italic;")

        # Комбобокс для выбора таблицы
        table_combo = QComboBox()
        table_combo.addItem("")
        table_combo.addItems(self.available_tables)
        table_combo.setPlaceholderText("Связываемая Таблица")

        # Комбобокс для выбора столбца
        column_combo = QComboBox()
        column_combo.setPlaceholderText("Столбец таблицы")
        column_combo.setEnabled(False)  # Изначально выключен

        # Связываем выбор таблицы с обновлением столбцов
        table_combo.currentTextChanged.connect(lambda table, combo=column_combo: self.update_column_combo(table, combo))

        relations_layout.addWidget(relations_label)
        relations_layout.addWidget(table_combo)
        relations_layout.addWidget(column_combo)

        relations_widget.setLayout(relations_layout)
        column_layout.addWidget(relations_widget)

        # Добавляем строку столбца в основной layout
        self.column_widgets.append({
            'name_input': column_name_input,
            'type_combo': column_type_combo,
            'relations_widget': relations_widget,
            'table_combo': table_combo,
            'column_combo': column_combo
        })

        # Вставляем перед кнопками управления
        self.scroll_layout.insertLayout(self.scroll_layout.count() - 1, column_layout)

    def update_column_combo(self, table_name, column_combo):
        """Обновляет комбобокс с колонками при выборе таблицы"""
        column_combo.clear()
        column_combo.setEnabled(False)

        if table_name:
            columns = self.get_table_columns(table_name)
            if columns:
                column_combo.addItems(columns)
                column_combo.setEnabled(True)

    def add_new_column(self):
        """Добавляет новую строку для столбца"""
        self.add_column_row()
        if self.current_column_count > 3:
            self.setFixedHeight(min(700, 500 + (self.current_column_count - 3) * 80))

    def get_inputs(self):
        """Возвращает введенные данные"""
        columns = []
        relations = []

        for i, widget in enumerate(self.column_widgets, 1):
            col_name = widget['name_input'].text()
            col_type = widget['type_combo'].currentText()
            columns.append((f"Столбец {i}", col_name, col_type))

            if self.relations_checkbox.isChecked():
                table_name = widget['table_combo'].currentText()
                column_name = widget['column_combo'].currentText()
                if table_name and column_name:
                    relations.append({
                        'column': col_name,
                        'foreign_table': table_name,
                        'foreign_column': column_name
                    })

        return {
            "table_name": self.table_name_input.text(),
            "columns": columns,
            "relations": relations if self.relations_checkbox.isChecked() else []
        }

    def create_table_in_db(self):
        """Создает таблицу в базе данных на основе введенных данных"""
        inputs = self.get_inputs()
        table_name = inputs["table_name"]
        cols = [col[1] for col in inputs["columns"]]
        cols_types = [col[2] for col in inputs["columns"]]

        # Подготовка данных для внешних ключей
        child_cols = []
        rel_lists = []
        parent_cols = []

        if inputs["relations"]:
            for rel in inputs["relations"]:
                child_cols.append(rel['column'])
                rel_lists.append(rel['foreign_table'])
                parent_cols.append(rel['foreign_column'])

        try:
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

            # Формируем основное определение таблицы
            column_defs = [f"{col} {dtype}" for col, dtype in zip(cols, cols_types)]

            # Добавляем внешние ключи
            fk_defs = []
            if child_cols:
                for child, parent_table, parent_col in zip(child_cols, rel_lists, parent_cols):
                    fk_defs.append(
                        f"FOREIGN KEY ({child}) REFERENCES {parent_table}({parent_col}) "
                        "ON DELETE SET NULL ON UPDATE CASCADE"
                    )

            # Объединяем все определения
            all_defs = column_defs + fk_defs
            create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(all_defs)})"

            cursor.execute(create_query)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")
            return False
        finally:
            conn.close()
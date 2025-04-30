import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QDialog,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QToolButton, QFormLayout, QScrollArea, QFrame,
    QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class DatabaseManager:
    @staticmethod
    def get_tables(db_name='schedule.db'):
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall() if table[0] != "sqlite_sequence"]
            conn.close()
            return tables
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка таблиц: {e}")
            return []

    @staticmethod
    def get_columns(table_name, db_name='schedule.db'):
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            conn.close()
            return columns
        except sqlite3.Error as e:
            print(f"Ошибка при получении столбцов таблицы: {e}")
            return []

class StyledButton(QPushButton):
    """Стилизованная кнопка для повторного использования"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #FF69B4;
                border: 2px solid #FF69B4;
                margin: 5px;
                min-width: 100px;
                min-height: 30px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
            }
        """)


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


class AddRecordDialog(QDialog):
    """Диалоговое окно для добавления новой таблицы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Добавить таблицу")
        self.setFixedSize(700, 500)
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

        self.column_widgets = []
        self.current_column_count = 0
        self.available_tables = self.get_existing_tables()

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

        # Затем заголовок "Столбцы таблицы"
        columns_label = QLabel("Столбцы таблицы:")
        columns_label.setStyleSheet("font-weight: bold;")
        self.scroll_layout.addWidget(columns_label)


        # Сначала добавляем кнопку "Добавить столбец"
        add_row_btn = StyledButton("Добавить столбец")
        add_row_btn.clicked.connect(self.add_new_column)
        self.scroll_layout.addWidget(add_row_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Затем добавляем первый столбец
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
                color: #FF69B4;
            }
            QLabel {
                font-size: 14px;
            }
            QComboBox {
                background-color: #252525;
                color: #E0E0E0;
                border: 1px solid #FF69B4;
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
            conn = sqlite3.connect('schedule.db')
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
            self.accept()


class EditTableDialog(QDialog):
    """Диалоговое окно для изменения существующей таблицы"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_states = {}  # Хранит состояния всех таблиц
        self.current_table = None  # Текущая редактируемая таблица
        self.permanent_widgets = []  # Виджеты, которые не должны удаляться
        self.setWindowTitle("Редактирование таблицы")
        self.setFixedSize(700, 500)

        # Стилизация
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #FF69B4;
            }
            QLabel {
                font-size: 14px;
            }
            QComboBox, QLineEdit {
                background-color: #252525;
                color: #E0E0E0;
                border: 1px solid #FF69B4;
                padding: 5px;
                min-height: 25px;
            }
            QPushButton {
                min-width: 120px;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Выбор таблицы для редактирования
        table_select_layout = QHBoxLayout()
        table_select_layout.addWidget(QLabel("Таблица для редактирования:"))

        self.table_combo = QComboBox()
        self.table_combo.addItems(self.get_existing_tables())
        self.table_combo.currentTextChanged.connect(self.load_table_structure)
        table_select_layout.addWidget(self.table_combo)

        main_layout.addLayout(table_select_layout)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("border: 1px solid #FF69B4;")
        main_layout.addWidget(separator)

        # Область редактирования структуры
        self.edit_area = QScrollArea()
        self.edit_area.setWidgetResizable(True)
        self.edit_content = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_content)
        self.edit_layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок столбцов (постоянный виджет)
        columns_header = QLabel("Структура таблицы:")
        columns_header.setStyleSheet("font-weight: bold;")
        self.edit_layout.addWidget(columns_header)

        # Кнопка добавления столбца (постоянный виджет)
        self.add_column_btn = StyledButton("Добавить столбец")
        self.add_column_btn.clicked.connect(self.add_empty_column)
        self.edit_layout.addWidget(self.add_column_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Сохраняем ссылки на постоянные виджеты
        self.permanent_widgets = [columns_header, self.add_column_btn]

        self.edit_area.setWidget(self.edit_content)
        main_layout.addWidget(self.edit_area)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = StyledButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_changes)
        cancel_btn = StyledButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        # Загружаем данные первой таблицы, если она есть
        if self.table_combo.count() > 0:
            self.load_table_structure(self.table_combo.currentText())

    def save_current_table_state(self):
        """Сохраняет текущее состояние таблицы перед переключением"""
        if not self.current_table:
            return


        state = {
            'columns': [],
            'foreign_keys': []
        }

        # Проходим по всем строкам столбцов (начиная с индекса 2)
        for i in range(2, self.edit_layout.count()):
            item = self.edit_layout.itemAt(i)
            widget = item.widget()

            if widget and hasattr(widget, 'relations_check'):
                column_data = {
                    'name': widget.name_edit.text(),
                    'type': widget.type_combo.currentText(),
                    'notnull': widget.notnull_check.isChecked(),
                    'pk': widget.relations_check.isChecked(),
                    'relations_visible': widget.relations_widget.isVisible(),
                }

                # Если есть связи, сохраняем их
                if hasattr(widget, 'table_combo') and widget.table_combo.currentText():
                    column_data.update({
                        'foreign_table': widget.table_combo.currentText(),
                        'foreign_column': widget.column_combo.currentText()
                    })

                state['columns'].append(column_data)

        # Сохраняем состояние в словарь
        if state['columns']:
            self.table_states[self.current_table] = state

    def load_table_structure(self, table_name):
        """Загружает структуру выбранной таблицы"""
        # Сохраняем текущее состояние перед загрузкой новой таблицы
        if self.current_table:
            self.save_current_table_state()

        # Очищаем layout, кроме постоянных виджетов
        self.clear_layout_except_permanent()

        if not table_name:
            self.current_table = None
            return

        # Устанавливаем текущую таблицу
        self.current_table = table_name

        try:
            # Получаем структуру таблицы из БД
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            db_columns = cursor.fetchall()
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            db_foreign_keys = cursor.fetchall()
            conn.close()

            # Получаем сохраненное состояние (если есть)
            saved_state = self.table_states.get(table_name, {})

            # Создаем строки для каждого столбца
            for db_column in db_columns:
                col_name = db_column[1]
                col_type = db_column[2]
                col_notnull = bool(db_column[3])
                col_pk = bool(db_column[5])

                # Ищем сохраненные данные для этого столбца
                saved_column = next(
                    (col for col in saved_state.get('columns', []) if col['name'] == col_name),
                    None
                )

                # Получаем информацию о внешнем ключе из БД
                fk_info = self.get_fk_for_column(db_foreign_keys, col_name)

                # Создаем строку столбца
                self.add_column_row(
                    name=saved_column['name'] if saved_column else col_name,
                    type=saved_column['type'] if saved_column else col_type,
                    notnull=saved_column.get('notnull', col_notnull) if saved_column else col_notnull,
                    pk=saved_column.get('pk', col_pk) if saved_column else col_pk,
                    relations_visible=saved_column.get('relations_visible', fk_info is not None) if saved_column else (
                                fk_info is not None),
                    table_name=saved_column.get('foreign_table',
                                                fk_info['table'] if fk_info else '') if saved_column else (
                        fk_info['table'] if fk_info else ''),
                    column_name=saved_column.get('foreign_column',
                                                 fk_info['column'] if fk_info else '') if saved_column else (
                        fk_info['column'] if fk_info else '')
                )


        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить структуру таблицы:\n{str(e)}")

    def add_column_row(self, name="", type="TEXT", notnull=False, pk=False,
                       relations_visible=False, table_name="", column_name=""):
        """Добавляет строку для редактирования столбца"""
        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)

        # Верхний ряд (название, тип и флаги)
        top_row = QHBoxLayout()

        # Название столбца
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Название столбца")
        top_row.addWidget(name_edit)

        # Тип данных
        type_combo = QComboBox()
        type_combo.addItems(["NULL", "INTEGER", "REAL", "TEXT", "BLOB", "NUMERIC"])
        type_combo.setCurrentText(type)
        top_row.addWidget(type_combo)

        # Флаги
        notnull_check = QCheckBox("NOT NULL")
        notnull_check.setChecked(notnull)
        top_row.addWidget(notnull_check)

        # Чекбокс для связей
        relations_check = QCheckBox("Связи с другими таблицами")
        relations_check.setChecked(pk)
        top_row.addWidget(relations_check)

        # Кнопка удаления
        delete_btn = QToolButton()
        delete_btn.setText("×")
        delete_btn.setStyleSheet("""
            QToolButton {
                color: #FF4500;
                font-weight: bold;
                font-size: 16px;
            }
            QToolButton:hover {
                color: #FF6347;
            }
        """)
        delete_btn.clicked.connect(lambda: self.remove_column_row(row_widget))
        top_row.addWidget(delete_btn)

        row_layout.addLayout(top_row)

        # Секция для связей
        relations_widget = QWidget()
        relations_layout = QHBoxLayout(relations_widget)
        relations_layout.setContentsMargins(20, 0, 0, 0)

        # Комбобокс для выбора таблицы
        table_combo = QComboBox()
        table_combo.addItem("")
        table_combo.addItems(self.get_other_tables())
        table_combo.setPlaceholderText("Выберите таблицу")
        if table_name:
            table_combo.setCurrentText(table_name)

        # Комбобокс для выбора столбца
        column_combo = QComboBox()
        column_combo.setPlaceholderText("Выберите столбец")
        column_combo.setEnabled(bool(table_name))
        if table_name:
            self.update_column_combo(table_name, column_combo)
            if column_name:
                column_combo.setCurrentText(column_name)

        # Связываем выбор таблицы с обновлением столбцов
        table_combo.currentTextChanged.connect(
            lambda table, combo=column_combo: self.update_column_combo(table, combo))

        relations_layout.addWidget(QLabel("Связать с:"))
        relations_layout.addWidget(table_combo)
        relations_layout.addWidget(column_combo)

        row_layout.addWidget(relations_widget)

        # Устанавливаем видимость в соответствии с параметром
        relations_widget.setVisible(relations_visible)
        relations_check.stateChanged.connect(
            lambda state, widget=relations_widget: widget.setVisible(state == Qt.CheckState.Checked.value))

        # Добавляем строку перед кнопкой "Добавить столбец"
        self.edit_layout.insertWidget(self.edit_layout.count() - 1, row_widget)

        # Сохраняем ссылки на виджеты
        row_widget.relations_widget = relations_widget
        row_widget.table_combo = table_combo
        row_widget.column_combo = column_combo
        row_widget.relations_check = relations_check
        row_widget.name_edit = name_edit
        row_widget.type_combo = type_combo
        row_widget.notnull_check = notnull_check


    def clear_layout_except_permanent(self):
        """Очищает layout, сохраняя постоянные виджеты"""
        items = []
        while self.edit_layout.count():
            item = self.edit_layout.takeAt(0)
            if item.widget() and item.widget() not in self.permanent_widgets:
                item.widget().deleteLater()
            else:
                items.append(item)

        for item in items:
            if item.widget():
                self.edit_layout.addWidget(item.widget())
                if item.widget() == self.add_column_btn:
                    self.edit_layout.setAlignment(item.widget(), Qt.AlignmentFlag.AlignLeft)
            else:
                self.edit_layout.addItem(item)

    def get_existing_tables(self):
        """Получает список существующих таблиц"""
        try:
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall() if table[0] != "sqlite_sequence"]
            conn.close()
            return tables
        except sqlite3.Error as e:
            print(f"Ошибка при получении списка таблиц: {e}")
            return []

    def get_fk_for_column(self, foreign_keys, column_name):
        """Возвращает информацию о внешнем ключе для столбца"""
        for fk in foreign_keys:
            if fk[3] == column_name:
                return {
                    'table': fk[2],
                    'column': fk[4]
                }
        return None

    def get_other_tables(self):
        """Получает список таблиц, исключая текущую"""
        current_table = self.table_combo.currentText()
        all_tables = self.get_existing_tables()
        return [table for table in all_tables if table != current_table and table != "sqlite_sequence"]

    def update_column_combo(self, table_name, column_combo):
        """Обновляет комбобокс с колонками при выборе таблицы"""
        column_combo.clear()
        column_combo.setEnabled(False)

        if table_name:
            columns = self.get_table_columns(table_name)
            if columns:
                column_combo.addItems(columns)
                column_combo.setEnabled(True)

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

    def add_empty_column(self):
        """Добавляет пустую строку для нового столбца"""
        insert_position = self.edit_layout.count() - 1
        self.add_column_row()
        self.edit_layout.insertWidget(insert_position, self.edit_layout.takeAt(insert_position + 1).widget())

    def remove_column_row(self, widget):
        """Удаляет строку столбца"""
        self.edit_layout.removeWidget(widget)
        widget.deleteLater()

    def save_changes(self):
        """Сохраняет изменения в таблице"""
        table_name = self.table_combo.currentText()
        if not table_name:
            QMessageBox.warning(self, "Ошибка", "Не выбрана таблица для редактирования")
            return

        # Собираем информацию о всех столбцах
        column_names = []
        types = []
        notnulls = []
        combos = []
        foreigns = []
        column_rel = []

        for i in range(1, self.edit_layout.count()):
            item = self.edit_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'name_edit'):
                    column_name = widget.name_edit.text()
                    if column_name:  # Проверяем, что имя столбца не пустое
                        column_names.append(column_name)
                if hasattr(widget, 'type_combo'):
                    typ = widget.type_combo.currentText()
                    types.append(typ)
                if hasattr(widget, 'notnull_check'):
                    g = widget.notnull_check.isChecked()
                    notnulls.append(g)
                if hasattr(widget, 'table_combo') and widget.table_combo.currentText():
                    column_name = widget.name_edit.text()
                    combo = widget.table_combo.currentText()
                    foreign = widget.column_combo.currentText()
                    column_rel.append(column_name)
                    combos.append(combo)
                    foreigns.append(foreign)

        self.update_the_table(table_name, column_names, types, notnulls, combos, foreigns, column_rel)

        # Можно также показать список в QMessageBox
        QMessageBox.information(
            self,
            "Список столбцов",
            f"Таблица: {table_name}\n\nСтолбцы:\n" + "\n".join(
                f"{i}. {name}" for i, name in enumerate(column_names, 1)),
            QMessageBox.StandardButton.Ok
        )

        # Здесь будет код для сохранения изменений в БД
        # Пока просто показываем сообщение
        QMessageBox.information(
            self,
            "Успех",
            f"Изменения в таблице '{table_name}' будут сохранены в БД",
            QMessageBox.StandardButton.Ok
        )
        self.accept()

    def update_the_table(db_name, table_name, column_names, types, notnulls, combos, foreigns, column_rel):
        """
        Обновляет таблицу в базе данных, заново записывая значения.

        :param db_name: Имя базы данных.
        :param table_name: Имя таблицы.
        :param column_names: Список имен столбцов.
        :param types: Список типов данных для столбцов (например, 'INTEGER', 'TEXT').
        :param notnulls: Список булевых значений, указывающих на NOT NULL для каждого столбца.
        :param combos: Список данных для вставки в таблицу.
        :param foreigns: Список имен столбцов внешних ключей.
        :param column_rel: Список с именами столбцов, которые имеют связи (внешние ключи).

        :return: None
        """
        # Подключаемся к базе данных
        conn = sqlite3.connect('schedule.db')
        cursor = conn.cursor()

        # Удаляем таблицу, если она существует
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Формируем основное определение таблицы
        column_defs = [f"{col} {dtype} {'NOT NULL' if null else 'NULL'}" for col, dtype, null in zip(column_names, types, notnulls)]

        # Добавляем внешние ключи
        fk_defs = []
        if foreigns:
            for child, parent_table, parent_col in zip(column_rel, foreigns, combos):
                fk_defs.append(f"FOREIGN KEY ({child}) REFERENCES {parent_table}({parent_col}) "
                               "ON DELETE SET NULL ON UPDATE CASCADE")

        # Объединяем все определения
        all_defs = column_defs + fk_defs
        create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(all_defs)})"

        try:
            cursor.execute(create_query)
            conn.commit()
            print(f"Таблица '{table_name}' успешно создана")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")
        finally:
            conn.commit()
            conn.close()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_dialog = None
        self.init_ui()

    def init_ui(self):
        """Инициализация главного окна"""
        self.setWindowTitle("Программа администратора")
        self.setFixedSize(400, 300)


        self.main_button = StyledButton("Возможности администратора")
        self.main_button.clicked.connect(self.show_admin_options)

        layout = QVBoxLayout()
        layout.addWidget(self.main_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #FF69B4;
                font-size: 14px;
            }
            QDialog {
                border: 1px solid #FF69B4;
            }
        """)

    def show_admin_options(self):
        """Окно с опциями администратора"""
        if self.current_dialog:
            self.current_dialog.close()

        dialog = QDialog(self)
        self.current_dialog = dialog
        dialog.setWindowTitle("Возможности администратора")
        dialog.setFixedSize(500, 150)

        layout = QHBoxLayout()


        button_placeholder = StyledButton("Функции в разработке")
        button_tables = StyledButton("Работа с таблицами")
        button_tables.clicked.connect(lambda: self.show_table_options(dialog))

        layout.addWidget(button_placeholder)
        layout.addWidget(button_tables)

        dialog.setLayout(layout)
        dialog.exec()

    def show_table_options(self, parent_dialog):
        """Окно работы с таблицами"""
        if parent_dialog:
            parent_dialog.close()

        dialog = QDialog(self)
        self.current_dialog = dialog
        dialog.setWindowTitle("Управление таблицами")
        dialog.setFixedSize(350, 200)

        layout = QGridLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        add_btn = StyledButton("Добавить")
        add_btn.clicked.connect(lambda: self.add_record(dialog))
        layout.addWidget(add_btn, 0, 0)

        edit_btn = StyledButton("Изменить")
        edit_btn.clicked.connect(self.edit_record)
        layout.addWidget(edit_btn, 0, 1)

        update_btn = StyledButton("Удалить")
        update_btn.clicked.connect(self.update_table)
        layout.addWidget(update_btn, 1, 0, 1, 2, Qt.AlignmentFlag.AlignHCenter)

        dialog.setLayout(layout)
        dialog.exec()

    def add_record(self, parent_dialog):
        """Обработчик кнопки 'Добавить'"""
        if parent_dialog:
            parent_dialog.close()

        dialog = AddRecordDialog(self)
        self.current_dialog = dialog


        if dialog.exec() == QDialog.DialogCode.Accepted:
            inputs = dialog.get_inputs()

            if not inputs["table_name"]:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Название таблицы не может быть пустым",
                    QMessageBox.StandardButton.Ok
                )
                return

            table_name = inputs["table_name"]
            cols = []
            cols_types = []
            child_cols = []
            rel_lists = []
            parent_cols = []

            empty_columns = [col[0] for col in inputs["columns"] if not col[1]]
            if empty_columns:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Следующие столбцы не имеют названия: {', '.join(empty_columns)}",
                    QMessageBox.StandardButton.Ok
                )
                return

            # Формируем информацию о таблице
            columns_info = "\n".join([f"{col[0]}: {col[1]} ({col[2]})" for col in inputs["columns"]])

            # сохранили информацию о столбцах
            for col in inputs["columns"]:
                cols.append(col[1])
                cols_types.append(col[2])


            # Добавляем информацию о связях, если они есть
            relations_info = ""
            if inputs["relations"]:
                relations_info = "\n\nСвязи:\n" + "\n".join(
                    [f"{rel['column']} → {rel['foreign_table']}.{rel['foreign_column']}"
                     for rel in inputs["relations"]]
                )

                # сохранили информацию о связях
                for rel in inputs["relations"]:
                    child_cols.append(rel['column'])
                    rel_lists.append(rel['foreign_table'])
                    parent_cols.append(rel['foreign_column'])

            #записали всё в БД
            self.add_table(table_name, cols, cols_types, child_cols, rel_lists, parent_cols)

            #вывели окошко как отчёт
            QMessageBox.information(
                self,
                "Успешно",
                f"Создана таблица: {inputs['table_name']}\n\n"
                f"Столбцы:\n{columns_info}"
                f"{relations_info}",
                QMessageBox.StandardButton.Ok
            )


    def add_table(self, name, cols, col_types, child_cols=None, rel_lists=None, parent_cols=None):
        """
        Создаёт таблицу в базе данных с возможностью указания внешних ключей

        :param name: имя таблицы
        :param cols: список столбцов
        :param col_types: список типов данных
        :param child_cols: столбцы с внешними ключами (опционально)
        :param rel_lists: родительские таблицы (опционально)
        :param parent_cols: столбцы в родительских таблицах (опционально)
        """
        if len(cols) != len(col_types):
            raise ValueError("Количество столбцов и типов данных должно совпадать!")

        if child_cols and (not rel_lists or not parent_cols):
            raise ValueError("Для внешних ключей укажите родительские таблицы и столбцы")

        if child_cols and (len(child_cols) != len(rel_lists) or len(child_cols) != len(parent_cols)):
            raise ValueError("Количество внешних ключей, родительских таблиц и столбцов должно совпадать")

        conn = sqlite3.connect('schedule.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Формируем основное определение таблицы
        column_defs = [f"{col} {dtype}" for col, dtype in zip(cols, col_types)]

        # Добавляем внешние ключи
        fk_defs = []
        if child_cols:
            for child, parent_table, parent_col in zip(child_cols, rel_lists, parent_cols):
                fk_defs.append(f"FOREIGN KEY ({child}) REFERENCES {parent_table}({parent_col}) "
                               "ON DELETE SET NULL ON UPDATE CASCADE")

        # Объединяем все определения
        all_defs = column_defs + fk_defs
        create_query = f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(all_defs)})"

        try:
            cursor.execute(create_query)
            conn.commit()
            print(f"Таблица '{name}' успешно создана")
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")
        finally:
            conn.close()

    def remove_column_row(self, widget):
        """Удаляет строку столбца с подтверждением"""
        # Получаем название столбца для сообщения
        column_name = ""
        for i in range(widget.layout().count()):
            child = widget.layout().itemAt(i).widget()
            if isinstance(child, QLineEdit):
                column_name = child.text()
                break

        # Формируем текст подтверждения
        confirm_text = f"Вы действительно хотите удалить столбец '{column_name}'?" if column_name else "Вы действительно хотите удалить этот столбец?"
        confirm_text += "\nЭто действие нельзя отменить!"


        # Создаем кастомное окно подтверждения
        confirm_box = QMessageBox(self)
        confirm_box.setWindowTitle("Подтверждение удаления")
        confirm_box.setText(confirm_text)
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Стилизуем окно подтверждения
        confirm_box.setStyleSheet("""
            QMessageBox {
                background-color: #1E1E1E;
                color: #FF69B4;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                min-width: 80px;
                min-height: 25px;
                background-color: #252525;
                color: #FF69B4;
                border: 1px solid #FF69B4;
            }
        """)

        # Показываем окно и обрабатываем результат
        if confirm_box.exec() == QMessageBox.StandardButton.Yes:
            self.edit_layout.removeWidget(widget)
            widget.deleteLater()

            # Показываем сообщение об успешном удалении, если было имя столбца
            if column_name:
                QMessageBox.information(
                    self,
                    "Столбец удален",
                    f"Столбец '{column_name}' был помечен для удаления.\nИзменения применятся после сохранения.",
                    QMessageBox.StandardButton.Ok
                )

    def edit_record(self):
        """Обработчик кнопки 'Изменить' - открывает диалог редактирования таблиц"""
        if self.current_dialog:
            self.current_dialog.close()

        # Проверяем, есть ли таблицы в базе данных
        try:
            conn = sqlite3.connect('schedule.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            conn.close()

            if not tables:
                QMessageBox.information(
                    self,
                    "Нет таблиц",
                    "В базе данных нет таблиц для редактирования.\nСначала создайте таблицу.",
                    QMessageBox.StandardButton.Ok
                )
                return
        except sqlite3.Error as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось проверить существующие таблицы:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return

        # Создаем и показываем диалог редактирования
        dialog = EditTableDialog(self)
        self.current_dialog = dialog

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Получаем имя таблицы, которую редактировали
            edited_table = dialog.table_combo.currentText()

            QMessageBox.information(
                self,
                "Изменения сохранены",
                f"Структура таблицы '{edited_table}' была успешно изменена.",
                QMessageBox.StandardButton.Ok
            )

    def update_table(self):
        """Обработчик кнопки 'Удалить'"""
        if self.current_dialog:
            self.current_dialog.close()

        dialog = DeleteTableDialog(self)
        self.current_dialog = dialog

        if dialog.exec() == QDialog.DialogCode.Accepted:
            table_name = dialog.table_combo.currentText()
            # Здесь будет передача команды на удаление таблицы в БД
            QMessageBox.information(
                self,
                "Таблица удалена",
                f"Таблица '{table_name}' была удалена.",
                QMessageBox.StandardButton.Ok
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
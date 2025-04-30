import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QDialog,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QToolButton, QFormLayout, QScrollArea, QFrame,
    QCheckBox
)
from PyQt6.QtCore import Qt
from StyledButton import *

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
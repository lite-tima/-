import sys
import os
from registration import LoginWindow
import win32com.client
import sqlite3
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QDialog, QMessageBox, QGroupBox, QGraphicsOpacityEffect
)
from datetime import datetime
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor


class MainWindow(QMainWindow):
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.setup_ui()
        self.setup_connections()
        self.load_tables_from_db()
        self.current_table_name = None
        self.new_rows = {}  # Словарь для хранения новых строк по таблицам

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setWindowTitle("Администратор: Управление данными школы")
        self.setFixedSize(1440, 980)

        # Основной стиль приложения
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QLabel {
                color: #E9967A;
            }
            QGroupBox {
                color: #E9967A;
                border: 1px solid #E9967A;
                margin-top: 10px;
                padding-top: 15px;
            }
            QTableWidget {
                background-color: #252525;
                color: #E0E0E0;
                gridline-color: #808080;  /* Горизонтальные линии */
                border: 1px solid #E9967A;
            }
            QHeaderView::section {
                background-color: #1E1E1E;
                color: #E9967A;
                padding: 5px;
                border: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #E9967A;
                color: black;
            }
            QPushButton {
                background-color: #1E1E1E;
                color: #E9967A;
                border: 1px solid #E9967A;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
            }
            QPushButton:checked {
                border: 2px solid #FBCEB1;
                font-weight: bold;
                color: #FBCEB1;
            }
        """)

        # Главный виджет и макет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Левая панель (информация пользователя и кнопки)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 20)
        left_layout.setSpacing(20)

        # Информация о пользователе
        user_info = QLabel(
            "<h3 style='color:#E9967A;'>Данные пользователя:</h3>"
            f"<p>Логин: <i>{self.username}</i></p>"
            "<p>Статус: <i>Админ</i></p>"
        )
        user_info.setFont(QFont("Arial", 12))
        left_layout.addWidget(user_info)

        # Кнопка составления расписания
        self.schedule_btn = QPushButton("Редактировать расписание")
        self.schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #CEA182;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FBCEB1;
            }
        """)
        left_layout.addWidget(self.schedule_btn)

        # Кнопка возможностей администратора
        self.admin_features_btn = QPushButton("Возможности администратора")
        self.admin_features_btn.setStyleSheet("""
            QPushButton {
                background-color: #CEA182;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FBCEB1;
            }
        """)
        left_layout.addWidget(self.admin_features_btn)
        self.edit_schedule = QPushButton("Изменить расписание")
        self.edit_schedule.setStyleSheet("""
                    QPushButton {
                        background-color: #CEA182;
                        color: black;
                        font-weight: bold;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #FBCEB1;
                    }
                """)
        left_layout.addWidget(self.edit_schedule)
        self.edit_schedule.clicked.connect(self.show_edit_table)
        # Время и дата
        left_layout.addStretch()
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.update_time()
        left_layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        # Правая панель (таблица и кнопки)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Панель кнопок для переключения таблиц
        self.tab_buttons = QHBoxLayout()
        self.tab_buttons.setSpacing(5)

        # Таблица
        # Настройка таблицы
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Скрываем вертикальные заголовки
        self.table.verticalHeader().setVisible(False)

        # Отключаем кнопку выбора всех строк
        self.table.setCornerButtonEnabled(True)

        # Стили таблицы
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #252525;
                color: #E0E0E0;
                gridline-color: #808080;
                border: 1px solid #E9967A;
            }
            QHeaderView {
                background-color: transparent;  /* Прозрачный фон */
            }
        """)
        # Добавляем красивый QLabel вместо corner-кнопки
        corner_label = QLabel("id", self.table)
        corner_label.setStyleSheet("""
            QLabel {
                background-color: #987055;
                color: black;
                font-weight: bold;
                border: 1px solid #E9967A;
                padding: 0px 5px;
                
            }
        """)
        corner_label.resize(41, 37)  # Размер метки
        corner_label.move(0, 0)  # Позиционируем в верхний левый угол
        corner_label.raise_()  # Поднимаем поверх других элементов
        # Кнопка добавления строки
        self.add_row_btn = QPushButton("Добавить строку")
        self.add_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #CEA182;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FBCEB1;
            }
        """)
        self.add_row_btn.clicked.connect(self.add_table_row)

        # Компоновка правой панели
        right_layout.addLayout(self.tab_buttons)
        right_layout.addWidget(self.table)
        right_layout.addWidget(self.add_row_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Добавляем панели на основное окно
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=3)

    def add_table_row(self):
        """Добавление новой строки в текущую таблицу"""
        if not self.current_table_name:
            return

        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Получаем информацию о столбцах таблицы
            cursor.execute(f"PRAGMA table_info({self.current_table_name})")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            column_types = [column[2] for column in columns]
            has_created_at = any(col[1].lower() == 'created_at' for col in columns)

            # Добавляем новую строку в таблицу
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Создаем словарь для значений по умолчанию
            default_values = {}

            # Определяем значения по умолчанию для разных типов столбцов
            for i, (name, type_) in enumerate(zip(column_names, column_types)):
                if name.lower() == 'id':
                    # Для ID получаем максимальное значение + 1
                    cursor.execute(f"SELECT MAX(id) FROM {self.current_table_name}")
                    max_id = cursor.fetchone()[0] or 0
                    default_values[i] = max_id + 1
                elif 'INTEGER' in type_:
                    default_values[i] = 0
                elif 'TEXT' in type_:
                    default_values[i] = ""
                elif 'REAL' in type_:
                    default_values[i] = 0.0
                else:
                    default_values[i] = ""

            # Заполняем строку в таблице
            for col in range(self.table.columnCount()):
                value = default_values.get(col, "")
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_position, col, item)

            # Помечаем строку как новую (еще не сохраненную в БД)
            if self.current_table_name not in self.new_rows:
                self.new_rows[self.current_table_name] = []
            self.new_rows[self.current_table_name].append(row_position)

            # Прокручиваем таблицу к новой строке
            self.table.scrollToBottom()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить строку: {str(e)}")
        finally:
            if conn:
                conn.close()

    def save_new_rows(self, table_name):
        """Сохранение новых строк в базу данных"""
        if table_name not in self.new_rows or not self.new_rows[table_name]:
            return

        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Проверяем наличие столбца created_at
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            has_created_at = any(col[1].lower() == 'created_at' for col in columns)

            # Получаем имена столбцов (исключая created_at, если он есть)
            column_names = [col[1] for col in columns if not has_created_at or col[1].lower() != 'created_at']

            for row in self.new_rows[table_name]:
                # Проверяем, заполнена ли строка (хотя бы одна ячейка не пустая)
                is_filled = any(
                    self.table.item(row, col) and self.table.item(row, col).text().strip()
                    for col in range(len(column_names)))

                if not is_filled:
                    continue  # Пропускаем пустые строки

                # Формируем данные для вставки
                row_data = [
                    self.table.item(row, col).text().strip()
                    if self.table.item(row, col) and self.table.item(row, col).text().strip()
                    else None
                    for col in range(len(column_names))
                ]

                # Формируем SQL запрос
                columns_str = ", ".join(column_names)
                placeholders = ", ".join(["?"] * len(column_names))

                query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                cursor.execute(query, row_data)

            conn.commit()
            QMessageBox.information(self, "Успех", "Данные успешно сохранены")

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            QMessageBox.critical(self, "Ошибка",
                                 f"Не удалось сохранить данные:\n{str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()
            if table_name in self.new_rows:
                del self.new_rows[table_name]

    def load_tables_from_db(self):
        """Загрузка списка таблиц из базы данных и создание кнопок для них"""
        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Получаем список всех таблиц в базе данных, исключая служебные и 'schedule'
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
                AND name NOT IN ('student_groups', 'schedule')  -- Исключаем таблицу с группами студентов и расписание
                ORDER BY name
            """)

            tables = [table[0] for table in cursor.fetchall()]

            # Очищаем предыдущие кнопки
            for i in reversed(range(self.tab_buttons.count())):
                widget = self.tab_buttons.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

            # Создаем кнопки для каждой таблицы
            self.buttons = []
            for table in tables:
                btn = QPushButton(self.translate_table_name(table))
                btn.setProperty('table_name', table)  # Сохраняем оригинальное имя таблицы
                btn.setCheckable(True)
                btn.clicked.connect(self.change_tab)
                self.tab_buttons.addWidget(btn)
                self.buttons.append(btn)

            if self.buttons:
                self.buttons[0].setChecked(True)
                self.current_table_name = self.buttons[0].property('table_name')
                self.update_table(self.current_table_name)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список таблиц: {str(e)}")
        finally:
            if conn:
                conn.close()

    def translate_table_name(self, table_name):
        """Перевод имен таблиц на русский"""
        translations = {
            'classes': 'Классы',
            'subjects': 'Предметы',
            'classrooms': 'Кабинеты',
            'teachers': 'Учителя',
            'teacher_subjects': 'Учителя-Предметы',
            'time_slots': 'Временные слоты',
            # 'schedule': 'Расписание'  # Эту строку можно удалить, так как мы исключаем таблицу
        }
        return translations.get(table_name, table_name)

    def setup_connections(self):
        """Настройка сигналов и слотов"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.table.itemChanged.connect(self.on_item_changed)
        self.schedule_btn.clicked.connect(self.show_schedule_window)
        self.admin_features_btn.clicked.connect(self.run_admin_features)
        #self.edit_schedule.clicked.connect(self.show_edit_table())

    def run_admin_features(self):
        """Запуск скрипта с возможностями администратора"""
        try:
            from MainWindow import MainWindow
            self.admin_window = MainWindow()
            self.admin_window.show()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить возможности администратора: {str(e)}")

    def show_schedule_window(self):
        """Показывает окно составления расписания"""
        try:
            # Создаем экземпляр класса ScheduleApp из модуля тимоха
            from тимоха import ScheduleApp
            self.schedule_window = ScheduleApp()
            self.schedule_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть расписание: {str(e)}")

    def change_tab(self):
        """Переключение между таблицами"""
        # Сохраняем новые строки из текущей таблицы перед переключением
        if self.current_table_name and self.current_table_name in self.new_rows:
            self.save_new_rows(self.current_table_name)

        sender = self.sender()
        table_name = sender.property('table_name')

        for btn in self.buttons:
            btn.setChecked(False)

        sender.setChecked(True)
        self.current_table_name = table_name
        self.update_table(table_name)

    def update_table(self, table_name):
        """Обновление таблицы в соответствии с выбранной вкладкой"""
        self.table.blockSignals(True)
        self.table.clear()

        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Получаем информацию о столбцах таблицы
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            headers = [column[1] for column in columns]
            has_created_at = any(col[1].lower() == 'created_at' for col in columns)

            # Получаем данные из таблицы
            cursor.execute(f"SELECT * FROM {table_name}")
            data = cursor.fetchall()

            # Настраиваем таблицу
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(data))

            # Настройка вертикальных заголовков (ID строк)
            self.table.verticalHeader().setVisible(True)
            self.table.verticalHeader().setDefaultSectionSize(30)
            self.table.verticalHeader().setStyleSheet("""
                QHeaderView::section {
                    background-color: #987055;
                    color: black;
                    border: 1px solid #333333;
                    padding: 8px;
                }
            """)

            # Заполняем таблицу данными
            for row_idx, row in enumerate(data):
                # Устанавливаем ID строки в вертикальный заголовок
                header_item = QTableWidgetItem(str(row_idx + 1))
                self.table.setVerticalHeaderItem(row_idx, header_item)

                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")

                    # Выравнивание текста по центру
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Устанавливаем цвет фона для четных/нечетных строк
                    if row_idx % 2 == 0:
                        item.setBackground(QColor(152, 112, 85))
                    else:
                        item.setBackground(QColor(200, 155, 135))

                    self.table.setItem(row_idx, col_idx, item)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные таблицы {table_name}: {str(e)}")
        finally:
            if conn:
                conn.close()
            self.table.blockSignals(False)

    def on_item_changed(self, item):
        """Обработка изменения данных в таблице"""
        row = item.row()
        col = item.column()

        if not self.current_table_name:
            return

        # Если строка не новая, обновляем ее в базе данных
        if self.current_table_name not in self.new_rows or row not in self.new_rows[self.current_table_name]:
            try:
                conn = sqlite3.connect('school_schedule.db')
                cursor = conn.cursor()

                # Получаем информацию о столбцах таблицы
                cursor.execute(f"PRAGMA table_info({self.current_table_name})")
                columns = cursor.fetchall()

                # Проверяем, что столбец существует
                if col >= len(columns):
                    return

                column_name = columns[col][1]

                # Получаем первичный ключ таблицы (предполагаем, что это первый столбец)
                if not columns:
                    return

                pk_column = columns[0][1]
                pk_item = self.table.item(row, 0)

                if not pk_item:
                     return

                pk_value = pk_item.text()

                # Обновляем данные в базе
                cursor.execute(f"""
                    UPDATE {self.current_table_name}
                    SET {column_name} = ?
                    WHERE {pk_column} = ?
                """, (item.text(), pk_value))

                # Для таблиц с триггерами обновления временных меток
                if self.current_table_name in ['classes', 'subjects', 'classrooms', 'teachers', 'time_slots']:
                    cursor.execute(f"""
                        UPDATE {self.current_table_name}
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE {pk_column} = ?
                    """, (pk_value,))

                conn.commit()

            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить данные: {str(e)}")
            except Exception as e:
                 QMessageBox.critical(self, "Ошибка", f"Произошла непредвиденная ошибка при обновлении данных: {str(e)}")
            finally:
                if conn:
                    conn.close()

    def update_time(self):
        """Обновление времени и даты"""
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        weekday = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][now.weekday()]
        month = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"][now.month - 1]
        date_str = f"{weekday}, {now.day} {month} {now.year}"
        self.time_label.setText(f"<b>{time_str}</b><br>{date_str}")
    def show_edit_table(self):
        from Edit_Schedule import ScheduleApp
        self.window = ScheduleApp()
        self.window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
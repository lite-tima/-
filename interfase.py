import sys
import sqlite3
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QDialog, QMessageBox, QGroupBox
)
from datetime import datetime
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor


class ScheduleWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Составление расписания")
        self.setFixedSize(1200, 800)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Группа для таблицы расписания
        schedule_group = QGroupBox("Расписание занятий")
        schedule_layout = QVBoxLayout()

        # Создаем таблицу расписания (5 уроков × 6 дней)
        self.schedule_table = QTableWidget(5, 6)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"])
        self.schedule_table.setVerticalHeaderLabels(["1", "2", "3", "4", "5"])

        # Настройка таблицы
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule_table.setStyleSheet("""
            QTableWidget {
                background-color: #252525;
                color: #E0E0E0;
                gridline-color: #808080;
                border: 1px solid #FF69B4;
            }
            QHeaderView::section {
                background-color: #1E1E1E;
                color: #FF69B4;
                padding: 5px;
                border: 1px solid #333333;
            }
        """)

        # Загружаем данные из базы данных
        self.load_schedule_data()

        schedule_layout.addWidget(self.schedule_table)
        schedule_group.setLayout(schedule_layout)

        # Панель управления
        control_panel = QHBoxLayout()

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить расписание")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF69B4;
                color: black;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF8FB3;
            }
        """)
        save_btn.clicked.connect(self.save_schedule)

        # Кнопка отмены
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E1E;
                color: #FF69B4;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #FF69B4;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
            }
        """)
        cancel_btn.clicked.connect(self.close)

        control_panel.addStretch()
        control_panel.addWidget(save_btn)
        control_panel.addWidget(cancel_btn)

        layout.addWidget(schedule_group)
        layout.addLayout(control_panel)

    def load_schedule_data(self):
        """Загрузка данных расписания из базы данных"""
        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Получаем данные из таблицы schedule
            cursor.execute("""
                SELECT s.day_of_week, ts.slot_number, subj.name, t.full_name, c.number, cl.name
                FROM schedule s
                JOIN time_slots ts ON s.time_slot_id = ts.id
                JOIN subjects subj ON s.subject_id = subj.id
                JOIN teachers t ON s.teacher_id = t.id
                JOIN classrooms c ON s.classroom_id = c.id
                JOIN classes cl ON s.class_id = cl.id
                WHERE s.week_number = 1  # Показываем только первую неделю
                ORDER BY s.day_of_week, ts.slot_number
            """)

            schedule_data = cursor.fetchall()

            # Заполняем таблицу данными
            for day, slot, subject, teacher, classroom, class_name in schedule_data:
                col = day - 1  # дни недели в базе от 1 до 6
                row = slot - 1  # слоты от 1 до 5

                if 0 <= row < 5 and 0 <= col < 6:
                    text = f"{subject} ({class_name})\n{teacher}, {classroom}"
                    item = QTableWidgetItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, (subject, teacher, classroom, class_name))
                    item.setBackground(QColor(60, 60, 60))
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                    self.schedule_table.setItem(row, col, item)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить расписание: {str(e)}")
        finally:
            if conn:
                conn.close()

    def save_schedule(self):
        """Сохранение изменений расписания в базу данных"""
        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Сначала очищаем текущее расписание (только для первой недели)
            cursor.execute("DELETE FROM schedule WHERE week_number = 1")

            # Сохраняем новые данные
            for row in range(self.schedule_table.rowCount()):
                for col in range(self.schedule_table.columnCount()):
                    item = self.schedule_table.item(row, col)
                    if item and item.text():
                        day_of_week = col + 1
                        time_slot_id = row + 1

                        # Получаем дополнительные данные из UserRole
                        user_data = item.data(Qt.ItemDataRole.UserRole)
                        if user_data:
                            subject_name, teacher_name, classroom_number, class_name = user_data
                        else:
                             # Если нет данных UserRole, пропускаем эту ячейку или обрабатываем ошибку
                             continue


                        # Получаем ID из базы данных
                        cursor.execute("SELECT id FROM subjects WHERE name = ?", (subject_name,))
                        subject_id = cursor.fetchone()[0]

                        cursor.execute("SELECT id FROM teachers WHERE full_name = ?", (teacher_name,))
                        teacher_id = cursor.fetchone()[0]

                        cursor.execute("SELECT id FROM classrooms WHERE number = ?", (classroom_number,))
                        classroom_id = cursor.fetchone()[0]

                        cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
                        class_id = cursor.fetchone()[0]

                        # Вставляем запись в расписание
                        cursor.execute("""
                            INSERT INTO schedule (
                                class_id, day_of_week, time_slot_id,
                                subject_id, teacher_id, classroom_id,
                                week_number
                            ) VALUES (?, ?, ?, ?, ?, ?, 1)
                        """, (class_id, day_of_week, time_slot_id, subject_id, teacher_id, classroom_id))

            conn.commit()
            QMessageBox.information(self, "Сохранено", "Расписание успешно сохранено в базу данных")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить расписание: {str(e)}")
        finally:
            if conn:
                conn.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.load_tables_from_db()
        self.current_table_name = None
        self.new_rows = {}  # Словарь для хранения новых строк по таблицам

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setWindowTitle("Администратор: Управление данными школы")
        self.setFixedSize(1200, 800)

        # Основной стиль приложения
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QLabel {
                color: #FF69B4;
            }
            QGroupBox {
                color: #FF69B4;
                border: 1px solid #FF69B4;
                margin-top: 10px;
                padding-top: 15px;
            }
            QTableWidget {
                background-color: #252525;
                color: #E0E0E0;
                gridline-color: #808080;
                border: 1px solid #FF69B4;
            }
            QHeaderView::section {
                background-color: #1E1E1E;
                color: #FF69B4;
                padding: 5px;
                border: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #FF69B4;
                color: black;
            }
            QPushButton {
                background-color: #1E1E1E;
                color: #FF69B4;
                border: 1px solid #FF69B4;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
            }
            QPushButton:checked {
                border: 2px solid #FF69B4;
                font-weight: bold;
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
            "<h3 style='color:#FF69B4;'>Данные пользователя:</h3>"
            "<p>Логин: <i>Шаура Фуатовна</i></p>"
            "<p>Статус: <i>Админ</i></p>"
        )
        user_info.setFont(QFont("Arial", 12))
        left_layout.addWidget(user_info)

        # Кнопка составления расписания
        self.schedule_btn = QPushButton("Редактировать расписание")
        self.schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF69B4;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FF8FB3;
            }
        """)
        left_layout.addWidget(self.schedule_btn)

        # Кнопка возможностей администратора
        self.admin_features_btn = QPushButton("Возможности администратора")
        self.admin_features_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF69B4;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FF8FB3;
            }
        """)
        left_layout.addWidget(self.admin_features_btn)


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
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        # Кнопка добавления строки
        self.add_row_btn = QPushButton("Добавить строку")
        self.add_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF69B4;
                color: black;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF8FB3;
            }
        """)
        self.add_row_btn.clicked.connect(self.add_table_row)

        right_layout.addLayout(self.tab_buttons)
        right_layout.addWidget(self.table)
        right_layout.addWidget(self.add_row_btn, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=3)

    def add_table_row(self):
        """Добавление новой строки в текущую таблицу"""
        if not self.current_table_name:
            return

        # Получаем количество столбцов
        column_count = self.table.columnCount()
        if column_count == 0:
            return

        # Добавляем новую строку
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        # Заполняем ячейки пустыми значениями
        for col in range(column_count):
            item = QTableWidgetItem("")
            self.table.setItem(row_position, col, item)

        # Помечаем строку как новую (еще не сохраненную в БД)
        if self.current_table_name not in self.new_rows:
            self.new_rows[self.current_table_name] = []
        self.new_rows[self.current_table_name].append(row_position)

        # Прокручиваем таблицу к новой строке
        self.table.scrollToBottom()


    def save_new_rows(self, table_name):
        """Сохранение новых строк в базу данных"""
        if table_name not in self.new_rows or not self.new_rows[table_name]:
            return

        try:
            conn = sqlite3.connect('school_schedule.db')
            cursor = conn.cursor()

            # Получаем информацию о столбцах таблицы
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]

            for row in self.new_rows[table_name]:
                # Проверяем, заполнена ли строка (хотя бы одна ячейка не пустая)
                is_filled = False
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and item.text().strip():
                        is_filled = True
                        row_data.append(item.text().strip())
                    else:
                        row_data.append(None)

                if not is_filled:
                    continue  # Пропускаем пустые строки

                # Формируем запрос на вставку
                columns_str = ", ".join(column_names)
                placeholders = ", ".join(["?"] * len(column_names))
                query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

                # Выполняем запрос
                cursor.execute(query, row_data)

            conn.commit()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить новые строки: {str(e)}")
        finally:
            if conn:
                conn.close()

            # Очищаем сохраненные строки для этой таблицы
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

    def run_admin_features(self):
        """Запуск скрипта с возможностями администратора"""
        try:
            # Создаем скрипт для запуска
            script = """
from MainWindow import *
import sys
from PyQt6.QtWidgets import (
    QApplication
)
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
            """

            # Сохраняем скрипт во временный файл
            with open("admin_features.py", "w", encoding="utf-8") as f:
                f.write(script)

            # Запускаем скрипт в новом процессе
            subprocess.Popen([sys.executable, "admin_features.py"])

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить возможности администратора: {str(e)}")


    def show_schedule_window(self):
        """Показывает окно составления расписания"""
        schedule_window = ScheduleWindow(self)
        schedule_window.exec()

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

            # Получаем данные из таблицы
            cursor.execute(f"SELECT * FROM {table_name}")
            data = cursor.fetchall()

            # Получаем названия столбцов
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            headers = [column[1] for column in columns]

            # Настраиваем таблицу
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(data))

            # Заполняем таблицу данными
            for row_idx, row in enumerate(data):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
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
                    print(f"Ошибка: Индекс столбца {col} выходит за пределы для таблицы {self.current_table_name}")
                    return

                column_name = columns[col][1]

                # Получаем первичный ключ таблицы (предполагаем, что это первый столбец)
                if not columns:
                    print(f"Ошибка: Не удалось получить информацию о столбцах для таблицы {self.current_table_name}")
                    return

                pk_column = columns[0][1]
                pk_item = self.table.item(row, 0)

                if not pk_item:
                     print(f"Ошибка: Не удалось получить значение первичного ключа для строки {row} в таблице {self.current_table_name}")
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

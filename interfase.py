import sys
import sqlite3
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

        # Создаем таблицу расписания (7 уроков × 6 дней)
        self.schedule_table = QTableWidget(7, 6)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"])
        self.schedule_table.setVerticalHeaderLabels(["1", "2", "3", "4", "5", "6", "7"])

        # Настройка таблицы
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.schedule_table.setStyleSheet("""
            QTableWidget {
                background-color: #252525;
                color: #E0E0E0;
                gridline-color: #333333;
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
        save_btn = QPushButton("Сохранить в schedule.db")
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
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()

            # Получаем данные расписания
            cursor.execute("SELECT weekday, lesson_number, subject FROM schedule")
            schedule_data = cursor.fetchall()

            # Заполняем таблицу данными
            for weekday, lesson_number, subject in schedule_data:
                # Преобразуем день недели в индекс столбца
                weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
                col = weekdays.index(weekday)
                row = lesson_number - 1  # уроки нумеруются с 1

                if 0 <= row < 7 and 0 <= col < 6:
                    item = QTableWidgetItem(subject)
                    item.setBackground(QColor(60, 60, 60))
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
                    self.schedule_table.setItem(row, col, item)
                    self.setup_tooltip(item, row, col)

        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные расписания: {str(e)}")
        finally:
            if conn:
                conn.close()

    def setup_tooltip(self, item, row, col):
        """Настраиваем подсказку для ячейки таблицы"""
        day = self.schedule_table.horizontalHeaderItem(col).text()
        lesson_num = self.schedule_table.verticalHeaderItem(row).text()
        subject = item.text()

        try:
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()

            # Получаем дополнительные данные о занятии
            cursor.execute("""
                SELECT teacher, classroom, class 
                FROM schedule 
                WHERE weekday = ? AND lesson_number = ? AND subject = ?
            """, (day, row + 1, subject))

            result = cursor.fetchone()

            if result:
                teacher, classroom, class_ = result
                tooltip = (
                    f"<b>Урок {lesson_num}, {day}</b><br><br>"
                    f"Предмет: {subject.split('(')[0].strip()}<br>"
                    f"Класс: {class_}<br>"
                    f"Кабинет: {classroom}<br>"
                    f"Учитель: {teacher}"
                )
            else:
                tooltip = f"<b>Урок {lesson_num}, {day}</b><br><br>Нет данных"

            item.setToolTip(tooltip)

        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные для подсказки: {str(e)}")
        finally:
            if conn:
                conn.close()

    def save_schedule(self):
        """Сохранение расписания в базу данных"""
        try:
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()

            # Сначала очистим таблицу расписания
            cursor.execute("DELETE FROM schedule")

            # Заполняем таблицу данными из QTableWidget
            for row in range(self.schedule_table.rowCount()):
                for col in range(self.schedule_table.columnCount()):
                    subject = self.schedule_table.item(row, col).text() if self.schedule_table.item(row, col) else ""
                    if subject:
                        weekday = self.schedule_table.horizontalHeaderItem(col).text()
                        lesson_number = row + 1  # номера уроков начинаются с 1

                        # Получаем дополнительные данные из подсказки
                        tooltip = self.schedule_table.item(row, col).toolTip()
                        teacher = "Не указано"
                        classroom = "Не указано"
                        class_ = "Не указано"

                        if "Учитель:" in tooltip:
                            teacher = tooltip.split("Учитель:")[1].split("<")[0].strip()
                        if "Кабинет:" in tooltip:
                            classroom = tooltip.split("Кабинет:")[1].split("<")[0].strip()
                        if "Класс:" in tooltip:
                            class_ = tooltip.split("Класс:")[1].split("<")[0].strip()

                        cursor.execute('''
                            INSERT INTO schedule (weekday, lesson_number, subject, teacher, classroom, class)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (weekday, lesson_number, subject, teacher, classroom, class_))

            conn.commit()
            QMessageBox.information(
                self,
                "Сохранение",
                "Расписание успешно сохранено в базу данных school.db",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Произошла ошибка при сохранении данных: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
        finally:
            if conn:
                conn.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.load_tables_from_db()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setWindowTitle("Администратор: Управление данными")
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
                gridline-color: #333333;
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
        self.schedule_btn = QPushButton("Начать составление расписания")
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

        right_layout.addLayout(self.tab_buttons)
        right_layout.addWidget(self.table)

        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=3)

    def load_tables_from_db(self):
        """Загрузка списка таблиц из базы данных и создание кнопок для них"""
        try:
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()

            # Получаем список всех таблиц в базе данных, исключая служебные
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
            """)
            tables = [table[0] for table in cursor.fetchall()]

            # Очищаем предыдущие кнопки
            for i in reversed(range(self.tab_buttons.count())):
                self.tab_buttons.itemAt(i).widget().setParent(None)

            # Создаем кнопки для каждой таблицы
            self.buttons = []
            for table in tables:
                btn = QPushButton(table)
                btn.setCheckable(True)
                btn.clicked.connect(self.change_tab)
                self.tab_buttons.addWidget(btn)
                self.buttons.append(btn)

            if self.buttons:
                self.buttons[0].setChecked(True)
                self.update_table(self.buttons[0].text())

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список таблиц: {str(e)}")
        finally:
            if conn:
                conn.close()

    def setup_connections(self):
        """Настройка сигналов и слотов"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.table.itemChanged.connect(self.on_item_changed)
        self.schedule_btn.clicked.connect(self.show_schedule_window)

    def show_schedule_window(self):
        """Показывает окно составления расписания"""
        schedule_window = ScheduleWindow(self)
        schedule_window.exec()

    def change_tab(self):
        """Переключение между таблицами"""
        sender = self.sender()

        for btn in self.buttons:
            btn.setChecked(False)

        sender.setChecked(True)
        self.update_table(sender.text())

    def update_table(self, table_name):
        """Обновление таблицы в соответствии с выбранной вкладкой"""
        self.table.blockSignals(True)
        self.table.clear()

        try:
            conn = sqlite3.connect('school.db')
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

        # Находим активную таблицу
        active_table = None
        for btn in self.buttons:
            if btn.isChecked():
                active_table = btn.text()
                break

        if not active_table:
            return

        try:
            conn = sqlite3.connect('school.db')
            cursor = conn.cursor()

            # Получаем информацию о столбцах таблицы
            cursor.execute(f"PRAGMA table_info({active_table})")
            columns = cursor.fetchall()
            column_name = columns[col][1]

            # Получаем первичный ключ таблицы (предполагаем, что это первый столбец)
            pk_column = columns[0][1]
            pk_value = self.table.item(row, 0).text()

            # Обновляем данные в базе
            cursor.execute(f"""
                UPDATE {active_table} 
                SET {column_name} = ? 
                WHERE {pk_column} = ?
            """, (item.text(), pk_value))

            conn.commit()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить данные: {str(e)}")
        finally:
            if conn:
                conn.close()

    def update_time(self):
        """Обновление времени и даты"""
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        weekday = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][now.weekday()]
        month = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"][now.month - 1]
        date_str = f"{weekday} // {now.day} {month}"
        self.time_label.setText(f"<b>{time_str}</b><br>{date_str}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

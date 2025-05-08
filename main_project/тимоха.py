import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QScrollArea, QPushButton, QDialog,
    QComboBox, QLineEdit, QFormLayout, QGridLayout, QStyledItemDelegate,
    QCompleter, QAbstractItemView, QMenu, QListView, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize, QSortFilterProxyModel, QStringListModel, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics, QIcon, QPixmap,
    QStandardItemModel, QStandardItem
)



class ClassSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка классов")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # Получаем список классов из базы данных
        self.db_conn = sqlite3.connect('school_schedule.db')
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название FROM Классы ORDER BY Название")
        existing_classes = [row[0] for row in cursor.fetchall()]

        # Создаем модель для списка классов
        self.model = QStringListModel()
        self.model.setStringList(existing_classes)

        # Виджет для отображения и редактирования списка классов
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        # Кнопки для управления списком
        button_layout = QHBoxLayout()
        add_button = QPushButton("Добавить")
        add_button.clicked.connect(self.add_class)
        remove_button = QPushButton("Удалить")
        remove_button.clicked.connect(self.remove_class)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)

        # Кнопки OK/Отмена
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_classes)
        button_box.rejected.connect(self.reject)

        layout.addWidget(QLabel("Список классов:"))
        layout.addWidget(self.list_view)
        layout.addLayout(button_layout)
        layout.addWidget(button_box)

    def add_class(self):
        """Добавляет новый класс в список"""
        row = self.model.rowCount()
        self.model.insertRow(row)
        index = self.model.index(row)
        self.list_view.setCurrentIndex(index)
        self.list_view.edit(index)

    def remove_class(self):
        """Удаляет выбранный класс из списка"""
        index = self.list_view.currentIndex()
        if index.isValid():
            self.model.removeRow(index.row())

    def save_classes(self):
        """Сохраняет изменения классов в базу данных"""
        try:
            cursor = self.db_conn.cursor()

            # Получаем текущий список классов из БД
            cursor.execute("SELECT Название FROM Классы")
            db_classes = {row[0] for row in cursor.fetchall()}

            # Получаем новые классы из модели
            new_classes = set(self.model.stringList())

            # Классы для добавления
            to_add = new_classes - db_classes
            for class_name in to_add:
                cursor.execute("INSERT INTO Классы (Название) VALUES (?)", (class_name,))

            # Классы для удаления
            to_remove = db_classes - new_classes
            for class_name in to_remove:
                cursor.execute("DELETE FROM Классы WHERE Название = ?", (class_name,))

            self.db_conn.commit()
            self.accept()
        except Exception as e:
            print(f"Ошибка при сохранении классов: {e}")
            self.db_conn.rollback()

    def get_classes(self):
        """Возвращает список классов"""
        return self.model.stringList()

    def closeEvent(self, event):
        """Закрывает соединение с БД при закрытии диалога"""
        self.db_conn.close()
        super().closeEvent(event)


class ScheduleItemDelegate(QStyledItemDelegate):
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        self.current_editor = None

    def createEditor(self, parent, option, index):
        # Создаем выпадающий список для редактора
        editor = QComboBox(parent)
        editor.setEditable(True)
        editor.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # Получаем список всех предметов из БД
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название, Сокращение FROM Предметы")
        subjects = [f"{short} ({full})" for full, short in cursor.fetchall()]

        # Настраиваем автодополнение
        completer = QCompleter(subjects, editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        editor.setCompleter(completer)

        editor.addItems(subjects)
        self.current_editor = editor
        return editor

    def setModelData(self, editor, model, index):
        # Получаем выбранный текст (например: "Мат (Математика)")
        text = editor.currentText()
        if not text:
            return

        # Извлекаем сокращенное название
        short_name = text.split(" ")[0]

        # Получаем полное название предмета из БД
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название FROM Предметы WHERE Сокращение = ?", (short_name,))
        result = cursor.fetchone()

        if not result:
            # Если предмет не найден — ничего не делаем
            return

        full_name = result[0]

        # Получаем учителей для этого предмета
        cursor.execute("""
            SELECT Учителя.ФИО 
            FROM Учителя
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?
        """, (short_name,))
        teachers = [row[0] for row in cursor.fetchall()]

        # Получаем кабинеты для этого предмета
        cursor.execute("""
            SELECT DISTINCT Кабинеты.Номер 
            FROM Кабинеты
            JOIN Предметы ON Кабинеты.id = Предметы.Основной_кабинет_id
            WHERE Предметы.Сокращение = ?
            UNION
            SELECT DISTINCT Кабинеты.Номер 
            FROM Кабинеты
            JOIN Учителя ON Кабинеты.id = Учителя.Основной_кабинет_id
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?
        """, (short_name, short_name))
        rooms = [row[0] for row in cursor.fetchall()]

        # Создаем диалог выбора учителя и кабинета
        dialog = TeacherRoomDialog(teachers, rooms, editor)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            teacher, room = dialog.get_selection()
            # Формируем текст для ячейки
            cell_text = f"{full_name}"
            if teacher:
                cell_text += f" ({teacher}"
                if room:
                    cell_text += f", {room}"
                cell_text += ")"
            elif room:
                cell_text += f" ({room})"
            # Устанавливаем значение в модель
            model.setData(index, cell_text, Qt.ItemDataRole.EditRole)
            model.setData(index, QColor(255, 230, 230), Qt.ItemDataRole.BackgroundRole)


class TeacherRoomDialog(QDialog):
    def __init__(self, teachers, rooms, parent=None):
        super().__init__(parent)
        self.selected_teacher = None
        self.selected_room = None

        self.setWindowTitle("Выбор преподавателя и кабинета")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # Создаем таблицу для выбора
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Преподаватель", "Кабинет"])
        self.table.setRowCount(max(len(teachers), len(rooms)))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Заполняем таблицу преподавателями
        for row, teacher in enumerate(teachers):
            item = QTableWidgetItem(teacher)
            self.table.setItem(row, 0, item)

        # Заполняем таблицу кабинетами
        for row, room in enumerate(rooms):
            item = QTableWidgetItem(room)
            self.table.setItem(row, 1, item)

        # Кнопки
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_selection)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)

        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)

        layout.addWidget(self.table)
        layout.addLayout(button_box)

    def accept_selection(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            teacher_item = self.table.item(selected_row, 0)
            room_item = self.table.item(selected_row, 1)
            self.selected_teacher = teacher_item.text() if teacher_item else None
            self.selected_room = room_item.text() if room_item else None
        self.accept()

    def get_selection(self):
        return self.selected_teacher, self.selected_room


class VerticalDayLabel(QLabel):
    """Вертикальная метка дня недели с закругленным фоном"""

    def __init__(self, text):
        # Инициализация метки
        super().__init__(text)  # Вызов конструктора QLabel

        # Настройка шрифта
        font = QFont()
        font.setPointSize(10)  # Размер шрифта 10 пунктов
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)  # Расстояние между буквами 2px
        self.setFont(font)  # Применяем шрифт к метке

    def paintEvent(self, event):
        """Кастомная отрисовка с повернутым текстом"""
        # Создаем объект для рисования
        painter = QPainter(self)
        # Включаем сглаживание для плавных линий
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Создаем путь для рисования фона
        path = QPainterPath()
        # Прямоугольник фона с отступами 2px от краев
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # Добавляем закругленный прямоугольник (радиус 8px)
        path.addRoundedRect(rect, 8, 8)

        # Рисуем фон без контура
        painter.setPen(Qt.PenStyle.NoPen)
        # Заливаем светло-серым цветом (RGB 230,230,230)
        painter.fillPath(path, QColor(230, 230, 230))
        # Отрисовываем путь
        painter.drawPath(path)

        # Настраиваем цвет текста (темно-серый)
        painter.setPen(QColor(70, 70, 70))
        # Поворачиваем систему координат на 90° против часовой стрелки
        painter.rotate(-90)

        # Получаем метрики шрифта для точного позиционирования
        fm = QFontMetrics(self.font())
        # Ширина текста в пикселях
        text_width = fm.horizontalAdvance(self.text())
        # Рисуем текст в повернутой системе координат
        painter.drawText(
            -self.height() + (self.height() - text_width) // 2,  # X (в исходной системе - Y)
            25,  # Y (в исходной системе - X)
            self.text()  # Текст для отображения
        )


class ScheduleApp(QMainWindow):
    """Главное окно приложения с расписанием"""

    def __init__(self):
        super().__init__()

        # Инициализация подключения к БД
        self.db_conn = sqlite3.connect('school_schedule.db')

        # Расписание звонков (по дням недели)
        self.schedule_times = {
            # Понедельник и четверг
            "ПОНЕДЕЛЬНИК": [
                ("8:30-9:10", "1 урок"),
                ("9:15-9:55", "2 урок"),
                ("10:10-10:50", "3 урок"),
                ("11:05-11:45", "4 урок"),
                ("12:00-12:40", "5 урок"),
                ("12:45-13:25", "6 урок"),
                ("13:30-14:10", "7 урок"),
                ("14:15-14:55", "8 урок"),
                ("15:00-15:40", "9 урок")
            ],
            # Вторник, среда, пятница
            "ВТОРНИК": [
                ("8:00-8:40", "1 урок"),
                ("8:45-9:25", "2 урок"),
                ("9:40-10:20", "3 урок"),
                ("10:35-11:15", "4 урок"),
                ("11:30-12:10", "5 урок"),
                ("12:15-12:55", "6 урок"),
                ("13:00-13:40", "7 урок"),
                ("13:45-14:25", "8 урок"),
                ("15:00-15:40", "9 урок")
            ],
            "СРЕДА": [
                ("8:00-8:40", "1 урок"),
                ("8:45-9:25", "2 урок"),
                ("9:40-10:20", "3 урок"),
                ("10:35-11:15", "4 урок"),
                ("11:30-12:10", "5 урок"),
                ("12:15-12:55", "6 урок"),
                ("13:00-13:40", "7 урок"),
                ("13:45-14:25", "8 урок"),
                ("15:00-15:40", "9 урок")
            ],
            "ЧЕТВЕРГ": [
                ("8:30-9:10", "1 урок"),
                ("9:15-9:55", "2 урок"),
                ("10:10-10:50", "3 урок"),
                ("11:05-11:45", "4 урок"),
                ("12:00-12:40", "5 урок"),
                ("12:45-13:25", "6 урок"),
                ("13:30-14:10", "7 урок"),
                ("14:15-14:55", "8 урок"),
                ("15:00-15:40", "9 урок")
            ],
            "ПЯТНИЦА": [
                ("8:00-8:40", "1 урок"),
                ("8:45-9:25", "2 урок"),
                ("9:40-10:20", "3 урок"),
                ("10:35-11:15", "4 урок"),
                ("11:30-12:10", "5 урок"),
                ("12:15-12:55", "6 урок"),
                ("13:00-13:40", "7 урок"),
                ("13:45-14:25", "8 урок"),
                ("15:00-15:40", "9 урок")
            ]
        }

        # Остальные настройки остаются без изменений
        self.setWindowTitle("Школьное расписание")
        self.window_width = 1500
        self.window_height = 900
        self.column_width = 120
        self.first_column_width = 50
        self.row_height = 31
        self.setGeometry(100, 100, self.window_width, self.window_height)
        self.classes = []
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        # Создаем центральный виджет
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)  # Устанавливаем как центральный

        # Основной горизонтальный макет
        self.main_layout = QHBoxLayout(self.central_widget)
        # Устанавливаем отступы (лево, верх, право, низ)
        self.main_layout.setContentsMargins(10, 0, 10, 0)

        # Создаем область прокрутки
        self.scroll_area = QScrollArea()
        # Разрешаем изменение размера внутреннего виджета
        self.scroll_area.setWidgetResizable(True)

        # 2. НАСТРОЙКА ПРОКРУТКИ (можно регулировать)
        self.scroll_area.setMinimumWidth(self.window_width - 1)  # Ширина области прокрутки
        # Добавляем область прокрутки в основной макет
        self.main_layout.addWidget(self.scroll_area)

        # Создаем контейнер для содержимого (дни + таблица)
        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        # Убираем отступы и промежутки между элементами
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        # Устанавливаем контейнер в область прокрутки
        self.scroll_area.setWidget(self.container)

        # Инициализация компонентов
        self.setup_days_panel()  # Панель с днями недели
        self.setup_schedule_table()  # Таблица расписания

    def show_class_setup(self):
        """Показывает диалог настройки классов"""
        # Создаем диалоговое окно
        dialog = ClassSetupDialog(self)
        # Если диалог завершился нажатием OK
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Получаем список классов
            self.classes = dialog.get_classes()
            # Пересоздаем интерфейс с новыми классами
            self.init_ui()

    def setup_days_panel(self):
        """Панель с днями недели"""
        self.days_panel = QWidget()  # Создаем виджет для панели дней

        # 3. НАСТРОЙКА ПАНЕЛИ ДНЕЙ (можно регулировать)
        self.days_panel.setFixedWidth(50)  # Ширина панели (было 50)

        # Вертикальный макет для дней
        self.days_layout = QVBoxLayout(self.days_panel)
        # Устанавливаем отступы (лево, верх, право, низ)
        self.days_layout.setContentsMargins(10, 22, 10, 0)
        self.days_layout.setSpacing(0)  # Промежуток между элементами

        # Список дней недели
        week_days = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА"]
        lesson_height = 28  # Высота одной строки с уроком

        # Создаем метки для каждого дня
        for day in week_days:
            label = VerticalDayLabel(day)  # Наша кастомная метка
            label.setFixedHeight(10 * lesson_height)  # Высота = 10 строк
            label.setFixedWidth(60)  # Ширина соответствует панели
            self.days_layout.addWidget(label)  # Добавляем в макет

        # Добавляем панель дней в контейнер
        self.container_layout.addWidget(self.days_panel)

    def setup_schedule_table(self):
        """Основной метод для настройки таблицы расписания.
        Создает таблицу с фиксированным первым столбцом (номера уроков),
        который остается видимым при горизонтальной прокрутке."""

        # Создаем основную таблицу для отображения расписания
        self.table = QTableWidget()
        self.table.setMinimumWidth(self.window_width - 100)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.show_cell_tooltip)

        if not self.classes:
            # Настроить, если классов нет
            self.table.setColumnCount(2)
            self.table.setRowCount(1)

            # Кнопка для добавления классов
            add_button = QPushButton()
            add_button.setIcon(QIcon("knopka.png"))
            add_button.setIconSize(QSize(32, 32))
            add_button.setText("Добавить классы")
            add_button.setStyleSheet("""
                QPushButton {
                    padding: 5px;  
                    border: 1px solid #ccc;  
                    border-radius: 4px;  
                    background-color: #F4A460;  
                }
                QPushButton:hover {
                    background-color: #E9967A;  
                }
            """)
            add_button.clicked.connect(self.show_class_setup)
            self.table.setCellWidget(0, 1, add_button)

            self.table.setHorizontalHeaderLabels(["", ""])
            self.table.horizontalHeader().setStretchLastSection(True)
            self.container_layout.addWidget(self.table)
        else:
            # Настройка, если классы присутствуют
            self.table.setColumnCount(len(self.classes) + 1)
            self.table.setRowCount(45)

            headers = ["Урок"] + self.classes
            self.table.setHorizontalHeaderLabels(headers)

            self.table.verticalHeader().setDefaultSectionSize(self.row_height)
            self.table.setColumnWidth(0, self.first_column_width)

            for day in range(5):
                for lesson in range(9):
                    row = day * 9 + lesson
                    item = QTableWidgetItem(str(lesson + 1))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, 0, item)

                    day_name = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА"][day]
                    if lesson < len(self.schedule_times[day_name]):
                        time, desc = self.schedule_times[day_name][lesson]
                        self.table.item(row, 0).setToolTip(f"{desc}\n{time}")

            # Устанавливаем кастомный делегат для редактируемых ячеек
            delegate = ScheduleItemDelegate(self.db_conn)

            # Для всех колонок с классами (кроме первой колонки с номерами уроков)
            for col in range(1, self.table.columnCount()):
                self.table.setItemDelegateForColumn(col, delegate)

            # Создаем фиксированную таблицу
            self.frozen_table = QTableWidget()
            self.frozen_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.frozen_table.setColumnCount(1)
            self.frozen_table.setRowCount(self.table.rowCount() + 1)

            # Настройка стиля фиксированной таблицы
            self.frozen_table.setStyleSheet("""
                QTableWidget {
                    border: none;  
                    background-color: #696969;  
                }
                QTableWidget::item {
                    border-right: 1px solid #696969;  
                }
            """)

            # Добавляем заголовок в фиксированную таблицу
            header_item = QTableWidgetItem("Урок")  # Заголовок номер урока
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # Выравниваем по центру
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Запрещаем редактирование
            self.frozen_table.setItem(0, 0, header_item)

            # Устанавливаем фиксированную высоту для заголовка
            header_fixed_height = 25
            self.frozen_table.setRowHeight(0, header_fixed_height)

            # Копируем данные из основной таблицы
            for row in range(1, self.table.rowCount() + 1):
                item = self.table.item(row - 1, 0).clone()
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.frozen_table.setItem(row, 0, item)
                self.frozen_table.setRowHeight(row, 31)

            self.frozen_table.setColumnWidth(0, self.first_column_width)
            self.frozen_table.setFixedWidth(self.first_column_width)
            self.frozen_table.verticalHeader().hide()
            self.frozen_table.horizontalHeader().hide()

            # Создаем контейнер для обеих таблиц
            table_container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.addWidget(self.frozen_table)
            container_layout.addWidget(self.table)
            container_layout.setSpacing(0)
            container_layout.setContentsMargins(5, 0, 0, 0)
            table_container.setLayout(container_layout)

            self.table.verticalScrollBar().valueChanged.connect(
                self.frozen_table.verticalScrollBar().setValue
            )
            self.frozen_table.verticalScrollBar().valueChanged.connect(
                self.table.verticalScrollBar().setValue
            )

            self.container_layout.addWidget(table_container)

            # Скрываем первый столбец основной таблицы
            self.table.setColumnHidden(0, True)

        # Общие настройки таблицы
        self.table.verticalHeader().setVisible(False)

        for col in range(1, self.table.columnCount()):
            self.table.setColumnWidth(col, self.column_width)

        self.table.verticalHeader().setDefaultSectionSize(self.row_height)

    def show_cell_tooltip(self, row, col):
        """Показывает подсказку с временем урока при наведении на ячейку"""
        if col == 0:  # Только для первой колонки (номера уроков)
            return

        day = row // 9  # Определяем день недели (0-4)
        lesson = row % 9  # Определяем номер урока (0-8)

        day_names = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА"]
        day_name = day_names[day]

        if lesson < len(self.schedule_times[day_name]):
            time, desc = self.schedule_times[day_name][lesson]
            item = self.table.item(row, 0)
            if item:
                # Устанавливаем tooltip для ячейки
                self.table.setToolTip(f"{day_name}\nУрок {lesson + 1}: {time}\n{desc}")
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())
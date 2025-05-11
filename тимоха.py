import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QScrollArea, QPushButton, QDialog,
    QComboBox, QLineEdit, QFormLayout, QGridLayout, QStyledItemDelegate,
    QCompleter, QAbstractItemView, QMenu, QListView, QDialogButtonBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QSize, QSortFilterProxyModel, QStringListModel, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics, QIcon, QPixmap,
    QStandardItemModel, QStandardItem, QPen
)


class ClassSetupDialog(QDialog):
    """Диалоговое окно для настройки списка классов"""
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
    """Делегат для отображения и редактирования ячеек расписания"""
    def __init__(self, db_conn, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        self.current_editor = None

    def createEditor(self, parent, option, index):
        """Создает редактор для ячейки - выпадающий список с предметами"""
        editor = QComboBox(parent)
        editor.setEditable(True)
        editor.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название, Сокращение FROM Предметы")
        subjects = [f"{short} ({full})" for full, short in cursor.fetchall()]

        completer = QCompleter(subjects, editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        editor.setCompleter(completer)

        editor.addItems(subjects)
        self.current_editor = editor
        return editor

    def paint(self, painter, option, index):
        """Упрощенная отрисовка без границ, только заливка"""
        # Получаем данные о конфликте
        conflict_type = index.data(Qt.ItemDataRole.UserRole + 1)

        # Сохраняем оригинальные настройки
        painter.save()

        # Рисуем стандартное содержимое ячейки
        super().paint(painter, option, index)

        # Восстанавливаем настройки
        painter.restore()

        # Восстанавливаем настройки
        painter.restore()

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        if not text:
            return

        short_name = text.split(" ")[0]

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название FROM Предметы WHERE Сокращение = ?", (short_name,))
        result = cursor.fetchone()

        if not result:
            return

        full_name = result[0]  # Полное название предмета

        # Получаем данные для диалога
        cursor.execute("SELECT ФИО FROM Учителя")
        all_teachers = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT Учителя.ФИО FROM Учителя
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?""", (short_name,))
        subject_teachers = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT Номер FROM Кабинеты")
        all_rooms = [str(row[0]) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT Кабинеты.Номер FROM Кабинеты
            JOIN Предметы ON Кабинеты.id = Предметы.Основной_кабинет_id
            WHERE Предметы.Сокращение = ?
            UNION
            SELECT DISTINCT Кабинеты.Номер FROM Кабинеты
            JOIN Учителя ON Кабинеты.id = Учителя.Основной_кабинет_id
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?""", (short_name, short_name))
        subject_rooms = [str(row[0]) for row in cursor.fetchall()]

        dialog = TeacherRoomDialog(
            all_teachers=all_teachers,
            all_rooms=all_rooms,
            recommended_teachers=subject_teachers,
            recommended_rooms=subject_rooms,
            parent=editor
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            teacher, room = dialog.get_selection()

            # Сохраняем ВСЕ данные в UserRole
            full_data = {
                'subject': full_name,
                'teacher': teacher,
                'room': room
            }
            model.setData(index, full_data, Qt.ItemDataRole.UserRole)

            # Отображаем только "ПредметКабинет"
            display_text = f"{full_name}{room}" if room else full_name
            model.setData(index, display_text, Qt.ItemDataRole.DisplayRole)

            # Устанавливаем цвета
            model.setData(index, QColor(127, 111, 102), Qt.ItemDataRole.BackgroundRole)
            model.setData(index, QColor(255, 255, 255), Qt.ItemDataRole.ForegroundRole)

            # Проверяем конфликты
            self.parent().check_teacher_conflicts()


class TeacherRoomDialog(QDialog):
    """Диалог выбора учителя и кабинета для предмета"""
    def __init__(self, all_teachers, all_rooms, recommended_teachers=None, recommended_rooms=None, parent=None):
        super().__init__(parent)
        self.selected_teacher = None
        self.selected_room = None

        self.setWindowTitle("Выбор преподавателя и кабинета")
        self.setFixedSize(600, 400)

        layout = QVBoxLayout(self)

        # Основной макет с выбором учителя и кабинета
        main_layout = QHBoxLayout()

        # Панель выбора учителя
        teacher_layout = QVBoxLayout()
        teacher_layout.addWidget(QLabel("Выберите преподавателя:"))

        # Список всех учителей с выделением рекомендуемых
        self.teacher_list = QListWidget()
        self.teacher_list.setStyleSheet("""
            QListView {
                show-decoration-selected: 1;
            }
            QListView::item:selected {
                background-color: rgb(91,80,72);
                color: white;
            }
        """)

        for teacher in all_teachers:
            item = QListWidgetItem(teacher)
            if recommended_teachers and teacher in recommended_teachers:
                item.setBackground(QColor(171, 131, 105))
                item.setToolTip("Рекомендуемый преподаватель для этого предмета")
            self.teacher_list.addItem(item)

        teacher_layout.addWidget(self.teacher_list)

        # Поле поиска учителя
        self.teacher_search = QLineEdit()
        self.teacher_search.setPlaceholderText("Поиск преподавателя...")
        self.teacher_search.textChanged.connect(self.filter_teachers)
        teacher_layout.addWidget(self.teacher_search)

        # Панель выбора кабинета
        room_layout = QVBoxLayout()
        room_layout.addWidget(QLabel("Выберите кабинет:"))

        # Список всех кабинетов с выделением рекомендуемых
        self.room_list = QListWidget()
        self.room_list.setStyleSheet("""
            QListView {
                show-decoration-selected: 1;
            }
            QListView::item:selected {
                background-color: rgb(91,80,72);
                color: white;
            }
        """)

        for room in all_rooms:
            item = QListWidgetItem(room)
            if recommended_rooms and room in recommended_rooms:
                item.setBackground(QColor(171, 131, 105))
                item.setToolTip("Рекомендуемый кабинет для этого предмета")
            self.room_list.addItem(item)

        room_layout.addWidget(self.room_list)

        # Поле поиска кабинета
        self.room_search = QLineEdit()
        self.room_search.setPlaceholderText("Поиск кабинета...")
        self.room_search.textChanged.connect(self.filter_rooms)
        room_layout.addWidget(self.room_search)

        # Добавляем обе панели в основной макет
        main_layout.addLayout(teacher_layout)
        main_layout.addLayout(room_layout)

        # Кнопки OK/Отмена
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)

        # Добавляем все в основной layout
        layout.addLayout(main_layout)
        layout.addWidget(button_box)

    def filter_teachers(self, text):
        """Фильтрация списка учителей по введенному тексту"""
        for i in range(self.teacher_list.count()):
            item = self.teacher_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def filter_rooms(self, text):
        """Фильтрация списка кабинетов по введенному тексту"""
        for i in range(self.room_list.count()):
            item = self.room_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def accept_selection(self):
        """Обработка выбора учителя и кабинета"""
        teacher_item = self.teacher_list.currentItem()
        room_item = self.room_list.currentItem()

        self.selected_teacher = teacher_item.text() if teacher_item else None
        self.selected_room = room_item.text() if room_item else None

        self.accept()

    def get_selection(self):
        """Возвращает выбранные значения"""
        return self.selected_teacher, self.selected_room


class VerticalDayLabel(QLabel):
    """Вертикальная метка дня недели с закругленным фоном"""

    def __init__(self, text):
        super().__init__(text)
        font = QFont()
        font.setPointSize(10)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        self.setFont(font)

    def paintEvent(self, event):
        """Отрисовывает вертикальный текст с закругленным фоном"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        path.addRoundedRect(rect, 8, 8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(path, QColor(251, 206, 177))
        painter.drawPath(path)

        painter.setPen(QColor(70, 70, 70))
        painter.rotate(-90)

        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.text())
        painter.drawText(
            -self.height() + (self.height() - text_width) // 2,
            25,
            self.text()
        )


class ScheduleApp(QMainWindow):
    """Главное окно приложения с расписанием"""

    def __init__(self):
        super().__init__()

        # Инициализация подключения к БД
        self.db_conn = sqlite3.connect('school_schedule.db')

        # Расписание звонков (по дням недели)
        self.schedule_times = {
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
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 0, 10, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumWidth(self.window_width - 1)
        self.main_layout.addWidget(self.scroll_area)

        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(5, 0, 0, 0)
        self.container_layout.setSpacing(0)
        self.scroll_area.setWidget(self.container)

        self.setup_days_panel()
        self.setup_schedule_table()

    def show_class_setup(self):
        """Показывает диалог настройки классов"""
        dialog = ClassSetupDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.classes = dialog.get_classes()
            self.init_ui()

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        if not text:
            return

        short_name = text.split(" ")[0]

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название FROM Предметы WHERE Сокращение = ?", (short_name,))
        result = cursor.fetchone()

        if not result:
            return

        full_name = result[0]  # Полное название предмета

        # Получаем списки для диалога выбора
        cursor.execute("SELECT ФИО FROM Учителя")
        all_teachers = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT Учителя.ФИО 
            FROM Учителя
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?
        """, (short_name,))
        subject_teachers = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT Номер FROM Кабинеты")
        all_rooms = [str(row[0]) for row in cursor.fetchall()]

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
        subject_rooms = [str(row[0]) for row in cursor.fetchall()]

        dialog = TeacherRoomDialog(
            all_teachers=all_teachers,
            all_rooms=all_rooms,
            recommended_teachers=subject_teachers,
            recommended_rooms=subject_rooms,
            parent=editor
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            teacher, room = dialog.get_selection()

            # Сохраняем полные данные в UserRole
            full_data = {
                'subject': full_name,
                'teacher': teacher,
                'room': room
            }
            model.setData(index, full_data, Qt.ItemDataRole.UserRole)

            # Отображаем только "ПредметКабинет"
            display_text = f"{full_name}{room}" if room else full_name
            model.setData(index, display_text, Qt.ItemDataRole.DisplayRole)

            # Устанавливаем цвета
            model.setData(index, QColor(127, 111, 102), Qt.ItemDataRole.BackgroundRole)
            model.setData(index, QColor(255, 255, 255), Qt.ItemDataRole.ForegroundRole)

            # Проверяем конфликты
            if hasattr(self.parent(), 'check_teacher_conflicts'):
                self.parent().check_teacher_conflicts()

    def displayText(self, value, locale):
        """Определяет, что отображается в неактивной ячейке"""
        if isinstance(value, dict):  # Если данные хранятся в UserRole
            return f"{value['subject']}{value['room']}" if value['room'] else value['subject']
        return super().displayText(value, locale)

    def createEditor(self, parent, option, index):
        """Создает редактор с полными данными"""
        editor = super().createEditor(parent, option, index)

        # Восстанавливаем полные данные при редактировании
        full_data = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(full_data, dict):
            subject = full_data['subject']
            teacher = full_data.get('teacher', '')
            room = full_data.get('room', '')

            # Формируем текст для редактора
            editor_text = f"{subject}"
            if teacher or room:
                editor_text += f" ({teacher}"
                if room:
                    editor_text += f", {room}"
                editor_text += ")"

            editor.setCurrentText(editor_text)

        return editor

    def check_teacher_conflicts(self):
        """Проверка конфликтов с цветовой подсветкой"""
        # Сбрасываем все выделения
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(127, 111, 102))  # Стандартный цвет
                    item.setData(Qt.ItemDataRole.UserRole + 1, None)

        # Словари для сбора данных
        teacher_dict = {}  # {строка: {учитель: [ячейки]}}
        room_dict = {}  # {строка: {кабинет: [ячейки]}}

        # Собираем данные
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item and item.text():
                    full_data = item.data(Qt.ItemDataRole.UserRole)

                    if isinstance(full_data, dict):
                        teacher = full_data.get('teacher')
                        room = full_data.get('room')

                        # Заполняем словари
                        if teacher:
                            teacher_dict.setdefault(row, {}).setdefault(teacher, []).append(item)
                        if room:
                            room_dict.setdefault(row, {}).setdefault(room, []).append(item)

        # Проверяем конфликты кабинетов (красный)
        for row in room_dict:
            for room in room_dict[row]:
                if len(room_dict[row][room]) > 1:
                    for item in room_dict[row][room]:
                        item.setBackground(QColor(255, 0, 0))  # Красный

        # Проверяем конфликты учителей (розовый)
        for row in teacher_dict:
            for teacher in teacher_dict[row]:
                if len(teacher_dict[row][teacher]) > 1:
                    for item in teacher_dict[row][teacher]:
                        # Подсвечиваем только если нет конфликта кабинета
                        if item.background().color() != QColor(255, 0, 0):
                            item.setBackground(QColor(205, 132, 157))  # Розовый

    def setup_days_panel(self):
        """Панель с днями недели"""
        self.days_panel = QWidget()
        self.days_panel.setFixedWidth(50)

        self.days_layout = QVBoxLayout(self.days_panel)
        self.days_layout.setContentsMargins(10, 22, 10, 11)
        self.days_layout.setSpacing(0)

        week_days = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА"]
        lesson_height = 28

        for day in week_days:
            label = VerticalDayLabel(day)
            label.setFixedHeight(10 * lesson_height)
            label.setFixedWidth(60)
            self.days_layout.addWidget(label)

        self.container_layout.addWidget(self.days_panel)

    def setup_schedule_table(self):
        """Настройка таблицы расписания"""
        self.table = QTableWidget()
        self.table.setMinimumWidth(self.window_width - 100)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self.show_cell_tooltip)

        if not self.classes:
            # Если классы не заданы, показываем кнопку для их добавления
            self.table.setColumnCount(2)
            self.table.setRowCount(1)

            add_button = QPushButton()
            add_button.setIcon(QIcon("knopka.png"))
            add_button.setIconSize(QSize(32, 32))
            add_button.setText("Добавить классы")
            add_button.setStyleSheet("""
                QPushButton {
                    padding: 5px;  
                    border: 1px solid #ccc;  
                    border-radius: 4px;  
                    background-color: #cea182;  
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
            # Если классы заданы, создаем полную таблицу расписания
            self.table.setColumnCount(len(self.classes) + 1)
            self.table.setRowCount(45)

            headers = ["Урок"] + self.classes
            self.table.setHorizontalHeaderLabels(headers)

            self.table.verticalHeader().setDefaultSectionSize(self.row_height)
            self.table.setColumnWidth(0, self.first_column_width)

            # Заполняем номера уроков и временные интервалы
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

            # Устанавливаем делегат для редактирования ячеек
            delegate = ScheduleItemDelegate(self.db_conn, self)
            for col in range(1, self.table.columnCount()):
                self.table.setItemDelegateForColumn(col, delegate)

            # Создаем закрепленную таблицу для номеров уроков
            self.frozen_table = QTableWidget()
            self.frozen_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.frozen_table.setColumnCount(1)
            self.frozen_table.setRowCount(self.table.rowCount() + 1)

            self.frozen_table.setStyleSheet("""
                QTableWidget {
                    border: none;  
                    background-color: #a8856b;  
                }
                QTableWidget::item {
                    border-right: 1px solid #000000;  
                }
            """)

            header_item = QTableWidgetItem("Урок")
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.frozen_table.setItem(0, 0, header_item)

            header_fixed_height = 25
            self.frozen_table.setRowHeight(0, header_fixed_height)

            # Копируем номера уроков из основной таблицы
            for row in range(1, self.table.rowCount() + 1):
                item = self.table.item(row - 1, 0).clone()
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.frozen_table.setItem(row, 0, item)
                self.frozen_table.setRowHeight(row, 31)

            self.frozen_table.setColumnWidth(0, self.first_column_width)
            self.frozen_table.setFixedWidth(self.first_column_width)
            self.frozen_table.verticalHeader().hide()
            self.frozen_table.horizontalHeader().hide()

            # Создаем контейнер для двух таблиц
            table_container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.addWidget(self.frozen_table)
            container_layout.addWidget(self.table)
            container_layout.setSpacing(0)
            container_layout.setContentsMargins(5, 0, 0, 0)
            table_container.setLayout(container_layout)

            # Синхронизируем скроллинг двух таблиц
            self.table.verticalScrollBar().valueChanged.connect(
                self.frozen_table.verticalScrollBar().setValue
            )
            self.frozen_table.verticalScrollBar().valueChanged.connect(
                self.table.verticalScrollBar().setValue
            )

            self.container_layout.addWidget(table_container)
            self.table.setColumnHidden(0, True)

        self.table.verticalHeader().setVisible(False)

        # Устанавливаем ширину столбцов
        for col in range(1, self.table.columnCount()):
            self.table.setColumnWidth(col, self.column_width)

        self.table.verticalHeader().setDefaultSectionSize(self.row_height)

        # Проверяем конфликты после настройки таблицы
        self.check_teacher_conflicts()

    def show_cell_tooltip(self, row, col):
        """Показывает подсказку с временем урока при наведении на ячейку"""
        if col == 0:
            return

        day = row // 9
        lesson = row % 9

        day_names = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА"]
        day_name = day_names[day]

        if lesson < len(self.schedule_times[day_name]):
            time, desc = self.schedule_times[day_name][lesson]
            item = self.table.item(row, 0)
            if item:
                self.table.setToolTip(f"{day_name}\nУрок {lesson + 1}: {time}\n{desc}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())

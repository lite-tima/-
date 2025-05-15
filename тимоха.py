import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QScrollArea, QPushButton, QDialog,
    QComboBox, QLineEdit, QFormLayout, QGridLayout, QStyledItemDelegate,
    QCompleter, QAbstractItemView, QMenu, QListView, QDialogButtonBox, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QSortFilterProxyModel, QStringListModel, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics, QIcon, QPixmap,
    QStandardItemModel, QStandardItem, QPen
)
from PyQt6.QtCore import QItemSelectionModel


class ClassSetupDialog(QDialog):
    """Диалоговое окно для выбора классов из базы данных"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор классов")
        self.setFixedSize(300, 400)

        layout = QVBoxLayout(self)

        # Получаем список классов из базы данных
        self.db_conn = sqlite3.connect('school_schedule.db')
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT Название FROM Классы ORDER BY Название")
        existing_classes = [row[0] for row in cursor.fetchall()]

        # Создаем модель для списка классов
        self.model = QStringListModel()
        self.model.setStringList(existing_classes)

        # Виджет для отображения списка классов
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        # Выделяем все классы по умолчанию
        for i in range(self.model.rowCount()):
            self.list_view.selectionModel().select(
                self.model.index(i),
                QItemSelectionModel.SelectionFlag.Select
            )

        # Кнопки OK/Отмена
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(QLabel("Выберите классы для отображения:"))
        layout.addWidget(self.list_view)
        layout.addWidget(button_box)

    def get_selected_classes(self):
        """Возвращает список выбранных классов"""
        indexes = self.list_view.selectedIndexes()
        return [self.model.data(index, Qt.ItemDataRole.DisplayRole) for index in indexes]

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
        try:
            self.selected_teacher = None
            self.selected_room = None

            # Безопасное получение соединения с БД
            self.db_conn = None
            if parent is not None:
                grandparent = parent.parent()
                if grandparent is not None and hasattr(grandparent, 'db_conn'):
                    self.db_conn = grandparent.db_conn

            self.setWindowTitle("Выбор преподавателя и кабинета")
            self.setFixedSize(600, 400)

            # Устанавливаем темную цветовую схему
            self.setStyleSheet("""
                QDialog {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                }
                QLabel {
                    color: #E0E0E0;
                }
                QLineEdit {
                    background-color: #3D3D3D;
                    color: #E0E0E0;
                    border: 1px solid #555;
                    padding: 5px;
                }
                QListWidget {
                    background-color: #3D3D3D;
                    color: #E0E0E0;
                    border: 1px solid #555;
                    show-decoration-selected: 1;
                }
                QListWidget::item {
                    padding: 5px;
                }
                QListWidget::item:selected {
                    background-color: #5B5048;
                    color: white;
                }
                QListWidget::item:hover {
                    background-color: #4A4A4A;
                }
                QPushButton {
                    background-color: #5B5048;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #6D5D52;
                }
                QPushButton:pressed {
                    background-color: #4A413B;
                }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)

            # Основной макет с выбором учителя и кабинета
            main_layout = QHBoxLayout()
            main_layout.setSpacing(15)

            # Панель выбора учителя
            self.setup_teacher_panel(all_teachers, recommended_teachers, main_layout)

            # Панель выбора кабинета
            self.setup_room_panel(all_rooms, recommended_rooms, main_layout)

            # Добавляем основной макет
            layout.addLayout(main_layout)

            # Кнопки OK/Отмена
            self.setup_buttons(layout)

        except Exception as e:
            print(f"Critical error in TeacherRoomDialog init: {e}")
            QMessageBox.critical(None, "Ошибка", "Не удалось инициализировать диалог выбора")
            raise

    def setup_teacher_panel(self, all_teachers, recommended_teachers, main_layout):
        """Настройка панели выбора учителя"""
        try:
            teacher_layout = QVBoxLayout()
            teacher_layout.setSpacing(5)
            teacher_layout.addWidget(QLabel("Выберите преподавателя:"))

            self.teacher_list = QListWidget()

            # Проверяем и преобразуем входные данные
            all_teachers = self.validate_list(all_teachers)
            recommended_teachers = self.validate_list(recommended_teachers)

            # Сначала добавляем рекомендуемых учителей
            if recommended_teachers:
                for teacher in recommended_teachers:
                    if teacher in all_teachers:
                        item = QListWidgetItem(teacher)
                        item.setBackground(QColor(171, 131, 105))
                        item.setToolTip("Рекомендуемый преподаватель для этого предмета")

                        room = self.get_teacher_room(teacher)
                        if room:
                            item.setText(f"{teacher} (каб. {room})")

                        self.teacher_list.addItem(item)

            # Затем добавляем остальных учителей
            for teacher in all_teachers:
                if not recommended_teachers or teacher not in recommended_teachers:
                    item = QListWidgetItem(teacher)
                    self.teacher_list.addItem(item)

            teacher_layout.addWidget(self.teacher_list)

            # Поле поиска учителя
            self.teacher_search = QLineEdit()
            self.teacher_search.setPlaceholderText("Поиск преподавателя...")
            self.teacher_search.textChanged.connect(self.filter_teachers)
            teacher_layout.addWidget(self.teacher_search)

            main_layout.addLayout(teacher_layout)

        except Exception as e:
            print(f"Error setting up teacher panel: {e}")
            raise

    def setup_room_panel(self, all_rooms, recommended_rooms, main_layout):
        """Настройка панели выбора кабинета"""
        try:
            room_layout = QVBoxLayout()
            room_layout.setSpacing(5)
            room_layout.addWidget(QLabel("Выберите кабинет:"))

            self.room_list = QListWidget()

            # Проверяем и преобразуем входные данные
            all_rooms = [str(r) for r in self.validate_list(all_rooms)]
            recommended_rooms = [str(r) for r in self.validate_list(recommended_rooms or [])]

            # Сначала добавляем рекомендуемые кабинеты
            if recommended_rooms:
                for room in recommended_rooms:
                    if room in all_rooms:
                        item = QListWidgetItem(room)
                        item.setBackground(QColor(171, 131, 105))
                        item.setToolTip("Рекомендуемый кабинет для этого предмета")
                        self.room_list.addItem(item)

            # Затем добавляем остальные кабинеты
            for room in all_rooms:
                if not recommended_rooms or room not in recommended_rooms:
                    item = QListWidgetItem(room)
                    self.room_list.addItem(item)

            room_layout.addWidget(self.room_list)

            # Поле поиска кабинета
            self.room_search = QLineEdit()
            self.room_search.setPlaceholderText("Поиск кабинета...")
            self.room_search.textChanged.connect(self.filter_rooms)
            room_layout.addWidget(self.room_search)

            main_layout.addLayout(room_layout)

        except Exception as e:
            print(f"Error setting up room panel: {e}")
            raise

    def setup_buttons(self, layout):
        """Настройка кнопок диалога"""
        try:
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                parent=self
            )
            button_box.accepted.connect(self.safe_accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)

            # Подключаем сигнал выбора учителя
            self.teacher_list.itemSelectionChanged.connect(self.on_teacher_selected)

        except Exception as e:
            print(f"Error setting up buttons: {e}")
            raise

    def validate_list(self, input_list):
        """Проверка и преобразование входного списка"""
        if input_list is None:
            return []
        try:
            return [str(item) for item in input_list if item is not None]
        except Exception as e:
            print(f"Error validating list: {e}")
            return []

    def get_teacher_room(self, teacher_name):
        """Безопасное получение кабинета учителя"""
        if not self.db_conn or not teacher_name:
            return None

        try:
            cursor = None
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT Кабинеты.Номер 
                    FROM Учителя
                    JOIN Кабинеты ON Учителя.Основной_кабинет_id = Кабинеты.id
                    WHERE Учителя.ФИО = ?""", (teacher_name,))
                result = cursor.fetchone()
                return str(result[0]) if result else None
            finally:
                if cursor:
                    cursor.close()
        except Exception as e:
            print(f"Error getting teacher room: {e}")
            return None

    def on_teacher_selected(self):
        """Безопасная обработка выбора учителя"""
        try:
            selected_items = self.teacher_list.selectedItems()
            if not selected_items:
                return

            teacher_item = selected_items[0]
            if teacher_item.background().color() == QColor(171, 131, 105):
                teacher_name = teacher_item.text().split(" (каб. ")[0]
                room = self.get_teacher_room(teacher_name)
                if room:
                    for i in range(self.room_list.count()):
                        item = self.room_list.item(i)
                        if item and item.text() == room:
                            self.room_list.setCurrentItem(item)
                            break
        except Exception as e:
            print(f"Error in teacher selection: {e}")

    def filter_teachers(self, text):
        """Безопасная фильтрация учителей"""
        try:
            for i in range(self.teacher_list.count()):
                item = self.teacher_list.item(i)
                if item:
                    item_text = item.text().split(" (каб. ")[0]
                    item.setHidden(text.lower() not in item_text.lower())
        except Exception as e:
            print(f"Error filtering teachers: {e}")

    def filter_rooms(self, text):
        """Безопасная фильтрация кабинетов"""
        try:
            for i in range(self.room_list.count()):
                item = self.room_list.item(i)
                if item:
                    item.setHidden(text.lower() not in item.text().lower())
        except Exception as e:
            print(f"Error filtering rooms: {e}")

    def safe_accept(self):
        """Безопасное подтверждение выбора"""
        try:
            teacher_item = self.teacher_list.currentItem()
            if teacher_item:
                self.selected_teacher = teacher_item.text().split(" (каб. ")[0]

            room_item = self.room_list.currentItem()
            if room_item:
                self.selected_room = room_item.text()

            self.accept()
        except Exception as e:
            print(f"Error accepting selection: {e}")
            self.reject()

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

        # Инициализация интерфейса с таблицей и кнопкой "Добавить классы"
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

        if not self.classes:
            # Если классы не заданы, показываем кнопку для их добавления
            self.table = QTableWidget()
            self.table.setMinimumWidth(self.window_width - 100)
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
            self.setup_days_panel()
            self.setup_schedule_table()

    def show_class_setup(self):
        """Показывает диалог выбора классов"""
        # Проверяем наличие классов в базе данных
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Классы")
        has_classes = cursor.fetchone()[0] > 0

        if not has_classes:
            QMessageBox.critical(self, "Ошибка", "В базе данных нет классов. Добавьте классы в таблицу 'Классы'.")
            return

        dialog = ClassSetupDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.classes = dialog.get_selected_classes()
            if self.classes:
                # Переключаемся на основной интерфейс
                self.init_ui()
            else:
                QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного класса.")

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

        # Создаем таблицу с колонками для каждого класса
        self.table.setColumnCount(len(self.classes) + 1)
        self.table.setRowCount(45)  # 5 дней * 9 уроков

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

    def closeEvent(self, event):
        """Закрывает соединение с БД при закрытии окна"""
        self.db_conn.close()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())
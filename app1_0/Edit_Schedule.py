import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget, QLabel, QHBoxLayout, QScrollArea, QPushButton, QDialog,
    QComboBox, QLineEdit, QFormLayout, QGridLayout, QStyledItemDelegate,
    QCompleter, QAbstractItemView, QMenu, QListView, QDialogButtonBox,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QSortFilterProxyModel, QStringListModel, QRectF
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QFont, QFontMetrics, QIcon, QPixmap,
    QStandardItemModel, QStandardItem, QPen
)
from PyQt6.QtCore import QItemSelectionModel
import requests
import json


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

        editor.addItem("")  # Пустая строка для удаления предмета
        editor.addItems(subjects)

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
        # Если выбрана пустая строка - удаляем данные
        if not text:
            model.setData(index, "", Qt.ItemDataRole.DisplayRole)
            model.setData(index, None, Qt.ItemDataRole.UserRole)
            model.setData(index, QColor(42, 181, 194), Qt.ItemDataRole.BackgroundRole)  # Бирюзовый фон
            model.setData(index, QColor(0, 0, 0), Qt.ItemDataRole.ForegroundRole)

            # Удаляем запись из базы данных
            self.delete_schedule_record(index)
            return

        short_name = text.split(" ")[0]

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT id, Название FROM Предметы WHERE Сокращение = ?", (short_name,))
        result = cursor.fetchone()

        if not result:
            return

        subject_id, full_name = result  # ID и полное название предмета

        # Получаем данные для диалога
        cursor.execute("SELECT id, ФИО FROM Учителя")
        all_teachers = [(row[0], row[1]) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT Учителя.id, Учителя.ФИО FROM Учителя
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?""", (short_name,))
        subject_teachers = [(row[0], row[1]) for row in cursor.fetchall()]

        cursor.execute("SELECT id, Номер FROM Кабинеты")
        all_rooms = [(row[0], str(row[1])) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT Кабинеты.id, Кабинеты.Номер FROM Кабинеты
            JOIN Предметы ON Кабинеты.id = Предметы.Основной_кабинет_id
            WHERE Предметы.Сокращение = ?
            UNION
            SELECT DISTINCT Кабинеты.id, Кабинеты.Номер FROM Кабинеты
            JOIN Учителя ON Кабинеты.id = Учителя.Основной_кабинет_id
            JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
            JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
            WHERE Предметы.Сокращение = ?""", (short_name, short_name))
        subject_rooms = [(row[0], str(row[1])) for row in cursor.fetchall()]

        dialog = TeacherRoomDialog(
            all_teachers=[t[1] for t in all_teachers],
            all_rooms=[r[1] for r in all_rooms],
            recommended_teachers=[t[1] for t in subject_teachers],
            recommended_rooms=[r[1] for r in subject_rooms],
            parent=editor
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            teacher_name, room_number = dialog.get_selection()

            # Находим ID выбранного учителя и кабинета
            teacher_id = next((t[0] for t in all_teachers if t[1] == teacher_name), None)
            room_id = next((r[0] for r in all_rooms if r[1] == room_number), None)

            if not teacher_id or not room_id:
                return

            # Получаем информацию о текущей ячейке
            row = index.row()
            col = index.column()

            # Определяем день недели и номер урока
            day_number = row // 9 + 1  # Порядковый номер дня (1-5)
            lesson_number = (row % 9) + 1  # Номер урока (1-9)

            # Получаем ID класса из заголовка столбца
            class_name = self.parent().table.horizontalHeaderItem(col).text()
            cursor.execute("SELECT id FROM Классы WHERE Название = ?", (class_name,))
            class_id_result = cursor.fetchone()
            if not class_id_result:
                return
            class_id = class_id_result[0]

            # Получаем ID временного слота
            cursor.execute("""
                SELECT id FROM Временные_слоты 
                WHERE Номер_слота = ? AND Тип_дня = (
                    SELECT CASE WHEN Сокращенный_день THEN 'Сокращенный' ELSE 'Обычный' END
                    FROM Настройки_дней WHERE Порядковый_номер = ?
                )""", (lesson_number, day_number))
            time_slot_result = cursor.fetchone()
            if not time_slot_result:
                return
            time_slot_id = time_slot_result[0]

            try:
                # Сохраняем или обновляем запись в базе данных
                cursor.execute("""
                    SELECT id FROM Расписание 
                    WHERE День_недели = ? AND ID_временного_слота = ? AND ID_класса = ?
                """, (day_number, time_slot_id, class_id))
                existing_record = cursor.fetchone()

                # Отправляем уведомление только пользователям этого класса
                try:
                    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
                    day_name = day_names[day_number - 1]

                    notification_data = {
                        "message": f"📝 Изменение в расписании вашего класса:\n"
                                   f"📅 День: {day_name}\n"
                                   f"⏰ Урок: {lesson_number}\n"
                                   f"📚 Предмет: {full_name}\n"
                                   f"👨‍🏫 Преподаватель: {teacher_name}\n"
                                   f"🚪 Кабинет: {room_number}\n\n\n"
                                   f"🏎 Кратко: {day_name}, {lesson_number} урок: {full_name} {room_number} ({teacher_name})",
                        "class_name": class_name
                    }

                    requests.post(
                        "http://localhost:8000/notify",
                        json=notification_data,
                        timeout=5
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления: {str(e)}")

                # Сохраняем все данные в UserRole
                full_data = {
                    'subject': full_name,
                    'subject_id': subject_id,
                    'teacher': teacher_name,
                    'teacher_id': teacher_id,
                    'room': room_number,
                    'room_id': room_id,
                    'day': day_number,
                    'lesson': lesson_number,
                    'class_id': class_id
                }
                model.setData(index, full_data, Qt.ItemDataRole.UserRole)

                # Отображаем только "Предмет (Кабинет)"
                display_text = f"{full_name} ({room_number})" if room_number else full_name
                model.setData(index, display_text, Qt.ItemDataRole.DisplayRole)

                # Устанавливаем цвета
                model.setData(index, QColor(42, 181, 194), Qt.ItemDataRole.BackgroundRole)
                model.setData(index, QColor(255, 255, 255), Qt.ItemDataRole.ForegroundRole)

                # Проверяем конфликты
                self.parent().check_teacher_conflicts()
            except sqlite3.Error as e:
                QMessageBox.critical(self.parent(), "Ошибка базы данных", f"Не удалось сохранить данные: {str(e)}")
                self.db_conn.rollback()

    def delete_schedule_record(self, index):
        """Удаляет запись расписания из базы данных"""
        try:
            cursor = self.db_conn.cursor()

            # Получаем информацию о текущей ячейке
            row = index.row()
            col = index.column()

            # Определяем день недели и номер урока
            day_number = row // 9 + 1  # Порядковый номер дня (1-5)
            lesson_number = (row % 9) + 1  # Номер урока (1-9)

            # Получаем ID класса из заголовка столбца
            class_name = self.parent().table.horizontalHeaderItem(col).text()
            cursor.execute("SELECT id FROM Классы WHERE Название = ?", (class_name,))
            class_id_result = cursor.fetchone()
            if not class_id_result:
                return
            class_id = class_id_result[0]

            # Получаем ID временного слота
            cursor.execute("""
                SELECT id FROM Временные_слоты 
                WHERE Номер_слота = ? AND Тип_дня = (
                    SELECT CASE WHEN Сокращенный_день THEN 'Сокращенный' ELSE 'Обычный' END
                    FROM Настройки_дней WHERE Порядковый_номер = ?
                )""", (lesson_number, day_number))
            time_slot_result = cursor.fetchone()
            if not time_slot_result:
                return
            time_slot_id = time_slot_result[0]

            # Удаляем запись из базы данных
            cursor.execute("""
                DELETE FROM Расписание 
                WHERE День_недели = ? AND ID_временного_слота = ? AND ID_класса = ?
            """, (day_number, time_slot_id, class_id))

            self.db_conn.commit()

        except sqlite3.Error as e:
            QMessageBox.critical(self.parent(), "Ошибка базы данных", f"Не удалось удалить данные: {str(e)}")
            self.db_conn.rollback()

class TeacherRoomDialog(QDialog):
    """Диалог выбора учителя и кабинета для предмета"""

    def __init__(self, all_teachers, all_rooms, recommended_teachers=None, recommended_rooms=None, parent=None):
        super().__init__(parent)
        self.selected_teacher = None
        self.selected_room = None
        self.db_conn = sqlite3.connect('school_schedule.db')  # Подключение к БД

        self.setWindowTitle("Выбор преподавателя и кабинета")
        self.setFixedSize(600, 400)

        layout = QVBoxLayout(self)

        # Основной макет с выбором учителя и кабинета
        main_layout = QHBoxLayout()

        # Получаем предмет из родительского виджета
        subject = self.get_current_subject()

        # Получаем рекомендуемых учителей и кабинеты для этого предмета
        subject_teachers = self.get_teachers_for_subject(subject)
        subject_rooms = self.get_rooms_for_subject(subject)

        # Разделяем учителей на рекомендуемых и остальных
        recommended_teachers = subject_teachers
        other_teachers = [t for t in all_teachers if t not in recommended_teachers]

        # Разделяем кабинеты на рекомендуемые и остальные
        recommended_rooms = subject_rooms
        other_rooms = [r for r in all_rooms if r not in recommended_rooms]

        # Панель выбора учителя
        teacher_layout = QVBoxLayout()
        teacher_layout.addWidget(QLabel("Выберите преподавателя:"))

        # Список учителей - сначала рекомендуемые, потом остальные
        self.teacher_list = QListWidget()
        self.teacher_list.setStyleSheet("""
            QListView {
                show-decoration-selected: 1;
            }
            QListView::item:selected {
                background-color: rgb(91,80,72);
                color: black;
            }
        """)

        # Добавляем рекомендуемых учителей (преподающих этот предмет)
        for teacher in recommended_teachers:
            item = QListWidgetItem(teacher)
            item.setBackground(QColor(171, 131, 105))
            item.setToolTip(f"Преподает {subject}")

            # Добавляем номер кабинета учителя
            teacher_room = self.get_teacher_room(teacher)
            if teacher_room:
                item.setText(f"{teacher} (каб. {teacher_room})")

            self.teacher_list.addItem(item)

        # Добавляем остальных учителей
        for teacher in other_teachers:
            item = QListWidgetItem(teacher)
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

        # Список кабинетов - сначала рекомендуемые, потом остальные
        self.room_list = QListWidget()
        self.room_list.setStyleSheet("""
            QListView {
                show-decoration-selected: 1;
            }
            QListView::item:selected {
                background-color: rgb(91,80,72);
                color: black;
            }
        """)

        # Добавляем рекомендуемые кабинеты (связанные с этим предметом)
        for room in recommended_rooms:
            item = QListWidgetItem(room)
            item.setBackground(QColor(171, 131, 105))
            item.setToolTip(f"Рекомендуемый кабинет для {subject}")
            self.room_list.addItem(item)

        # Добавляем остальные кабинеты
        for room in other_rooms:
            item = QListWidgetItem(room)
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

        # Подключаем сигнал выбора учителя для автоматического выбора его кабинета
        self.teacher_list.itemSelectionChanged.connect(self.on_teacher_selected)

    def get_current_subject(self):
        """Получает текущий выбранный предмет из родительского виджета"""
        try:
            # Получаем родительский виджет (редактор)
            editor = self.parent()
            # Получаем текст из редактора
            subject_text = editor.currentText()
            # Извлекаем сокращенное название предмета (первые буквы до пробела)
            subject_short = subject_text.split(" ")[0]

            # Получаем полное название предмета из БД
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT Название FROM Предметы WHERE Сокращение = ?", (subject_short,))
            result = cursor.fetchone()

            return result[0] if result else None
        except Exception as e:
            print(f"Error getting current subject: {e}")
            return None

    def get_teachers_for_subject(self, subject):
        """Получает список учителей, которые преподают указанный предмет"""
        if not subject:
            return []

        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT Учителя.ФИО 
                FROM Учителя
                JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
                JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
                WHERE Предметы.Название = ?""", (subject,))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting teachers for subject: {e}")
            return []

    def get_rooms_for_subject(self, subject):
        """Получает список кабинетов, рекомендованных для указанного предмета"""
        if not subject:
            return []

        try:
            cursor = self.db_conn.cursor()
            # Получаем кабинеты, привязанные к предмету
            cursor.execute("""
                SELECT DISTINCT Кабинеты.Номер 
                FROM Кабинеты
                JOIN Предметы ON Кабинеты.id = Предметы.Основной_кабинет_id
                WHERE Предметы.Название = ?""", (subject,))
            subject_rooms = [str(row[0]) for row in cursor.fetchall()]

            # Получаем кабинеты учителей, которые преподают этот предмет
            cursor.execute("""
                SELECT DISTINCT Кабинеты.Номер 
                FROM Кабинеты
                JOIN Учителя ON Кабинеты.id = Учителя.Основной_кабинет_id
                JOIN Учителя_Предметы ON Учителя.id = Учителя_Предметы.ID_учителя
                JOIN Предметы ON Учителя_Предметы.ID_предмета = Предметы.id
                WHERE Предметы.Название = ?""", (subject,))
            teacher_rooms = [str(row[0]) for row in cursor.fetchall()]

            # Объединяем списки и убираем дубликаты
            return list(set(subject_rooms + teacher_rooms))
        except Exception as e:
            print(f"Error getting rooms for subject: {e}")
            return []

    def get_teacher_room(self, teacher_name):
        """Получает номер кабинета для указанного учителя"""
        if not teacher_name:
            return None

        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT Кабинеты.Номер 
                FROM Учителя
                JOIN Кабинеты ON Учителя.Основной_кабинет_id = Кабинеты.id
                WHERE Учителя.ФИО = ?""", (teacher_name,))
            result = cursor.fetchone()
            return str(result[0]) if result else None
        except Exception as e:
            print(f"Error getting teacher room: {e}")
            return None

    def on_teacher_selected(self):
        """Автоматически выбирает кабинет учителя при выборе учителя"""
        selected_items = self.teacher_list.selectedItems()
        if not selected_items:
            return

        teacher_item = selected_items[0]
        if teacher_item.background().color() == QColor(171, 131, 105):
            # Если выбран рекомендуемый учитель, пытаемся найти его кабинет
            teacher_name = teacher_item.text().split(" (каб. ")[0]
            room = self.get_teacher_room(teacher_name)

            if room:
                # Ищем этот кабинет в списке
                for i in range(self.room_list.count()):
                    item = self.room_list.item(i)
                    if item.text() == room:
                        self.room_list.setCurrentItem(item)
                        break

    def filter_teachers(self, text):
        """Фильтрация списка учителей по введенному тексту"""
        for i in range(self.teacher_list.count()):
            item = self.teacher_list.item(i)
            item_text = item.text().split(" (каб. ")[0]  # Убираем номер кабинета для поиска
            item.setHidden(text.lower() not in item_text.lower())

    def filter_rooms(self, text):
        """Фильтрация списка кабинетов по введенному тексту"""
        for i in range(self.room_list.count()):
            item = self.room_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def accept_selection(self):
        """Обработка выбора учителя и кабинета"""
        teacher_item = self.teacher_list.currentItem()
        room_item = self.room_list.currentItem()

        if teacher_item:
            self.selected_teacher = teacher_item.text().split(" (каб. ")[0]
        else:
            self.selected_teacher = None

        if room_item:
            self.selected_room = room_item.text()
        else:
            self.selected_room = None

        self.accept()

    def get_selection(self):
        """Возвращает выбранные значения"""
        return self.selected_teacher, self.selected_room

    def closeEvent(self, event):
        """Закрывает соединение с БД при закрытии окна"""
        self.db_conn.close()
        super().closeEvent(event)


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
        self.db_conn.execute("PRAGMA foreign_keys = ON")

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
            self.load_schedule_from_db()

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
                    #item.setBackground(QColor(251, 206, 177))  # Стандартный цвет
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

    def load_schedule_from_db(self):
        """Загружает расписание из базы данных в таблицу"""
        try:
            cursor = self.db_conn.cursor()

            for col in range(1, self.table.columnCount()):
                class_name = self.table.horizontalHeaderItem(col).text()

                # Получаем ID класса
                cursor.execute("SELECT id FROM Классы WHERE Название = ?", (class_name,))
                class_id_result = cursor.fetchone()
                if not class_id_result:
                    continue
                class_id = class_id_result[0]

                # Получаем расписание для этого класса
                cursor.execute("""
                    SELECT 
                        r.День_недели, 
                        ts.Номер_слота,
                        p.Название AS предмет,
                        p.Сокращение,
                        u.ФИО AS учитель,
                        k.Номер AS кабинет
                    FROM Расписание r
                    JOIN Временные_слоты ts ON r.ID_временного_слота = ts.id
                    JOIN Предметы p ON r.ID_предмета = p.id
                    JOIN Учителя u ON r.ID_учителя = u.id
                    JOIN Кабинеты k ON r.ID_кабинета = k.id
                    WHERE r.ID_класса = ?
                    ORDER BY r.День_недели, ts.Номер_слота
                """, (class_id,))

                for record in cursor.fetchall():
                    day_number, lesson_number, subject, subject_short, teacher, room = record

                    # Вычисляем строку в таблице
                    row = (day_number - 1) * 9 + (lesson_number - 1)

                    # Получаем дополнительные ID
                    cursor.execute("SELECT id FROM Предметы WHERE Название = ?", (subject,))
                    subject_id = cursor.fetchone()[0]

                    cursor.execute("SELECT id FROM Учителя WHERE ФИО = ?", (teacher,))
                    teacher_id = cursor.fetchone()[0]

                    cursor.execute("SELECT id FROM Кабинеты WHERE Номер = ?", (room,))
                    room_id = cursor.fetchone()[0]

                    # Создаем данные для ячейки
                    full_data = {
                        'subject': subject,
                        'subject_id': subject_id,
                        'teacher': teacher,
                        'teacher_id': teacher_id,
                        'room': room,
                        'room_id': room_id,
                        'day': day_number,
                        'lesson': lesson_number,
                        'class_id': class_id
                    }

                    # Создаем элемент таблицы
                    item = QTableWidgetItem(f"{subject} ({room})")
                    item.setData(Qt.ItemDataRole.UserRole, full_data)
                    item.setBackground(QColor(127, 111, 102))
                    item.setForeground(QColor(255, 255, 255))

                    self.table.setItem(row, col, item)

            # Проверяем конфликты после загрузки
            self.check_teacher_conflicts()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось загрузить расписание: {str(e)}")

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

    # Проверяем наличие базы данных и создаем при необходимости
    try:
        conn = sqlite3.connect('school_schedule.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Классы'")
        if not cursor.fetchone():
            # Если таблицы не существует, создаем базу данных
            import create_database  # Импортируем модуль для создания БД

            create_database.create_and_fill_database()
        conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось проверить/создать базу данных: {str(e)}")
        sys.exit(1)

    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())

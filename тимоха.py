# Импорт необходимых модулей
import sys  # Для работы с системными функциями

# Импорт компонентов PyQt6
from PyQt6.QtWidgets import (
    QApplication,  # Главный класс приложения
    QMainWindow,  # Класс главного окна
    QTableWidget,  # Виджет таблицы
    QTableWidgetItem,  # Элемент таблицы
    QVBoxLayout,  # Вертикальный макет
    QWidget,  # Базовый виджет
    QLabel,  # Текстовая метка
    QHBoxLayout,  # Горизонтальный макет
    QScrollArea,  # Область прокрутки
    QPushButton,  # Кнопка
    QDialog,  # Диалоговое окно
    QComboBox,  # Выпадающий список
    QLineEdit,  # Поле ввода
    QFormLayout,  # Макет формы
    QGridLayout  # Сеточный макет
)
from PyQt6.QtCore import Qt, QSize  # Основные константы и классы Qt
from PyQt6.QtGui import (
    QColor,  # Цвет
    QPainter,  # Для рисования
    QPainterPath,  # Путь для рисования
    QFont,  # Шрифт
    QFontMetrics,  # Метрики шрифта
    QIcon,  # Иконка
    QPixmap  # Изображение
)
from PyQt6.QtCore import QRectF  # Прямоугольник с float-координатами


class ClassSetupDialog(QDialog):
    """Диалоговое окно для настройки классов (11 строк с настройками)"""

    def __init__(self, parent=None):
        # Инициализация диалогового окна
        super().__init__(parent)  # Вызов конструктора родительского класса
        self.setWindowTitle("Настройка классов")  # Заголовок окна
        self.setFixedSize(500, 500)  # Фиксированный размер окна (ширина, высота)

        # Основной вертикальный макет для диалога
        layout = QVBoxLayout(self)

        # Список для хранения элементов управления (выпадающих списков)
        self.class_entries = []

        # Создаем 11 строк (для классов с 1 по 11)
        for class_num in range(1, 12):
            # Горизонтальный макет для одной строки
            row_layout = QHBoxLayout()

            # Метка с номером класса
            label = QLabel(f"{class_num} класс:")

            # Выпадающий список для начальной буквы
            letter_from = QComboBox()
            letter_from.addItem("нету")  # Вариант по умолчанию
            # Добавляем буквы от 'а' до 'е' (коды 1072-1077 в Unicode)
            letter_from.addItems([chr(i) for i in range(ord('а'), ord('ф') +1)])

            # Выпадающий список для конечной буквы
            letter_to = QComboBox()
            letter_to.addItem("нету")
            letter_to.addItems([chr(i) for i in range(ord('а'), ord('ф') +1)])

            # Добавляем элементы в строку
            row_layout.addWidget(label)  # Метка класса
            row_layout.addWidget(QLabel("от:"))  # Метка "от"
            row_layout.addWidget(letter_from)  # Выпадающий список "от"
            row_layout.addWidget(QLabel("до:"))  # Метка "до"
            row_layout.addWidget(letter_to)  # Выпадающий список "до"

            # Добавляем строку в основной макет
            layout.addLayout(row_layout)
            # Сохраняем элементы управления для этой строки
            self.class_entries.append((letter_from, letter_to))

        # Создаем макет для кнопок
        buttons_layout = QHBoxLayout()

        # Кнопка OK
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)  # При нажатии закрываем с результатом OK

        # Кнопка Отмена
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)  # При нажатии закрываем без результата

        # Добавляем кнопки в макет
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        # Добавляем макет кнопок в основной макет
        layout.addLayout(buttons_layout)

    def get_classes(self):
        """Генерирует список классов на основе выбранных параметров"""
        classes = []  # Список для хранения результатов

        # Перебираем все строки (class_num начинается с 1)
        for class_num, (letter_from, letter_to) in enumerate(self.class_entries, 1):
            # Получаем выбранные значения
            from_text = letter_from.currentText()
            to_text = letter_to.currentText()

            # Пропускаем если выбрано "нету" в любом из списков
            if from_text == "нету" or to_text == "нету":
                continue

            # Получаем коды символов для выбранных букв
            from_code = ord(from_text)
            to_code = ord(to_text)

            # Генерируем все буквы в диапазоне (учитываем порядок)
            for letter_code in range(min(from_code, to_code), max(from_code, to_code) + 1):
                # Формируем название класса (например "5а") и добавляем в список
                classes.append(f"{class_num}{chr(letter_code)}")

        return classes


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
            self.frozen_table.setItem(0, 0,
                                      header_item)  # Устанавливаем заголовок в первую ячейку фиксированной таблицы

            # Устанавливаем фиксированную высоту для заголовка
            header_fixed_height = 25  # Укажите желаемый размер высоты заголовка в пикселях
            self.frozen_table.setRowHeight(0,
                                           header_fixed_height)  # Устанавливаем высоту заголовка фиксированной таблицы

            # Копируем данные из основной таблицы
            for row in range(1, self.table.rowCount() + 1):
                item = self.table.item(row - 1, 0).clone()
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.frozen_table.setItem(row, 0, item)
                # Устанавливаем высоту остальных строк фиксированной таблицы в 28 пикселей
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.showFullScreen()  # Открываем окно в полноэкранном режиме
    sys.exit(app.exec())

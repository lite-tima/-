import sqlite3
from datetime import datetime


def create_and_fill_database():
    # Подключаемся к базе данных (или создаем новую)
    conn = sqlite3.connect('school_schedule.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Удаляем существующие таблицы (для чистого создания)
    cursor.execute("DROP TABLE IF EXISTS Расписание")
    cursor.execute("DROP TABLE IF EXISTS Учителя_Предметы")
    cursor.execute("DROP TABLE IF EXISTS Учителя")
    cursor.execute("DROP TABLE IF EXISTS Предметы")
    cursor.execute("DROP TABLE IF EXISTS Кабинеты")
    cursor.execute("DROP TABLE IF EXISTS Классы")
    cursor.execute("DROP TABLE IF EXISTS Временные_слоты")
    cursor.execute("DROP TABLE IF EXISTS Настройки_дней")

    # 1. Создаем таблицы с улучшенной структурой
    tables_sql = [
        '''CREATE TABLE IF NOT EXISTS Классы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Название TEXT NOT NULL UNIQUE,
            Количество_учеников INTEGER NOT NULL DEFAULT 25
        )''',

        '''CREATE TABLE IF NOT EXISTS Предметы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Название TEXT NOT NULL UNIQUE,
            Сокращение TEXT NOT NULL UNIQUE,
            Основной_кабинет_id INTEGER,
            FOREIGN KEY (Основной_кабинет_id) REFERENCES Кабинеты(id)
                ON DELETE SET NULL ON UPDATE CASCADE
        )''',

        '''CREATE TABLE IF NOT EXISTS Кабинеты (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Номер TEXT NOT NULL UNIQUE,
            Вместимость INTEGER NOT NULL
        )''',

        '''CREATE TABLE IF NOT EXISTS Учителя (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ФИО TEXT NOT NULL,
            Сокращенное_имя TEXT NOT NULL,
            Основной_кабинет_id INTEGER,
            FOREIGN KEY (Основной_кабинет_id) REFERENCES Кабинеты(id)
                ON DELETE SET NULL ON UPDATE CASCADE
        )''',

        '''CREATE TABLE IF NOT EXISTS Учителя_Предметы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_учителя INTEGER NOT NULL,
            ID_предмета INTEGER NOT NULL,
            FOREIGN KEY (ID_учителя) REFERENCES Учителя(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (ID_предмета) REFERENCES Предметы(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            UNIQUE(ID_учителя, ID_предмета)
        )''',

        '''CREATE TABLE IF NOT EXISTS Временные_слоты (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Номер_слота INTEGER NOT NULL,
            Время_начала TEXT NOT NULL,
            Время_окончания TEXT NOT NULL,
            Тип_дня TEXT NOT NULL DEFAULT 'Обычный',
            UNIQUE(Номер_слота, Тип_дня)
        )''',

        '''CREATE TABLE IF NOT EXISTS Настройки_дней (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            День_недели TEXT NOT NULL UNIQUE,
            Порядковый_номер INTEGER NOT NULL UNIQUE,
            Сокращенный_день BOOLEAN DEFAULT FALSE,
            Учебный_день BOOLEAN DEFAULT TRUE
        )''',

        '''CREATE TABLE IF NOT EXISTS Расписание (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_класса INTEGER NOT NULL,
            ID_предмета INTEGER NOT NULL,
            ID_учителя INTEGER NOT NULL,
            ID_кабинета INTEGER NOT NULL,
            ID_временного_слота INTEGER NOT NULL,
            День_недели INTEGER NOT NULL,
            Группа INTEGER DEFAULT 1,
            FOREIGN KEY (ID_класса) REFERENCES Классы(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (ID_предмета) REFERENCES Предметы(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (ID_учителя) REFERENCES Учителя(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (ID_кабинета) REFERENCES Кабинеты(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (ID_временного_слота) REFERENCES Временные_слоты(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (День_недели) REFERENCES Настройки_дней(Порядковый_номер)
                ON DELETE CASCADE ON UPDATE CASCADE,
            UNIQUE(ID_класса, День_недели, ID_временного_слота, Группа)
        )'''
    ]

    for table_sql in tables_sql:
        cursor.execute(table_sql)

    # 2. Создаем индексы для ускорения запросов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_расписание_класс ON Расписание(ID_класса)",
        "CREATE INDEX IF NOT EXISTS idx_расписание_день ON Расписание(День_недели)",
        "CREATE INDEX IF NOT EXISTS idx_расписание_слот ON Расписание(ID_временного_слота)",
        "CREATE INDEX IF NOT EXISTS idx_учителя_предметы ON Учителя_Предметы(ID_учителя, ID_предмета)",
        "CREATE INDEX IF NOT EXISTS idx_предметы_название ON Предметы(Название)",
        "CREATE INDEX IF NOT EXISTS idx_учителя_фио ON Учителя(ФИО)"
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    # 3. Заполняем таблицы тестовыми данными

    # Настройки дней недели
    cursor.executemany('''
        INSERT INTO Настройки_дней (День_недели, Порядковый_номер, Сокращенный_день, Учебный_день) 
        VALUES (?, ?, ?, ?)
    ''', [
        ('Понедельник', 1, False, True),
        ('Вторник', 2, False, True),
        ('Среда', 3, True, True),  # Сокращенный день
        ('Четверг', 4, False, True),
        ('Пятница', 5, False, True),
        ('Суббота', 6, False, False),  # Выходной
        ('Воскресенье', 7, False, False)  # Выходной
    ])

    # Классы
    cursor.executemany('''
        INSERT INTO Классы (Название, Количество_учеников) 
        VALUES (?, ?)
    ''', [
        ('5А', 25), ('5Б', 24),
        ('6А', 26), ('6Б', 23),
        ('7А', 27), ('7Б', 22),
        ('8А', 25), ('8Б', 24),
        ('9А', 26), ('9Б', 23),
        ('10А', 25), ('10Б', 20),
        ('11А', 22), ('11Б', 21)
    ])

    # Кабинеты
    cursor.executemany('''
        INSERT INTO Кабинеты (Номер, Вместимость) 
        VALUES (?, ?)
    ''', [
        ('101', 25), ('102', 25),
        ('103', 25), ('201', 30),
        ('202', 30), ('203', 30),
        ('301', 20), ('302', 20),
        ('303', 20), ('Спортзал', 40)
    ])

    # Предметы (с указанием основного кабинета)
    cursor.executemany('''
        INSERT INTO Предметы (Название, Сокращение, Основной_кабинет_id) 
        VALUES (?, ?, ?)
    ''', [
        ('Математика', 'Мат', 1),
        ('Русский язык', 'Рус', 2),
        ('Литература', 'Лит', 3),
        ('Физика', 'Физ', 7),
        ('Химия', 'Хим', 8),
        ('Биология', 'Био', 9),
        ('История', 'Ист', 1),
        ('География', 'Гео', 2),
        ('Английский язык', 'Анг', 3),
        ('Физкультура', 'Физ-ра', 10),
        ('Информатика', 'Инф', 9)
    ])

    # Учителя (с указанием основного кабинета)
    cursor.executemany('''
        INSERT INTO Учителя (ФИО, Сокращенное_имя, Основной_кабинет_id) 
        VALUES (?, ?, ?)
    ''', [
        ('Иванова Анна Петровна', 'Иванова А.П.', 1),
        ('Петров Борис Васильевич', 'Петров Б.В.', 2),
        ('Сидорова Виктория Сергеевна', 'Сидорова В.С.', 3),
        ('Кузнецов Геннадий Иванович', 'Кузнецов Г.И.', 7),
        ('Смирнова Дарья Олеговна', 'Смирнова Д.О.', 8),
        ('Федоров Евгений Николаевич', 'Федоров Е.Н.', 9),
        ('Николаева Жанна Владимировна', 'Николаева Ж.В.', 1),
        ('Алексеев Константин Дмитриевич', 'Алексеев К.Д.', 2),
        ('Павлова Людмила Александровна', 'Павлова Л.А.', 3),
        ('Семенов Михаил Игоревич', 'Семенов М.И.', 10)
    ])

    # Учителя_Предметы (какие учителя какие предметы ведут)
    cursor.executemany('''
        INSERT INTO Учителя_Предметы (ID_учителя, ID_предмета) 
        VALUES (?, ?)
    ''', [
        (1, 1),   # Иванова - Математика
        (2, 2),   # Петров - Русский язык
        (3, 3),   # Сидорова - Литература
        (4, 4),   # Кузнецов - Физика
        (5, 5),   # Смирнова - Химия
        (6, 6),   # Федоров - Биология
        (7, 7),   # Николаева - История
        (8, 8),   # Алексеев - География
        (9, 9),   # Павлова - Английский
        (10, 10), # Семенов - Физкультура
        (4, 11),  # Кузнецов также может преподавать Информатику
        (9, 1)    # Павлова также может преподавать Математику
    ])

    # Временные_слоты (обычные дни)
    cursor.executemany('''
        INSERT INTO Временные_слоты (Номер_слота, Время_начала, Время_окончания, Тип_дня) 
        VALUES (?, ?, ?, ?)
    ''', [
        (1, '08:00', '08:40', 'Обычный'),
        (2, '08:45', '09:25', 'Обычный'),
        (3, '09:40', '10:20', 'Обычный'),
        (4, '10:35', '11:15', 'Обычный'),
        (5, '11:30', '12:10', 'Обычный'),
        (6, '12:15', '12:55', 'Обычный'),
        (7, '13:00', '13:40', 'Обычный'),
        (8, '13:45', '14:25', 'Обычный'),
        (9, '14:30', '15:10', 'Обычный'),
        (10, '15:15', '15:55', 'Обычный')
    ])

    # Временные_слоты (сокращенные дни)
    cursor.executemany('''
        INSERT INTO Временные_слоты (Номер_слота, Время_начала, Время_окончания, Тип_дня) 
        VALUES (?, ?, ?, ?)
    ''', [
        (1, '08:00', '08:30', 'Сокращенный'),
        (2, '08:35', '09:05', 'Сокращенный'),
        (3, '09:20', '09:50', 'Сокращенный'),
        (4, '10:05', '10:35', 'Сокращенный'),
        (5, '10:50', '11:20', 'Сокращенный'),
        (6, '11:25', '11:55', 'Сокращенный'),
        (7, '12:00', '12:30', 'Сокращенный'),
        (8, '12:35', '13:05', 'Сокращенный'),
        (9, '13:10', '13:40', 'Сокращенный'),
        (10, '13:45', '14:15', 'Сокращенный')
    ])

    # Добавляем тестовое расписание
    # Понедельник (обычный день)
    cursor.executemany('''
        INSERT INTO Расписание (
            ID_класса, ID_предмета, ID_учителя, ID_кабинета, 
            ID_временного_слота, День_недели, Группа
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 1, 1, 1, 1, 1, 1),  # 5А - Математика - Иванова - 101 - 1 урок
        (1, 2, 2, 2, 2, 1, 1),   # 5А - Русский - Петров - 102 - 2 урок
        (1, 9, 9, 3, 3, 1, 1),   # 5А - Английский - Павлова - 103 - 3 урок
        (2, 1, 1, 1, 1, 1, 1),   # 5Б - Математика - Иванова - 101 - 1 урок
        (2, 3, 3, 3, 2, 1, 1),   # 5Б - Литература - Сидорова - 103 - 2 урок
        (3, 4, 4, 7, 3, 1, 1)    # 6А - Физика - Кузнецов - 301 - 3 урок
    ])

    # Среда (сокращенный день)
    cursor.executemany('''
        INSERT INTO Расписание (
            ID_класса, ID_предмета, ID_учителя, ID_кабинета, 
            ID_временного_слота, День_недели, Группа
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 10, 10, 10, 1, 3, 1),  # 5А - Физкультура - Семенов - Спортзал - 1 урок
        (1, 4, 4, 7, 2, 3, 1),     # 5А - Физика - Кузнецов - 301 - 2 урок
        (2, 10, 10, 10, 3, 3, 1),  # 5Б - Физкультура - Семенов - Спортзал - 3 урок
        (3, 1, 1, 1, 1, 3, 1)      # 6А - Математика - Иванова - 101 - 1 урок
    ])

    conn.commit()
    conn.close()
    print("База данных успешно создана и заполнена тестовыми данными!")


if __name__ == '__main__':
    create_and_fill_database()

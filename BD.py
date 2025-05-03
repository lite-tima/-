import sqlite3
from datetime import datetime


def create_database():
    conn = sqlite3.connect('schedule.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Таблица классов
    cursor.execute('''CREATE TABLE IF NOT EXISTS Классы (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      Название TEXT NOT NULL UNIQUE,
                      Количество_учеников INTEGER NOT NULL DEFAULT 25,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')

    # 2. Таблица предметов
    cursor.execute('''CREATE TABLE IF NOT EXISTS Предметы (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      Название TEXT NOT NULL UNIQUE,
                      Сокращение TEXT,
                      Делится_на_группы INTEGER DEFAULT 0,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')

    # 3. Таблица кабинетов
    cursor.execute('''CREATE TABLE IF NOT EXISTS Кабинеты (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      Номер TEXT NOT NULL UNIQUE,
                      Вместимость INTEGER NOT NULL,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')

    # 4. Таблица учителей
    cursor.execute('''CREATE TABLE IF NOT EXISTS Учителя (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      ФИО TEXT NOT NULL,
                      Сокращенное_имя TEXT,
                      Основной_кабинет_id INTEGER,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (Основной_кабинет_id) REFERENCES Кабинеты(id)
                  )''')

    # 5. Связь учителей и предметов
    cursor.execute('''CREATE TABLE IF NOT EXISTS Учителя_Предметы (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      ID_учителя INTEGER NOT NULL,
                      ID_предмета INTEGER NOT NULL,
                      Может_преподавать_группы INTEGER DEFAULT 0,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (ID_учителя) REFERENCES Учителя(id),
                      FOREIGN KEY (ID_предмета) REFERENCES Предметы(id),
                      UNIQUE(ID_учителя, ID_предмета)
                  )''')

    # 6. Таблица временных слотов
    cursor.execute('''CREATE TABLE IF NOT EXISTS Временные_слоты (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      Номер_слота INTEGER NOT NULL,
                      Время_начала TEXT NOT NULL,
                      Время_окончания TEXT NOT NULL,
                      Тип_дня INTEGER DEFAULT 0,
                      Дата_создания TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      Дата_обновления TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      UNIQUE(Номер_слота, Тип_дня)
                  )''')

    # Триггеры для обновления временных меток
    tables = ['Классы', 'Предметы', 'Кабинеты', 'Учителя', 'Учителя_Предметы', 'Временные_слоты']
    for table in tables:
        cursor.execute(f'''CREATE TRIGGER IF NOT EXISTS обновить_дату_{table}
                           AFTER UPDATE ON {table}
                           FOR EACH ROW
                           BEGIN
                               UPDATE {table} SET Дата_обновления = CURRENT_TIMESTAMP WHERE id = OLD.id;
                           END''')

    conn.commit()
    conn.close()
    print("Пустая база данных с русскими названиями успешно создана")


if __name__ == '__main__':
    create_database()

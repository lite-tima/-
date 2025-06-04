import sqlite3


def create_database():
    conn = sqlite3.connect('tg_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        school TEXT,
        class TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("База данных tg_bot.db успешно создана")


if __name__ == '__main__':
    create_database()
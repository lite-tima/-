import logging
import sqlite3
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)


from PyQt6.QtWidgets import (
    QApplication
)
import pytz
from datetime import timezone

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний разговора
CHOOSING_SCHOOL, CHOOSING_CLASS, CONFIRM_DELETE = range(3)

# Названия баз данных
USER_DB = 'BD_TG_BOT.db'
SCHEDULE_DB = 'school_schedule.db'

# Данные для выбора школы
SCHOOLS = {
    "Башкирский Лицей №1 им. С. Зиганшина": "🏫Башкирский Лицей №1 им. С. Зиганшина🏫"
}


def get_available_classes():
    """Получаем список всех доступных классов из базы данных расписания"""
    conn = sqlite3.connect(SCHEDULE_DB)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT Название FROM Классы")
        classes = [row[0] for row in cursor.fetchall()]
        # Сортируем классы: сначала по номеру, затем по букве
        classes.sort(key=lambda x: (int(''.join(filter(str.isdigit, x))),
                                    ''.join(filter(str.isalpha, x))))
        return classes
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении классов из базы данных: {e}")
        return []
    finally:
        conn.close()


def init_user_database():
    """Инициализация базы данных пользователей"""
    conn = sqlite3.connect(USER_DB)
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
    logger.info("База данных пользователей инициализирована")


def is_user_registered(user_id):
    """Проверяем, зарегистрирован ли пользователь"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def delete_user(user_id):
    """Удаляем пользователя из базы данных"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"Пользователь {user_id} удален из базы данных")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало взаимодействия с ботом"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} начал взаимодействие.")

    if is_user_registered(user.id):
        # Пользователь уже зарегистрирован
        reply_keyboard = [["Удалить аккаунт", "Оставить"]]

        await update.message.reply_text(
            "Вы уже зарегистрированы! Хотите удалить аккаунт и зарегистрироваться заново?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return CONFIRM_DELETE
    else:
        # Начинаем процесс регистрации
        reply_keyboard = [[school] for school in SCHOOLS.values()]

        await update.message.reply_text(
            'Добро пожаловать! Выберите вашу школу:',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return CHOOSING_SCHOOL


async def school_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора школы и переход к выбору класса"""
    user = update.message.from_user
    school = update.message.text

    if school not in SCHOOLS.values():
        await update.message.reply_text(
            'Пожалуйста, выберите школу из предложенных вариантов.',
            reply_markup=ReplyKeyboardMarkup(
                [[school] for school in SCHOOLS.values()],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return CHOOSING_SCHOOL

    context.user_data['school'] = school
    logger.info(f"Пользователь {user.first_name} выбрал школу: {school}")

    # Получаем список доступных классов
    available_classes = get_available_classes()

    if not available_classes:
        await update.message.reply_text(
            'В данный момент нет доступных классов для выбора. Пожалуйста, попробуйте позже.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Разбиваем классы на строки по 3 для удобного отображения
    classes_rows = [available_classes[i:i + 3] for i in range(0, len(available_classes), 3)]

    await update.message.reply_text(
        'Отлично! Теперь выберите ваш класс из списка:',
        reply_markup=ReplyKeyboardMarkup(
            classes_rows,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    return CHOOSING_CLASS


async def class_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбранного класса"""
    user = update.message.from_user
    selected_class = update.message.text

    # Проверяем, что класс есть в доступных
    available_classes = get_available_classes()
    if selected_class not in available_classes:
        await update.message.reply_text(
            'Пожалуйста, выберите класс из предложенных вариантов.',
            reply_markup=ReplyKeyboardMarkup(
                [available_classes[i:i + 3] for i in range(0, len(available_classes), 3)],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return CHOOSING_CLASS

    school = context.user_data['school']

    # Сохраняем данные в базу
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, school, class) VALUES (?, ?, ?)",
        (user.id, school, selected_class)
    )
    conn.commit()
    conn.close()

    logger.info(f"Регистрация: {user.first_name}, школа {school}, класс {selected_class}")

    await update.message.reply_text(
        f'🎉 Регистрация завершена! 🎉\n\n'
        f'🏫 Школа: {school}\n'
        f'📚 Класс: {selected_class}\n\n'
        'Теперь вы будете получать уведомления!',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения удаления аккаунта"""
    user = update.message.from_user
    choice = update.message.text

    if choice == "Удалить аккаунт":
        delete_user(user.id)
        await update.message.reply_text(
            "Ваш аккаунт удален. Нажмите /start для новой регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Ваши данные сохранены. Для изменения удалите аккаунт через /start",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} отменил регистрацию.")
    await update.message.reply_text(
        'Регистрация отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")


async def send_schedule_update(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Отправляет уведомление об изменении расписания всем зарегистрированным пользователям"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    try:
        # Получаем всех зарегистрированных пользователей
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for user_id in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id[0],
                    text=message
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user_id[0]}: {e}")

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении пользователей из БД: {e}")
    finally:
        conn.close()


async def get_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет текущее расписание пользователю"""
    user_id = update.message.from_user.id

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT class FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start")
        return

    class_name = result[0]
    schedule = get_class_schedule(class_name)  # Нужно реализовать эту функцию

    await update.message.reply_text(f"📅 Расписание для {class_name}:\n\n{schedule}")


# Добавьте обработчик в main():


def get_class_schedule(class_name):
    """Возвращает форматированное расписание для указанного класса"""
    conn = sqlite3.connect(SCHEDULE_DB)
    cursor = conn.cursor()

    try:
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        result = []

        for day_num, day_name in enumerate(days):
            cursor.execute("""
                SELECT Урок, Предмет, Учитель, Кабинет 
                FROM Расписание 
                WHERE Класс = ? AND День = ?
                ORDER BY Урок
            """, (class_name, day_num + 1))

            lessons = cursor.fetchall()
            day_schedule = [f"📅 {day_name}:"]

            for lesson in lessons:
                lesson_num, subject, teacher, room = lesson
                day_schedule.append(
                    f"{lesson_num}. {subject} ({teacher}, каб. {room})"
                )

            result.append("\n".join(day_schedule))

        return "\n\n".join(result)

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        return "Не удалось загрузить расписание"
    finally:
        conn.close()


def main():
    import sys
    from Edit_Schedule import Edit_Schedule

    # Инициализация приложения Qt
    app = QApplication(sys.argv)

    # Создаем и настраиваем бота
    application = Application.builder().token("7740433474:AAGMa_q92stKOJr5hcUFAn5E6C6Q9yR6wBw").build()

    # Создаем главное окно и передаем контекст бота
    window = Edit_Schedule(bot_context=application)
    window.show()

    # Запускаем бота в отдельном потоке
    import threading
    bot_thread = threading.Thread(target=application.run_polling, daemon=True)
    bot_thread.start()

    # Запускаем Qt приложение
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
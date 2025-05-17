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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний разговора
CHOOSING_SCHOOL, CHOOSING_CLASS, CONFIRM_DELETE, SEND_MASSAGE = range(4)

# Названия баз данных
USER_DB = 'BD_TG_BOT.db'
SCHEDULE_DB = 'school_schedule.db'

# Данные для выбора школы
SCHOOLS = {
    "Башкирский Лицей №1 им. С. Зиганшина": "🏫Башкирский Лицей №1 им. С. Зиганшина🏫"
}


bot_app = None


async def start_bot():
    """Запуск бота и сохранение экземпляра приложения"""
    global bot_app
    bot_app = Application.builder().token("7740433474:AAGMa_q92stKOJr5hcUFAn5E6C6Q9yR6wBw").build()
    await bot_app.initialize()
    await bot_app.start()
    print("Telegram-бот запущен")


async def send_message(message_text):
    """Отправляет сообщение всем пользователям из REGISTERED_USERS"""
    global bot_app
    if not bot_app:
        print("Бот не запущен")
        return

    for user_id in REGISTERED_USERS:
        try:
            await bot_app.bot.send_message(chat_id=user_id, text=message_text)
            print(f"Сообщение отправлено пользователю {user_id}")
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
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

    # Переход к выбору класса
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
    # --- ЗАПУСК ПЕРИОДИЧЕСКОЙ ОТПРАВКИ СООБЩЕНИЙ ---
    # Удаляем старую задачу, если она была
    job_name = f"periodic_message_{user.id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    # Добавляем новую задачу
    context.job_queue.run_repeating(
        send_massage_periodic,
        interval=5,
        first=0,
        chat_id=update.effective_chat.id,
        name=job_name
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

async def send_massage_periodic(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая отправляет сообщение каждые 5 секунд"""
    job = context.job
    chat_id = job.chat_id
    try:
        await context.bot.send_message(chat_id=chat_id, text="Просто тестовое сообщение каждые 5 секунд")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")


def main() -> None:
    """Запуск бота"""
    # Инициализация БД
    init_user_database()

    # Создаем и настраиваем бота
    application = Application.builder().token("7740433474:AAGMa_q92stKOJr5hcUFAn5E6C6Q9yR6wBw").build()

    # Обработчики диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_SCHOOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_chosen)],
            CHOOSING_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_chosen)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Регистрируем обработчики
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    application.run_polling()


if __name__ == '__main__':
    main()
import logging
import json  # Добавьте этот импорт в начало файла TG_BOT_SCHEDULE.py
import sqlite3
import requests
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
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
CHOOSING_SCHOOL, CHOOSING_CLASS, CONFIRM_DELETE = range(3)

# Названия баз данных
USER_DB = 'BD_TG_BOT.db'
SCHEDULE_DB = 'school_schedule.db'

# Данные для выбора школы
SCHOOLS = {
    "Башкирский Лицей №1 им. С. Зиганшина": "🏫Башкирский Лицей №1 им. С. Зиганшина🏫"
}

# Токен бота
TOKEN = "7740433474:AAGMa_q92stKOJr5hcUFAn5E6C6Q9yR6wBw"


# В класс NotificationHandler добавить более информативное сообщение:
class NotificationHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/notify':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data['message']
                class_name = data.get('class_name')

                if class_name:
                    Thread(target=lambda: send_notification_to_class_users(class_name, message)).start()
                else:
                    Thread(target=lambda: send_notification_to_all_users(message)).start()

                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                logger.error(f"Notification error: {str(e)}")
                self.wfile.write(json.dumps({"status": "error"}).encode())

def get_user_ids_by_class(class_name):
    """Возвращает список user_id для указанного класса"""
    conn = sqlite3.connect(USER_DB)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE class = ?", (class_name,))
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def send_notification_to_class_users(class_name, message):
    """Отправляет сообщение пользователям указанного класса"""
    user_ids = get_user_ids_by_class(class_name)
    for user_id in user_ids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {str(e)}")

def run_notification_server():
    server = HTTPServer(('localhost', 8000), NotificationHandler)
    server.serve_forever()


def get_all_user_ids():
    """Возвращает список всех user_id из базы данных"""
    conn = sqlite3.connect(USER_DB)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def send_notification_to_all_users(message: str):
    """Отправляет сообщение всем пользователям через Telegram API"""
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {str(e)}")


def get_available_classes():
    """Получаем список всех доступных классов из базы данных расписания"""
    conn = sqlite3.connect(SCHEDULE_DB)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT Название FROM Классы")
        classes = [row[0] for row in cursor.fetchall()]
        classes.sort(key=lambda x: (int(''.join(filter(str.isdigit, x))),
                                    ''.join(filter(str.isalpha, x))))
        return classes
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении классов: {e}")
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
    logger.info(f"Пользователь {user_id} удален")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало взаимодействия с ботом"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} начал взаимодействие")

    if is_user_registered(user.id):
        reply_keyboard = [["Удалить аккаунт", "Оставить"]]
        await update.message.reply_text(
            "Вы уже зарегистрированы! Хотите удалить аккаунт?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return CONFIRM_DELETE
    else:
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
    """Обработка выбора школы"""
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

    available_classes = get_available_classes()
    if not available_classes:
        await update.message.reply_text(
            'Нет доступных классов. Попробуйте позже.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    classes_rows = [available_classes[i:i + 3] for i in range(0, len(available_classes), 3)]
    await update.message.reply_text(
        'Выберите ваш класс:',
        reply_markup=ReplyKeyboardMarkup(
            classes_rows,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CHOOSING_CLASS


async def class_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора класса"""
    user = update.message.from_user
    selected_class = update.message.text
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
            "Ваши данные сохранены.",
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации"""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} отменил регистрацию")
    await update.message.reply_text(
        'Регистрация отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")


def main() -> None:
    """Запуск бота"""
    init_user_database()

    # Запускаем сервер уведомлений в отдельном потоке
    server_thread = Thread(target=run_notification_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_SCHOOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_chosen)],
            CHOOSING_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_chosen)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    logger.info("Бот запущен и готов к работе")
    application.run_polling()


if __name__ == '__main__':
    main()
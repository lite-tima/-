import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from io import BytesIO
import os
import sys
import asyncio


# Настройка бота
logging.basicConfig(level=logging.INFO)
bot = Bot(token="7740433474:AAGMa_q92stKOJr5hcUFAn5E6C6Q9yR6wBw")
dp = Dispatcher(storage=MemoryStorage())
# Шаблоны таблиц и их полей
TABLE_TEMPLATES = {
    "classes": {
        "fields": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
        },
        "followups": {
            "class_letter": {"field": "letter", "type": "TEXT"},
            "class_year": {"field": "year", "type": "INTEGER"},
        },
        "question_key": "classes",
    },
    "subjects": {
        "fields": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
        },
        "followups": {
            "subject_short_name": {"field": "short_name", "type": "TEXT"},
        },
        "question_key": "subjects",
    },
    "teachers": {
        "fields": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
        },
        "followups": {
            "teacher_name_format": {
                "field": "name_format",
                "type": "TEXT",
                "options": ["Полное ФИО", "Фамилия + инициалы"],
            },
        },
        "question_key": "teachers",
    },
    "classrooms": {
        "fields": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
        },
        "followups": {
            "classroom_type": {"field": "type", "type": "TEXT"},
        },
        "question_key": "classrooms",
    },
}

# Вопросы и уточнения
QUESTIONS = [
    {"text": "Нужны ли классы (например, 5А, 10Б)?", "key": "classes"},
    {"text": "Нужны ли предметы (математика, физика)?", "key": "subjects"},
    {"text": "Нужны ли учителя?", "key": "teachers"},
    {"text": "Нужны ли аудитории (кабинеты)?", "key": "classrooms"},
    {"text": "Привязывать учителей к предметам?", "key": "link_teacher_subject"},
    {"text": "Учитывать дни недели в расписании (Пн-Пт)?", "key": "use_weekdays"},
]

# Уточняющие вопросы
FOLLOW_UPS = {
    "classes": [
        {"text": "Добавлять букву класса (например, 5А)?", "key": "class_letter"},
        {"text": "Учитывать учебный год для классов?", "key": "class_year"},
    ],
    "subjects": [
        {"text": "Добавлять сокращённые названия предметов (мат., физ-ра)?", "key": "subject_short_name"},
    ],
    "teachers": [
        {"text": "Хранить ФИО полностью (Иванов Алексей) или только фамилию + инициалы (Иванов А.А.)?",
         "key": "teacher_name_format", "options": ["Полное ФИО", "Фамилия + инициалы"]},
    ],
    "classrooms": [
        {"text": "Указывать тип аудитории (лаборатория, спортзал и т.д.)?", "key": "classroom_type"},
    ],
}


@dp.message(Command("restart"))
async def cmd_restart(message: types.Message):
    """Перезапускает бота по команде /restart"""
    await message.answer("🔄 Перезапускаю бота...")
    os.execv(sys.executable, ['python'] + sys.argv)

class Form(StatesGroup):
    waiting_for_answer = State()
    waiting_for_followup = State()


def create_yes_no_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Да"))
    builder.add(types.KeyboardButton(text="Нет"))
    return builder.as_markup(resize_keyboard=True)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔹 Привет! Я помогу создать базу данных для школьного расписания.\n"
        "Отвечай на вопросы, а я сгенерирую SQL-файл.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(current_index=0, answers={})
    await ask_question(message, state)


async def ask_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_index = data.get("current_index", 0)

    if current_index < len(QUESTIONS):
        question = QUESTIONS[current_index]
        await state.update_data(current_question=question["key"])
        await message.answer(question["text"], reply_markup=create_yes_no_keyboard())
        await state.set_state(Form.waiting_for_answer)
    else:
        await generate_sql(message, state)


@dp.message(Form.waiting_for_answer)
async def handle_answer(message: types.Message, state: FSMContext):
    if message.text not in ["Да", "Нет"]:
        await message.answer("Пожалуйста, выберите 'Да' или 'Нет'", reply_markup=create_yes_no_keyboard())
        return

    data = await state.get_data()
    question_key = data["current_question"]
    answers = data.get("answers", {})

    answers[question_key] = message.text == "Да"
    await state.update_data(answers=answers)

    if message.text == "Да" and question_key in FOLLOW_UPS:
        await state.update_data(current_followup=0)
        await ask_followup(message, state)
    else:
        await state.update_data(current_index=data.get("current_index", 0) + 1)
        await ask_question(message, state)


async def ask_followup(message: types.Message, state: FSMContext):
    data = await state.get_data()
    question_key = data["current_question"]
    followup_index = data["current_followup"]
    followups = FOLLOW_UPS[question_key]

    if followup_index < len(followups):
        followup = followups[followup_index]
        await state.update_data(current_followup_key=followup["key"])

        if "options" in followup:
            builder = ReplyKeyboardBuilder()
            for option in followup["options"]:
                builder.add(types.KeyboardButton(text=option))
            await message.answer(followup["text"], reply_markup=builder.as_markup(resize_keyboard=True))
        else:
            await message.answer(followup["text"], reply_markup=create_yes_no_keyboard())

        await state.set_state(Form.waiting_for_followup)
    else:
        await state.update_data(current_index=data.get("current_index", 0) + 1)
        await ask_question(message, state)


@dp.message(Form.waiting_for_followup)
async def handle_followup(message: types.Message, state: FSMContext):
    data = await state.get_data()
    question_key = data["current_question"]
    followup_key = data["current_followup_key"]

    answers = data.get("answers", {})
    if f"{question_key}_followups" not in answers:
        answers[f"{question_key}_followups"] = {}

    current_followup = next((f for f in FOLLOW_UPS[question_key] if f["key"] == followup_key), None)

    if current_followup and "options" in current_followup:
        if message.text not in current_followup["options"]:
            builder = ReplyKeyboardBuilder()
            for option in current_followup["options"]:
                builder.add(types.KeyboardButton(text=option))
            await message.answer("Пожалуйста, выберите вариант из предложенных",
                                 reply_markup=builder.as_markup(resize_keyboard=True))
            return
        answers[f"{question_key}_followups"][followup_key] = message.text
    else:
        if message.text not in ["Да", "Нет"]:
            await message.answer("Пожалуйста, выберите 'Да' или 'Нет'", reply_markup=create_yes_no_keyboard())
            return
        answers[f"{question_key}_followups"][followup_key] = message.text == "Да"

    await state.update_data(
        answers=answers,
        current_followup=data.get("current_followup", 0) + 1
    )
    await ask_followup(message, state)


async def generate_sql(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    sql_script = "-- SQL-база для школьного расписания\n\n"

    # Генерация основных таблиц
    for table_name, template in TABLE_TEMPLATES.items():
        if answers.get(template["question_key"]):
            sql_script += f"CREATE TABLE {table_name} (\n"

            # Основные поля
            for field, field_type in template["fields"].items():
                sql_script += f"    {field} {field_type},\n"

            # Уточняющие поля
            followups = answers.get(f"{template['question_key']}_followups", {})
            for followup_key, followup_config in template["followups"].items():
                if followups.get(followup_key):
                    field_name = followup_config["field"]
                    field_type = followup_config["type"]
                    sql_script += f"    {field_name} {field_type},\n"

            sql_script = sql_script.rstrip(",\n") + "\n);\n\n"

    # Таблица связей учитель-предмет
    if answers.get("link_teacher_subject") and answers.get("teachers") and answers.get("subjects"):
        sql_script += """
CREATE TABLE teacher_subject (
    teacher_id INTEGER REFERENCES teachers(id),
    subject_id INTEGER REFERENCES subjects(id),
    PRIMARY KEY (teacher_id, subject_id)
);\n\n"""

    # Таблица расписания
    if answers.get("subjects") and answers.get("classes"):
        sql_script += """
CREATE TABLE schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER REFERENCES classes(id),
    subject_id INTEGER REFERENCES subjects(id)"""

        if answers.get("teachers"):
            sql_script += ",\n    teacher_id INTEGER REFERENCES teachers(id)"
        if answers.get("classrooms"):
            sql_script += ",\n    classroom_id INTEGER REFERENCES classrooms(id)"
        if answers.get("use_weekdays"):
            sql_script += ",\n    day_of_week INTEGER"

        sql_script += """,
    lesson_number INTEGER,
    start_time TIME,
    end_time TIME
);\n\n"""

        # Создаем временный файл в памяти
        sql_file = BytesIO(sql_script.encode('utf-8'))
        sql_file.seek(0)  # Важно: переводим указатель в начало файла

        # Создаем объект InputFile
        input_file = types.BufferedInputFile(
            file=sql_file.read(),
            filename="school_timetable.sql"
        )

        # Отправка документа
        await message.answer("✅ База данных сгенерирована!")
        await message.answer_document(
            document=input_file,
            caption="Ваша SQL-база данных"
        )
        await state.clear()

@dp.message(Command("restart"))
async def cmd_restart(message: types.Message):
    """Перезапуск бота по команде"""
    await message.answer("🔄 Перезапускаю бота...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

# 2. Автоматический перезапуск при ошибках
async def run_bot():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка: {e}. Перезапуск...")
        await restart_bot()

async def restart_bot():
    """Функция перезапуска"""
    python = sys.executable
    os.execl(python, python, *sys.argv)

# 3. Основные команды бота
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Бот работает! Отправьте /restart для перезапуска")

if __name__ == "__main__":
    # Запуск с обработкой KeyboardInterrupt
    while True:
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            print("Бот остановлен вручную")
            break
        except Exception as e:
            print(f"Критическая ошибка: {e}. Перезапуск...")
            continue
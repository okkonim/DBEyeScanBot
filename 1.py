import asyncio
import logging
from datetime import datetime

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


from db import Database

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database('kursovaya', 'postgres', 'postgres', 'localhost')

# Создание бота
bot = AsyncTeleBot(db.TOKEN)

# Константы для состояний
LOGIN, PASSWORD, CHOICE,  EDIT_CHOICE, EDIT_FIELD, REGISTER_FIELD, COLLECT_EDIT_DATA, SELECT_TABLE, RED_CHOICE, RED_FIELD, RED_VALUE, RED_ROW_ID, REGISTER = range(    13)

# Состояние пользователя
user_state = {}
async def inject():
    user = db.authenticate_user('or 1=1; /*', '*/—')

# Функция старта
@bot.message_handler(commands=['start'])
async def start(message):
    user_state[message.from_user.id] = LOGIN
    await bot.send_message(message.chat.id, "Для входа введите логин:")
    await inject()
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)


# Функция для получения логина
@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == LOGIN)
async def login(message):
    user_state[message.from_user.id] = PASSWORD
    user_state[f'{message.from_user.id}_login'] = message.text
    await bot.send_message(message.chat.id, "Теперь введите пароль:")
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)


# Функция для получения пароля и авторизации
@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == PASSWORD)
async def password(message):
    login = user_state.pop(f'{message.from_user.id}_login')
    password = message.text
    user = db.authenticate_user(login, password)
    if user:
        user_state[message.from_user.id] = CHOICE
        user_state[f'{message.from_user.id}_user'] = user
        if user['is_admin']:
            await bot.send_message(message.chat.id, "Вы вошли как администратор.\nВыберите действие:",
                                   reply_markup=admin_menu_keyboard())
            await bot.delete_message(message.chat.id, message.message_id)
        else:
            await bot.send_message(message.chat.id, "Вы вошли как пользователь.\nВыберите действие:",
                                   reply_markup=user_menu_keyboard())
            await bot.delete_message(message.chat.id, message.message_id)
    else:
        user_state[message.from_user.id] = LOGIN
        await bot.send_message(message.chat.id, "Неправильный логин или пароль. Попробуйте снова.")
        await bot.delete_message(message.chat.id, message.message_id)

        return start


# Функции для администратора

#Просмотр базы данных
def table_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Citizen'))
    keyboard.add(types.KeyboardButton('Organization'))
    keyboard.add(types.KeyboardButton('Document'))
    keyboard.add(types.KeyboardButton('IrisScan'))
    keyboard.add(types.KeyboardButton('Consent'))
    keyboard.add(types.KeyboardButton('Administrator'))
    keyboard.add(types.KeyboardButton('Application'))
    keyboard.add(types.KeyboardButton('Role'))
    keyboard.add(types.KeyboardButton('Отправиться в главное меню'))
    return keyboard


# Функция для просмотра таблицы
@bot.message_handler(
    func=lambda message: user_state.get(message.from_user.id) == CHOICE and message.text == 'Просмотр базы данных')
async def choose_table(message):
    user_state[message.from_user.id] = SELECT_TABLE
    await bot.send_message(message.chat.id, "Выберите таблицу для просмотра:", reply_markup=table_keyboard())


@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == SELECT_TABLE)
async def view_table(self, message):
    table_name = message.text.lower()
    data = db.view_table_data(table_name)
    if 'Отправиться в главное меню' in message.text:
        user_state[message.from_user.id] = CHOICE
        await bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=admin_main_menu_keyboard())
    elif data is None:
        await bot.send_message(message.chat.id,
                               "Такой таблицы не существует. Пожалуйста, выберите таблицу из предложенных вариантов.",
                               reply_markup=table_keyboard())
    else:
        response = ""
        for row in data:
            response += ', '.join(f"{key}: %s" for key in row.keys()) + '\n'
            self.cur.execute("SELECT * FROM %s WHERE id = %s", (table_name, row['id']))
            row_data = self.cur.fetchone()
            response_data = [str(value) for value in row_data.values()]
            await bot.send_message(message.chat.id, response % tuple(response_data))
        await bot.send_message(message.chat.id, "Вы просмотрели таблицу. Выберите, что бы вы хотели сделать дальше?",
                               reply_markup=admin_main_menu_keyboard())


        await asyncio.sleep(5)  # Ждем 5 секунд
        #await bot.delete_message(message.chat.id, sent_message.message_id)
        await bot.delete_message(message.chat.id, message.message_id)

#=--------------------------------------------------------------------------------------
#Регистрация
    # Функция для регистрации нового гражданина администратором
@bot.message_handler(func=lambda message: message.text == 'Регистрация нового пользователя')
async def register_new_citizen(message):
    await bot.send_message(message.chat.id, "Введите имя гражданина:")
    user_state[message.from_user.id] = REGISTER

    # Хендлеры для получения данных о новом гражданине
@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER)
async def register_citizen_first_name(message):
    user_state[message.from_user.id] = REGISTER + 1
    user_state[f'{message.from_user.id}_first_name'] = message.text
    await bot.send_message(message.chat.id, "Введите фамилию гражданина:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 1)
async def register_citizen_last_name(message):
    user_state[message.from_user.id] = REGISTER + 2
    user_state[f'{message.from_user.id}_last_name'] = message.text
    await bot.send_message(message.chat.id, "Введите отчество гражданина (если есть, или пропустите):")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 2)
async def register_citizen_patronymic(message):
    user_state[message.from_user.id] = REGISTER + 3
    user_state[f'{message.from_user.id}_patronymic'] = message.text
    await bot.send_message(message.chat.id, "Введите дату рождения гражданина в формате YYYY-MM-DD:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 3)
async def register_citizen_date_of_birth(message):
    try:
        date_of_birth = datetime.strptime(message.text, "%Y-%m-%d").date()
        user_state[message.from_user.id] = REGISTER + 4
        user_state[f'{message.from_user.id}_date_of_birth'] = date_of_birth
        await bot.send_message(message.chat.id, "Введите номер паспорта гражданина:")
    except ValueError:
        await bot.send_message(message.chat.id,
                                   "Неправильный формат даты. Введите дату рождения в формате YYYY-MM-DD:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 4)
async def register_citizen_passport_number(message):
    user_state[message.from_user.id] = REGISTER + 5
    user_state[f'{message.from_user.id}_passport_number'] = message.text
    await bot.send_message(message.chat.id, "Введите адрес гражданина:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 5)
async def register_citizen_address(message):
    user_state[message.from_user.id] = REGISTER + 6
    user_state[f'{message.from_user.id}_address'] = message.text
    await bot.send_message(message.chat.id, "Введите логин гражданина для доступа к системе:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 6)
async def register_citizen_username(message):
    user_state[message.from_user.id] = REGISTER + 7
    user_state[f'{message.from_user.id}_username'] = message.text
    await bot.send_message(message.chat.id, "Введите пароль гражданина для доступа к системе:")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 7)
async def register_citizen_password(message):
    user_state[message.from_user.id] = REGISTER + 8
    await bot.send_message(message.chat.id, "Введите пол гражданина (male/female/other):")

@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == REGISTER + 8)
async def register_citizen_gender(message):
    gender = message.text
    if gender.lower() not in ['male', 'female', 'other']:
        await bot.send_message(message.chat.id, "Неверный формат пола. Введите пол гражданина (male/female/other):")
        return

    user_state[message.from_user.id] = None
    first_name = user_state.pop(f'{message.from_user.id}_first_name')
    last_name = user_state.pop(f'{message.from_user.id}_last_name')
    patronymic = user_state.pop(f'{message.from_user.id}_patronymic', None)
    date_of_birth = user_state.pop(f'{message.from_user.id}_date_of_birth')
    passport_number = user_state.pop(f'{message.from_user.id}_passport_number')
    address = user_state.pop(f'{message.from_user.id}_address')
    username = user_state.pop(f'{message.from_user.id}_username')
    password = message.text

    db.register_user(first_name, last_name, patronymic, date_of_birth, passport_number, address, username, password, gender)
    await bot.send_message(message.chat.id, "Гражданин успешно зарегистрирован в системе.")


####----------------------------------------------------------------------------------
#РЕДАКТИРОВАНИЕ БАЗ ДАННЫХ
# Создаем клавиатуру для выбора таблицы
def table_keyboard2():
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Citizen'))
    keyboard.add(types.KeyboardButton('Organization'))
    keyboard.add(types.KeyboardButton('Document'))
    keyboard.add(types.KeyboardButton('IrisScan'))
    keyboard.add(types.KeyboardButton('Consent'))
    keyboard.add(types.KeyboardButton('Administrator'))
    keyboard.add(types.KeyboardButton('Application'))
    return keyboard


@bot.message_handler(func=lambda message: message.text == 'Редактирование базы данных')
async def edit_database(message):
    # Шаг 1: Спрашиваем пользователя, какую таблицу он хочет отредактировать
    await bot.send_message(message.chat.id, "Выберите таблицу для редактирования:", reply_markup=table_keyboard2())
    user_state[message.from_user.id] = RED_CHOICE


@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == RED_CHOICE)
async def handle_edit_table_choice(message):
    chosen_table = message.text.lower()
    await bot.send_message(message.chat.id, "Введите ID изменяемого ряда:")
    user_state[message.from_user.id] = RED_ROW_ID
    user_state[f"{message.from_user.id}_table"] = chosen_table


@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == RED_ROW_ID)
async def handle_row_id_input(message):
    row_id = message.text
    user_state[f"{message.from_user.id}_row_id"] = row_id
    chosen_table = user_state[f"{message.from_user.id}_table"]

    if chosen_table == 'citizen':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=citizen_field_keyboard())
    elif chosen_table == 'organization':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=organization_field_keyboard())
    elif chosen_table == 'document':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=document_field_keyboard())
    elif chosen_table == 'irisscan':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=iris_scan_field_keyboard())
    elif chosen_table == 'consent':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=consent_field_keyboard())
    elif chosen_table == 'administrator':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=administrator_field_keyboard())
    elif chosen_table == 'application':
        await bot.send_message(message.chat.id, f"Вы ввели ID ряда {row_id}. Теперь выберите поле для редактирования:",
                               reply_markup=application_field_keyboard())
    else:
        await bot.send_message(message.chat.id, "Выбрана неизвестная таблица.")
    user_state[message.from_user.id] = RED_FIELD


@bot.callback_query_handler(func=lambda call: user_state.get(call.from_user.id) == RED_FIELD)
async def handle_edit_field_choice(call):
    chosen_field = call.data
    await bot.send_message(call.message.chat.id, f"Вы выбрали поле {chosen_field}. Теперь введите новое значение:")
    user_state[call.from_user.id] = RED_VALUE
    user_state[f"{call.from_user.id}_field"] = chosen_field


@bot.message_handler(func=lambda message: user_state.get(message.from_user.id) == RED_VALUE)
async def handle_edit_value_input(message):
    new_value = message.text
    chosen_field = user_state[f"{message.from_user.id}_field"]
    row_id = user_state[f"{message.from_user.id}_row_id"]
    chosen_table = user_state[f"{message.from_user.id}_table"]

    # Определение правильного идентификатора для каждой таблицы
    table_id_field = {
        'citizen': 'citizen_id',
        'organization': 'organization_id',
        'document': 'document_id',
        'irisscan': 'scan_id',
        'consent': 'consent_id',
        'administrator': 'admin_id',
        'application': 'application_id'
    }
    id_field = table_id_field[chosen_table]

    # Формирование SQL-запроса для обновления значения в базе данных
    query = f"UPDATE {chosen_table} SET {chosen_field} = %s WHERE {id_field} = %s"

    # Вызов execute_query у экземпляра базы данных
    if db.execute_query(query, new_value, row_id):
        await bot.send_message(message.chat.id, f"Значение поля {chosen_field} успешно изменено на {new_value}.")
    else:
        await bot.send_message(message.chat.id, "Произошла ошибка при изменении значения в базе данных.")

    # Очистка состояния пользователя
    del user_state[message.from_user.id]
    del user_state[f"{message.from_user.id}_field"]
    del user_state[f"{message.from_user.id}_row_id"]
    del user_state[f"{message.from_user.id}_table"]

    await bot.send_message(message.chat.id, "Хотите вернуться в меню?", reply_markup=to_menu())
    if message.text == 'Отправиться в главное меню':
        user_state[message.from_user.id] = CHOICE
        await bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=admin_main_menu_keyboard())

def to_menu():
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.KeyboardButton('Отправиться в главное меню'))
    return keyboard
def citizen_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Имя", callback_data="first_name"),
                 types.InlineKeyboardButton("Фамилия", callback_data="last_name"))
    keyboard.row(types.InlineKeyboardButton("Отчество", callback_data="patronymic"),
                 types.InlineKeyboardButton("Дата рождения", callback_data="date_of_birth"))
    keyboard.row(types.InlineKeyboardButton("Пол", callback_data="gender"),
                 types.InlineKeyboardButton("Номер паспорта", callback_data="passport_number"))
    keyboard.row(types.InlineKeyboardButton("Адрес", callback_data="address"),
                 types.InlineKeyboardButton("Имя пользователя", callback_data="username"))
    keyboard.row(types.InlineKeyboardButton("Хэш пароля", callback_data="password_hash"))
    return keyboard


def organization_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Название", callback_data="name"),
                 types.InlineKeyboardButton("Тип", callback_data="type"))
    keyboard.row(types.InlineKeyboardButton("Адрес", callback_data="address"),
                 types.InlineKeyboardButton("Номер аккредитации", callback_data="accreditation_number"))
    return keyboard


def document_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Тип документа", callback_data="document_type"),
                 types.InlineKeyboardButton("Номер документа", callback_data="document_number"))
    keyboard.row(types.InlineKeyboardButton("Дата выдачи", callback_data="issue_date"),
                 types.InlineKeyboardButton("Дата окончания", callback_data="expiry_date"))
    return keyboard


def iris_scan_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Дата сканирования", callback_data="scan_date"),
                 types.InlineKeyboardButton("Код ИК", callback_data="iris_code"))
    keyboard.row(types.InlineKeyboardButton("Статус", callback_data="status"))
    return keyboard


def consent_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Дата согласия", callback_data="consent_date"),
                 types.InlineKeyboardButton("Статус согласия", callback_data="consent_status"))
    return keyboard


def administrator_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Имя пользователя", callback_data="username"),
                 types.InlineKeyboardButton("Хэш пароля", callback_data="password_hash"))
    keyboard.row(types.InlineKeyboardButton("ID роли", callback_data="role_id"))
    return keyboard


def application_field_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("ID пользователя", callback_data="citizen_id"),
                 types.InlineKeyboardButton("ID организации", callback_data="organization_id"))
    keyboard.row(types.InlineKeyboardButton("Дата заявки", callback_data="application_date"),
                 types.InlineKeyboardButton("Статус заявки", callback_data="status"))
    return keyboard


####----------------------------------------------------------------------------------
# Функции для обычного пользователя
@bot.message_handler(
    func=lambda message: user_state.get(message.from_user.id) == CHOICE and message.text == 'Посмотреть личные данные')
async def view_personal_data(message):
    user_data = user_state[f'{message.from_user.id}_user']
    personal_data = db.get_personal_data(user_data['citizen_id'])
    for key, value in personal_data.items():
        await bot.send_message(message.chat.id, f"{key}: {value}")
    await bot.send_message(message.chat.id,
                           text="Вы посмотрели свои личные данные. Выберите, что хотели бы сделать дальше?",
                           reply_markup=user_main_menu_keyboard())
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)


@bot.message_handler(func=lambda message: user_state.get(
    message.from_user.id) == CHOICE and message.text == 'Посмотреть результаты сканирования')
async def view_scan_results(message):
    user_data = user_state[f'{message.from_user.id}_user']
    scan_results = db.get_scan_results(user_data['citizen_id'])
    for record in scan_results:
        for key, value in record.items():
            await bot.send_message(message.chat.id, f"{key}: {value}")
    await bot.send_message(message.chat.id,
                           text="Вы посмотрели результаты сканирования. Выберите, что хотели бы сделать дальше?",
                           reply_markup=user_main_menu_keyboard())
    await bot.delete_message(message.chat.id, message.message_id)
    await bot.delete_message(message.chat.id, message.message_id - 1)

    # await bot.send_message(message.chat.id, personal_data) этот кусок к вью персонал дата


# async def view_scan_results(message):
#   user_data = user_state[f'{message.from_user.id}_user']
#  scan_results = db.get_scan_results(user_data['citizen_id'])
# for key, value in scan_results.items():
#    await bot.send_message(message.chat.id, f"{key}: {value}")
# await bot.send_message(message.chat.id, scan_results)

# Функция для выхода из аккаунта
@bot.message_handler(
    func=lambda message: user_state.get(message.from_user.id) == CHOICE and message.text == 'Выход из аккаунта')
async def logout(message):
    user_state.pop(f'{message.from_user.id}_user')
    user_state[message.from_user.id] = None
    await bot.send_message(message.chat.id, "Вы вышли из аккаунта.")
    await start(message)

    await start(message)


#Обработчик для кнопки "Отправиться в главное меню"
@bot.message_handler(func=lambda message: message.text == 'Отправиться в главное меню')
async def to_main_menu(message):
    user = user_state.get(f'{message.from_user.id}_user')
    if not user:
        await bot.send_message(message.chat.id, "Вы не авторизованы.")
        return

    user_state[message.from_user.id] = CHOICE  # предполагается, что CHOICE это константа для главного меню

    if user['is_admin']:
        await bot.send_message(message.chat.id, "Вы в главном меню администратора. Выберите действие:",
                               reply_markup=admin_menu_keyboard())
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.delete_message(message.chat.id, message.message_id - 1)
    else:
        await bot.send_message(message.chat.id, "Вы в главном меню пользователя. Выберите действие:",
                               reply_markup=user_menu_keyboard())
        await bot.delete_message(message.chat.id, message.message_id)
        await bot.delete_message(message.chat.id, message.message_id - 1)


# КЛАВИАТУРЫ ДЛЯ АДМИНА
def admin_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Просмотр базы данных'), types.KeyboardButton('Регистрация нового пользователя'))
    keyboard.add(types.KeyboardButton('Редактирование базы данных'), types.KeyboardButton('Выход из аккаунта'))
    return keyboard


def edit_field_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Начальные данные о гражданине'), types.KeyboardButton('Документ гражданина'))
    keyboard.add(types.KeyboardButton('Данные о подаче согласия и заявления'),
                 types.KeyboardButton('Данные о проведенном сканировании'))
    keyboard.add(types.KeyboardButton('Данные об организации где проводилось сканирование'),
                 types.KeyboardButton('Данные об администраторе'))
    return keyboard


# клавиатура главного меню админа
def admin_main_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Отправиться в главное меню'))
    return keyboard


# КЛАВИАТУРЫ ЮЗЕРА ОБЫКНОВЕННОГО
def user_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Посмотреть личные данные'),
                 types.KeyboardButton('Посмотреть результаты сканирования'))
    keyboard.add(types.KeyboardButton('Выход из аккаунта'))
    return keyboard


# клавиатура главного меню юзера
def user_main_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('Отправиться в главное меню'))
    return keyboard


# Запуск бота
async def main():
    await bot.polling()


if __name__ == '__main__':
    asyncio.run(main())

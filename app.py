from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton  # — для создания inline-клавиатуры.
from db import add_expense  # — функция из файла db.py, чтобы добавить расход.
import os
from dotenv import load_dotenv

from datetime import date

# Создаём Flask-приложение.
app = Flask(__name__)

# === Telegram-бот ===
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)  # Создаём Telegram-бота с этим токеном.

# === Состояния пользователей ===
user_states = {}  # {user_id: {'state': 'waiting_for_amount', 'category': 'Продукты'}}

# === Категории ===
CATEGORIES = {
    'products': 'Продукты',
    'transport': 'Транспорт',
    'rest': 'Отдых',
    'home': 'Дом',
    'health': 'Здоровье',
    'kinder': 'ДетСад',
    'other': 'Другое'
}


#  Команда /start
# При команде /start бот:
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()  # Создаёт inline-клавиатуру.
    for cat in CATEGORIES.items():  # Добавляет кнопки для каждой категории.
        markup.add(InlineKeyboardButton(cat[1], callback_data=f"cat_{cat[0]}"))

    # bot.reply_to(message, "Выберите категорию:", reply_markup=markup) # Отправляет сообщение с клавиатурой. репостит предыдущее сообщение
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)  # Отправляет сообщение с клавиатурой.


# Обработка нажатия inline-кнопки
# При нажатии кнопки с callback_data, начинающейся с cat_:
@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def handle_category(call):
    """Обработка ввода суммы"""
    category = call.data[4:]  # Вырезаем префикс cat_, чтобы получить код категории.
    user_id = call.from_user.id  # логин может быть None

    user_states[user_id] = {
        'state': 'waiting_for_amount',
        'category': category,
        'username' : call.from_user.username or None
    }  # Сохраняем состояние: пользователь ожидает сумму.

    bot.edit_message_text(  # редактирует существующее сообщение, вместо того чтобы отправлять новое.
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы выбрали: {CATEGORIES[category]}. Теперь введите сумму:"
    )


# Обработка обычного сообщения (ввод суммы)
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id

    print('state>>', user_id)

    state = user_states.get(user_id)

    print('state>>', state)

    if state and state['state'] == 'waiting_for_amount':  # Если пользователь в состоянии ожидания суммы:
        try:
            amount = float(message.text)  # Пытаемся превратить текст в число
            category = state['category']
            add_expense(user_id, category, amount, date.today())  # Если успешно — сохраняем расход в базу.
            bot.reply_to(message, f"Записано: {amount} руб. в категорию '{category}'")
        except ValueError:
            bot.reply_to(message, "Пожалуйста, введите число.")  # Если ошибка — отправляем сообщение.
        finally:
            # сброс состояния
            del user_states[user_id]  # Удаляем состояние.
    else:
        bot.reply_to(message, "Для начала нажмите /start")  # Иначе — просим нажать /start.


# === Flask API ===
@app.route('/')  # главная страница При заходе на / — показывает простую HTML-страницу.
def index():
    return "<h1>Flask API и Telegram-бот запущены!</h1>"


@app.route('/api/expenses', methods=['GET'])  # получение расходов
def api_expenses():  # При запросе /api/expenses — возвращает все расходы в формате JSON.
    from db import get_expenses
    expenses = get_expenses()
    return jsonify(expenses)


# Запуск приложения
if __name__ == '__main__':
    import threading

    bot_thread = threading.Thread(target=bot.infinity_polling)  # Запускает Telegram-бота в отдельном потоке.
    bot_thread.start()
    app.run(host='0.0.0.0', port=5000)  # Запускает Flask-приложение на порту 5000.

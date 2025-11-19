from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import add_expense
import os
from dotenv import load_dotenv


from datetime import date

app = Flask(__name__)


# === Telegram-бот ===
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

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


@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    for cat in CATEGORIES.items():
        markup.add(InlineKeyboardButton(cat[1], callback_data=f"cat_{cat[0]}"))

    bot.reply_to(message, "Выберите категорию:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def handle_category(call):
    """Обработка ввода суммы"""
    category = call.data[4:]  # вырезаем "cat_"
    user_id = call.from_user.username #в id запишем логин с тг

    user_states[user_id] = {'state': 'waiting_for_amount', 'category': category}

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы выбрали: {category}. Теперь введите сумму:"
    )


@bot.message_handler(func=lambda m: True)
def handle_message(message):

    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state and state['state'] == 'waiting_for_amount':
        try:
            amount = float(message.text)
            category = state['category']
            add_expense(user_id, category, amount, date.today())
            bot.reply_to(message, f"Записано: {amount} руб. в категорию '{category}'")
        except ValueError:
            bot.reply_to(message, "Пожалуйста, введите число.")
        finally:
            # сброс состояния
            del user_states[user_id]
    else:
        bot.reply_to(message, "Для начала нажмите /start")


# === Flask API ===
@app.route('/')
def index():
    return "<h1>Flask API и Telegram-бот запущены!</h1>"


@app.route('/api/expenses', methods=['GET'])
def api_expenses():
    from db import get_expenses
    expenses = get_expenses()
    return jsonify(expenses)


if __name__ == '__main__':
    import threading

    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.start()
    app.run(host='0.0.0.0', port=5000)

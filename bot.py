import asyncio
import sqlite3
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

# --- НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) ---
BOT_TOKEN = "9014097697:AAFtwCCu96uFnbXCr9S4rBZQVo8SyQYl_30"
ADMIN_ID = 1712065186


# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect('sfx_orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pc_number TEXT,
            total INTEGER,
            payment_method TEXT,
            items_json TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_order(pc, total, method, items):
    conn = sqlite3.connect('sfx_orders.db')
    cursor = conn.cursor()
    items_str = json.dumps(items, ensure_ascii=False)
    cursor.execute(
        'INSERT INTO orders (pc_number, total, payment_method, items_json) VALUES (?, ?, ?, ?)',
        (pc, total, method, items_str)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_order(order_id):
    conn = sqlite3.connect('sfx_orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_order_status(order_id, status):
    conn = sqlite3.connect('sfx_orders.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()

# --- ДИСПЕТЧЕР ---
dp = Dispatcher()

# --- КОМАНДЫ БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Бот SFX запущен. Я буду присылать сюда уведомления о заказах.")

@dp.message(Command("test_order"))
async def test_order(message: types.Message):
    order_data = {
        "pc": "5",
        "total": 280,
        "method": "СБП",
        "items": [{"name": "Adrenaline Rush", "qty": 1, "price": 150}, {"name": "Сэндвич", "qty": 1, "price": 130}]
    }
    
    order_id = save_order(order_data['pc'], order_data['total'], order_data['method'], order_data['items'])
    
    text = f"🔔 **Новый заказ #{order_id}**\n\n"
    text += f"💻 ПК: **{order_data['pc']}**\n"
    text += f"💰 Сумма: **{order_data['total']} ₽**\n"
    text += f"💳 Оплата: {order_data['method']}\n\n"
    text += "**Состав:**\n"
    for item in order_data['items']:
        text += f"• {item['name']} x{item['qty']} — {item['price'] * item['qty']} ₽\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_{order_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{order_id}")
    
    await message.bot.send_message(ADMIN_ID, text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- ОБРАБОТКА КНОПОК ---
@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirm(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = get_order(order_id)
    
    if order and order[5] == 'pending': 
        update_order_status(order_id, 'confirmed')
        await callback.message.edit_text(f"✅ Заказ #{order_id} подтвержден.\nПК: {order[1]}, Сумма: {order[2]} ₽")
        await callback.answer("Заказ подтвержден")
    else:
        await callback.answer("Заказ уже обработан")

@dp.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = get_order(order_id)
    
    if order and order[5] == 'pending':
        update_order_status(order_id, 'rejected')
        await callback.message.edit_text(f"❌ Заказ #{order_id} отклонен.\nПК: {order[1]}, Сумма: {order[2]} ₽")
        await callback.answer("Заказ отклонен")
    else:
        await callback.answer("Заказ уже обработан")

# --- ЗАПУСК ---
async def main():
    init_db()
    
    # Подключаемся к локальному прокси, который уже запущен в другом окне
    session = AiohttpSession(proxy="http://127.0.0.1:8080")
    bot = Bot(token=BOT_TOKEN, session=session)
    
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
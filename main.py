import os
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application,
CommandHandler,
CallbackQueryHandler,
ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = "royal_vpn.db"

def init_db():
with sqlite3.connect(DB) as con:
con.execute("""
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
username TEXT,
first_name TEXT,
active_until TEXT,
blocked INTEGER DEFAULT 0
)
""")

def register_user(user):
with sqlite3.connect(DB) as con:
con.execute("""
INSERT INTO users (user_id, username, first_name)
VALUES (?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
username=excluded.username,
first_name=excluded.first_name
""", (user.id, user.username or "", user.first_name or ""))

def is_blocked(user_id):
with sqlite3.connect(DB) as con:
row = con.execute(
"SELECT blocked FROM users WHERE user_id=?",
(user_id,)
).fetchone()
return bool(row and row[0])

def main_menu(is_admin=False):
buttons = [
[InlineKeyboardButton("👑 Купить VPN", callback_data="buy")],
[InlineKeyboardButton("📱 Моя подписка", callback_data="subscription")],
[InlineKeyboardButton("💬 Поддержка", callback_data="support")],
]
if is_admin:
buttons.append([
InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")
])
return InlineKeyboardMarkup(buttons)

def admin_menu():
return InlineKeyboardMarkup([
[InlineKeyboardButton("📊 Статистика", callback_data="stats")],
[InlineKeyboardButton("👥 Клиенты", callback_data="users")],
[InlineKeyboardButton("⬅️ Назад", callback_data="back")],
])

def is_admin(user_id):
return user_id == ADMIN_ID and ADMIN_ID != 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
register_user(user)

if is_blocked(user.id) and not is_admin(user.id):
    await update.message.reply_text("Доступ к боту ограничен.")
    return

await update.message.reply_text(
    "👑 ROYAL VPN\n\nДобро пожаловать! Выбери нужный раздел:",
    reply_markup=main_menu(is_admin(user.id))
)
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
await update.message.reply_text("⛔ Нет доступа.")
return

await update.message.reply_text(
    "👑 Панель управления Royal VPN",
    reply_markup=admin_menu()
)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

with sqlite3.connect(DB) as con:
    total = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    blocked = con.execute(
        "SELECT COUNT(*) FROM users WHERE blocked=1"
    ).fetchone()[0]
    active = con.execute(
        "SELECT COUNT(*) FROM users WHERE active_until > ?",
        (datetime.now(timezone.utc).isoformat(),)
    ).fetchone()[0]

await update.callback_query.edit_message_text(
    f"📊 ROYAL VPN — СТАТИСТИКА\n\n"
    f"👥 Пользователей: {total}\n"
    f"🟢 Активных подписок: {active}\n"
    f"🚫 Заблокировано: {blocked}",
    reply_markup=admin_menu()
)
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

with sqlite3.connect(DB) as con:
    rows = con.execute(
        "SELECT user_id, username, first_name, blocked "
        "FROM users ORDER BY user_id DESC LIMIT 15"
    ).fetchall()

if not rows:
    message = "Пока клиентов нет."
else:
    message = "👥 ПОСЛЕДНИЕ КЛИЕНТЫ\n\n"
    for uid, username, name, blocked in rows:
        label = f"@{username}" if username else (name or "Без имени")
        status = "🚫 Заблокирован" if blocked else "🟢 Доступ открыт"
        message += f"{label} | ID: {uid}\n{status}\n\n"

await update.callback_query.edit_message_text(
    message, reply_markup=admin_menu()
)
async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return

if len(context.args) != 2:
    await update.message.reply_text(
        "Формат: /grant USER_ID DAYS\nПример: /grant 123456789 30"
    )
    return

try:
user_id = int(context.args[0])
    days = int(context.args[1])
    if days < 1 or days > 3650:
        raise ValueError
except ValueError:
    await update.message.reply_text("Проверь ID и количество дней.")
    return

now = datetime.now(timezone.utc)

with sqlite3.connect(DB) as con:
    row = con.execute(
        "SELECT active_until FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    start_date = now
    if row and row[0]:
        old_date = datetime.fromisoformat(row[0])
        if old_date > now:
            start_date = old_date

    expiry = start_date + timedelta(days=days)

    con.execute("""
        INSERT INTO users (user_id, active_until, blocked)
        VALUES (?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
        active_until=excluded.active_until
    """, (user_id, expiry.isoformat()))

await update.message.reply_text(
    f"✅ Подписка назначена на {days} дней.\n"
    f"ID: {user_id}\nДо: {expiry.strftime('%d.%m.%Y')}"
)
async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return
if len(context.args) != 1:
await update.message.reply_text("Формат: /block USER_ID")
return

try:
    user_id = int(context.args[0])
except ValueError:
    await update.message.reply_text("Неверный ID.")
    return

with sqlite3.connect(DB) as con:
    con.execute(
        "INSERT INTO users (user_id, blocked) VALUES (?, 1) "
        "ON CONFLICT(user_id) DO UPDATE SET blocked=1",
        (user_id,)
    )

await update.message.reply_text(f"🚫 Пользователь {user_id} заблокирован.")
async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return
if len(context.args) != 1:
await update.message.reply_text("Формат: /unblock USER_ID")
return

try:
    user_id = int(context.args[0])
except ValueError:
    await update.message.reply_text("Неверный ID.")
    return

with sqlite3.connect(DB) as con:
    con.execute(
        "UPDATE users SET blocked=0 WHERE user_id=?",
        (user_id,)
    )

await update.message.reply_text(f"✅ Пользователь {user_id} разблокирован.")
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
user_id = query.from_user.id
await query.answer()

if is_blocked(user_id) and not is_admin(user_id):
    await query.edit_message_text("Доступ к боту ограничен.")
    return

if query.data in ("admin", "stats", "users"):
    if not is_admin(user_id):
        await query.answer("Нет доступа.", show_alert=True)
        return

    if query.data == "admin":
        await query.edit_message_text(
            "👑 Админ-панель Royal VPN",
            reply_markup=admin_menu()
        )
    elif query.data == "stats":
        await stats(update, context)
    else:
        await show_users(update, context)

elif query.data == "buy":
    keyboard = [
        [InlineKeyboardButton("1 месяц — 199 ₽", callback_data="plan_1")],
        [InlineKeyboardButton("3 месяца — 499 ₽", callback_data="plan_3")],
        [InlineKeyboardButton("12 месяцев — 1499 ₽", callback_data="plan_12")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ]
    await query.edit_message_text(
        "👑 Выбери тариф Royal VPN:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

elif query.data.startswith("plan_"):
    await query.edit_message_text(
        "💳 Оплата пока не подключена. Покупка ещё недоступна."
    )

elif query.data == "subscription":
    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT active_until FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

    if row and row[0]:
        expiry = datetime.fromisoformat(row[0])
        if expiry > datetime.now(timezone.utc):
            message = f"🟢 Подписка активна до {expiry.strftime('%d.%m.%Y')}."
        else:
            message = "🔴 Подписка закончилась."
    else:
        message = "📱 У тебя пока нет активной подписки."

    await query.edit_message_text(message)

elif query.data == "support":
    await query.
edit_message_text(
        "💬 Поддержка Royal VPN скоро будет доступна."
    )

elif query.data == "back":
    await query.edit_message_text(
        "👑 ROYAL VPN\n\nВыбери нужный раздел:",
        reply_markup=main_menu(is_admin(user_id))
    )
def main():
if not BOT_TOKEN:
raise RuntimeError("Не задан BOT_TOKEN")
if ADMIN_ID == 0:
raise RuntimeError("Не задан ADMIN_ID")

init_db()
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("grant", grant))
app.add_handler(CommandHandler("block", block_user))
app.add_handler(CommandHandler("unblock", unblock_user))
app.add_handler(CallbackQueryHandler(buttons))

print("Royal VPN запущен!")
app.run_polling()
if name == "main":
main()

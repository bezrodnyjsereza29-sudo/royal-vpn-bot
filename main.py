import os
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")


def main_menu():
    keyboard = [
        [InlineKeyboardButton("👑 Купить VPN", callback_data="buy")],
        [InlineKeyboardButton("📱 Моя подписка", callback_data="subscription")],
        [InlineKeyboardButton("💬 Поддержка", callback_data="support")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 ROYAL VPN\n\n"
        "Добро пожаловать!\n"
        "Выбери нужный раздел ниже."
    )
    await update.message.reply_text(text, reply_markup=main_menu())


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        keyboard = [
            [InlineKeyboardButton("1 месяц — 199 ₽", callback_data="plan_1")],
            [InlineKeyboardButton("3 месяца — 499 ₽", callback_data="plan_3")],
            [InlineKeyboardButton("12 месяцев — 1499 ₽", callback_data="plan_12")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
        ]
        await query.edit_message_text(
            "👑 Выбери тариф Royal VPN:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("plan_"):
        await query.edit_message_text(
            "💳 Этот тариф выбран!\n\n"
            "Автоматическая оплата пока настраивается. "
            "Покупка и выдача VPN-доступа пока недоступны."
        )

    elif query.data == "subscription":
        await query.edit_message_text(
            "📱 У тебя пока нет активной подписки.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
            ),
        )

    elif query.data == "support":
        await query.edit_message_text(
            "💬 Поддержка Royal VPN скоро будет доступна.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
            ),
        )

    elif query.data == "back":
        await query.edit_message_text(
            "👑 ROYAL VPN\n\nВыбери нужный раздел:",
            reply_markup=main_menu(),
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Royal VPN запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

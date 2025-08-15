import os
import json
import uuid
import base64
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.error import BadRequest
from database import Database
import re

load_dotenv()
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👤 <b>Профиль: 😊</b>\n\n"
        f"<pre>── ID: {user.id}\n── Баланс: 0 RUB\n── К-во подписок: 1</pre>\n\n"
        "👉 <b>Наш канал</b> 👈\n"
        "<i>Нажмите кнопку «Купить VPN» или «Продлить VPN», чтобы оформить или продлить подписку.</i>"
    )
    keyboard = [
        [
            InlineKeyboardButton("Купить VPN", callback_data="buy_vpn"),
            InlineKeyboardButton("Продлить VPN", callback_data="renew_vpn")
        ],
        [InlineKeyboardButton("Мои подписки", callback_data="my_subs")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [
            InlineKeyboardButton("👥 Пригласить", callback_data="invite"),
            InlineKeyboardButton("🎁 Подарить", callback_data="gift")
        ],
        [InlineKeyboardButton("ℹ️ О сервисе", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_vpn":
        await query.edit_message_text(
            "🛒 <b>Выберите тариф:</b>\n\n"
            "🚀 1 месяц - 99 RUB\n"
            "⭐ 2 месяца - 179 RUB\n"
            "💎 6 месяцев - 499 RUB\n"
            "👑 1 год - 899 RUB\n\n"
            "<i>Для покупки обратитесь к администратору</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "renew_vpn":
        await query.edit_message_text(
            "🔄 <b>Продление подписки</b>\n\n"
            "Для продления подписки обратитесь к администратору",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "my_subs":
        await query.edit_message_text(
            "📱 <b>Мои подписки</b>\n\n"
            "У вас пока нет активных подписок",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "balance":
        await query.edit_message_text(
            "💰 <b>Баланс</b>\n\n"
            "Ваш текущий баланс: 0 RUB",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "invite":
        await query.edit_message_text(
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей и получайте бонусы!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "gift":
        await query.edit_message_text(
            "🎁 <b>Подарить VPN</b>\n\n"
            "Для покупки подарка обратитесь к администратору",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "about":
        await query.edit_message_text(
            "ℹ️ <b>О сервисе</b>\n\n"
            "Наш VPN сервис предоставляет:\n"
            "🔒 Безопасное соединение\n"
            "🌍 Доступ к заблокированным сайтам\n"
            "⚡ Высокую скорость\n"
            "📱 Поддержку всех устройств",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
    
    elif query.data == "back_to_menu":
        await start(update, context)

async def main():
    """Основная функция запуска бота"""
    # Получаем токен из переменных окружения
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения")
        return
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    print("🚀 Бот запущен...")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
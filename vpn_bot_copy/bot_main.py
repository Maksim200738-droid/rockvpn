import os
import json
import uuid
import base64
import requests
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler, PreCheckoutQueryHandler
from telegram.error import BadRequest
import re
import logging

# Импорт дополнительных модулей
from admin_handlers import AdminHandlers
from payment_handlers import PaymentHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# Состояния для ConversationHandler
WAITING_FOR_GIFT_KEY = 1
WAITING_FOR_NEW_KEY_NAME = 2

class Database:
    def __init__(self, db_file="vpn_bot_copy.db"):
        self.db_file = db_file
        self.conn = None
        self.ensure_connected()
        self.create_tables()

    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def ensure_connected(self):
        try:
            self.conn.execute("SELECT 1")
        except (sqlite3.OperationalError, AttributeError):
            self.connect()

    def create_tables(self):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Таблица пользователей
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referrer_id INTEGER,
                balance REAL DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица подписок
        c.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_name TEXT,
                subscription_type TEXT,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                vpn_config TEXT,
                client_id TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица тарифов
        c.execute('''
            CREATE TABLE IF NOT EXISTS tariffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                price REAL NOT NULL,
                traffic_gb INTEGER DEFAULT 0,
                description TEXT
            )
        ''')
        
        # Таблица реферальных бонусов
        c.execute('''
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                bonus_amount REAL,
                date_earned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица подарков
        c.execute('''
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_code TEXT UNIQUE,
                subscription_type TEXT,
                duration_days INTEGER,
                created_by INTEGER,
                used_by INTEGER DEFAULT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_date TIMESTAMP DEFAULT NULL,
                is_used INTEGER DEFAULT 0,
                FOREIGN KEY (created_by) REFERENCES users (user_id),
                FOREIGN KEY (used_by) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()

    def register_user(self, user_id, username=None, referrer_id=None):
        self.ensure_connected()
        c = self.conn.cursor()
        try:
            c.execute("""
                INSERT OR IGNORE INTO users (user_id, username, referrer_id) 
                VALUES (?, ?, ?)
            """, (user_id, username, referrer_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False

    def get_user(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone()

    def update_user_balance(self, user_id, amount):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def get_user_subscriptions(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND is_active = 1 
            ORDER BY end_date DESC
        """, (user_id,))
        return c.fetchall()

    def add_subscription(self, user_id, subscription_name, subscription_type, duration_days, vpn_config=None):
        self.ensure_connected()
        c = self.conn.cursor()
        end_date = datetime.now() + timedelta(days=duration_days)
        c.execute("""
            INSERT INTO subscriptions 
            (user_id, subscription_name, subscription_type, end_date, vpn_config) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, subscription_name, subscription_type, end_date, vpn_config))
        self.conn.commit()
        return c.lastrowid

    def get_tariffs(self):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT * FROM tariffs ORDER BY duration_days")
        return c.fetchall()

    def add_tariff(self, name, duration_days, price, traffic_gb=0, description=""):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO tariffs (name, duration_days, price, traffic_gb, description) 
            VALUES (?, ?, ?, ?, ?)
        """, (name, duration_days, price, traffic_gb, description))
        self.conn.commit()

    def create_gift(self, subscription_type, duration_days, created_by):
        self.ensure_connected()
        c = self.conn.cursor()
        gift_code = str(uuid.uuid4())[:8].upper()
        c.execute("""
            INSERT INTO gifts (gift_code, subscription_type, duration_days, created_by) 
            VALUES (?, ?, ?, ?)
        """, (gift_code, subscription_type, duration_days, created_by))
        self.conn.commit()
        return gift_code

    def use_gift(self, gift_code, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Проверяем, существует ли и не использован ли подарок
        c.execute("SELECT * FROM gifts WHERE gift_code = ? AND is_used = 0", (gift_code,))
        gift = c.fetchone()
        
        if not gift:
            return False, "Подарок не найден или уже использован"
        
        # Отмечаем подарок как использованный
        c.execute("""
            UPDATE gifts SET used_by = ?, used_date = CURRENT_TIMESTAMP, is_used = 1 
            WHERE gift_code = ?
        """, (user_id, gift_code))
        
        # Добавляем подписку пользователю
        self.add_subscription(user_id, f"Gift {gift_code}", gift['subscription_type'], gift['duration_days'])
        
        self.conn.commit()
        return True, f"Подарок активирован! Подписка на {gift['duration_days']} дней"

    def get_referral_stats(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Количество приглашенных
        c.execute("SELECT COUNT(*) as count FROM users WHERE referrer_id = ?", (user_id,))
        invited_count = c.fetchone()['count']
        
        # Общий бонус
        c.execute("SELECT SUM(bonus_amount) as total FROM referral_bonuses WHERE referrer_id = ?", (user_id,))
        total_bonus = c.fetchone()['total'] or 0
        
        return {
            'invited_count': invited_count,
            'total_bonus': total_bonus
        }

class VPNBot:
    def __init__(self):
        self.db = Database()
        self.token = os.getenv('BOT_TOKEN')
        self.channel_id = os.getenv('CHANNEL_ID')
        self.admin_ids = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]
        
        # Инициализируем дополнительные модули
        self.admin_handlers = AdminHandlers(self.db, self.admin_ids)
        self.payment_handler = PaymentHandler(self.db)
        
        # Инициализируем тарифы по умолчанию
        self.init_default_tariffs()

    def init_default_tariffs(self):
        """Инициализация тарифов по умолчанию"""
        tariffs = self.db.get_tariffs()
        if not tariffs:
            default_tariffs = [
                ("1 месяц", 30, 179, 50, "Пробный тариф на месяц"),
                ("3 месяца", 90, 474, 50, "Популярный тариф"),
                ("6 месяцев", 180, 919, 50, "Выгодный тариф"),
                ("12 месяцев", 365, 1549, 50, "Максимальная экономия")
            ]
            for name, days, price, traffic, desc in default_tariffs:
                self.db.add_tariff(name, days, price, traffic, desc)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Проверка реферального кода
        referrer_id = None
        if context.args:
            try:
                referrer_id = int(context.args[0])
            except ValueError:
                pass
        
        # Регистрируем пользователя
        self.db.register_user(user.id, user.username, referrer_id)
        
        # Если есть реферер, добавляем бонус
        if referrer_id and referrer_id != user.id:
            self.db.update_user_balance(referrer_id, 25)  # Бонус за привлечение
        
        # Создаем главное меню
        keyboard = [
            [InlineKeyboardButton("🔑 Мои подписки", callback_data="my_subscriptions")],
            [InlineKeyboardButton("💳 Купить VPN", callback_data="buy_vpn"),
             InlineKeyboardButton("🎁 Продлить VPN", callback_data="extend_vpn")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")],
            [InlineKeyboardButton("💝 Пригласить", callback_data="invite"),
             InlineKeyboardButton("🎁 Подарить", callback_data="gift_menu")],
            [InlineKeyboardButton("💬 О сервисе", callback_data="about")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""🎭 Добро пожаловать в VPN бота!

👤 Ваш ID: {user.id}
🔗 Статус: Активный пользователь

Выберите действие из меню ниже:"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок"""
        query = update.callback_query
        await query.answer()
        
        # Основные кнопки
        if query.data == "my_subscriptions":
            await self.show_subscriptions(query, context)
        elif query.data == "buy_vpn":
            await self.show_tariffs(query, context)
        elif query.data == "profile":
            await self.show_profile(query, context)
        elif query.data == "invite":
            await self.show_referral_info(query, context)
        elif query.data == "gift_menu":
            await self.show_gift_menu(query, context)
        elif query.data == "about":
            await self.show_about(query, context)
        elif query.data == "back_to_main":
            await self.show_main_menu(query, context)
            
        # Платежи
        elif query.data.startswith("buy_tariff_"):
            tariff_id = int(query.data.split("_")[2])
            await self.payment_handler.create_payment(query, context, tariff_id)
        elif query.data.startswith("pay_telegram_"):
            tariff_id = int(query.data.split("_")[2])
            await self.payment_handler.telegram_payment(query, context, tariff_id)
        elif query.data.startswith("pay_yookassa_"):
            tariff_id = int(query.data.split("_")[2])
            await self.payment_handler.yookassa_payment(query, context, tariff_id)
        elif query.data.startswith("pay_crypto_"):
            tariff_id = int(query.data.split("_")[2])
            await self.payment_handler.crypto_payment(query, context, tariff_id)
        elif query.data.startswith("check_payment_"):
            tariff_id = int(query.data.split("_")[2])
            await self.payment_handler.check_payment(query, context, tariff_id)
            
        # Админ-панель
        elif query.data == "admin_panel":
            await self.admin_handlers.admin_panel(update, context)
        elif query.data == "admin_users":
            await self.admin_handlers.admin_users(query, context)
        elif query.data == "admin_tariffs":
            await self.admin_handlers.admin_tariffs(query, context)
        elif query.data == "admin_gifts":
            await self.admin_handlers.admin_gifts(query, context)
        elif query.data == "admin_broadcast":
            await self.admin_handlers.admin_broadcast(query, context)

    async def show_subscriptions(self, query, context):
        """Показать подписки пользователя"""
        user_id = query.from_user.id
        subscriptions = self.db.get_user_subscriptions(user_id)
        
        if not subscriptions:
            text = """🔑 Ваши подписки:

У вас пока нет активных подписок.
Выберите подходящий тариф для покупки!"""
            
            keyboard = [
                [InlineKeyboardButton("💳 Купить подписку", callback_data="buy_vpn")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
        else:
            text = "🔑 Ваши подписки:\n\n"
            for i, sub in enumerate(subscriptions, 1):
                end_date = datetime.fromisoformat(sub['end_date'].replace('Z', '+00:00'))
                days_left = (end_date - datetime.now()).days
                
                status = "🟢 Активна" if days_left > 0 else "🔴 Истекла"
                text += f"📱 {sub['subscription_name']}\n"
                text += f"📅 До: {end_date.strftime('%d.%m.%Y')}\n"
                text += f"⏰ Осталось: {days_left} дней\n"
                text += f"📊 Статус: {status}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🔧 Подключить устройство", callback_data="connect_device")],
                [InlineKeyboardButton("📱 Android TV", callback_data="android_tv"),
                 InlineKeyboardButton("📱 Показать QR-код", callback_data="show_qr")],
                [InlineKeyboardButton("❌ Удалить", callback_data="delete_subscription")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_tariffs(self, query, context):
        """Показать тарифы"""
        tariffs = self.db.get_tariffs()
        
        text = """💳 Выберите план продления:

💰 Баланс: 0.0 RUB
📅 Текущая дата истечения подписки: 2025-08-18 22:57:19 🔧

"""
        
        keyboard = []
        for tariff in tariffs:
            keyboard.append([InlineKeyboardButton(
                f"🎁 {tariff['name']} — {tariff['price']}₽",
                callback_data=f"buy_tariff_{tariff['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_profile(self, query, context):
        """Показать профиль пользователя"""
        user_id = query.from_user.id
        user = self.db.get_user(user_id)
        subscriptions = self.db.get_user_subscriptions(user_id)
        
        text = f"""👤 Профиль: 😊

— ID: {user_id}
— Баланс: {user['balance']} RUB
— К-во подписок: {len(subscriptions)}

👥 Наш канал 👥
Нажмите кнопку «Купить VPN» 🔗 Продлить VPN», чтобы оформить или продлить подписку."""
        
        keyboard = [
            [InlineKeyboardButton("💳 Купить VPN", callback_data="buy_vpn"),
             InlineKeyboardButton("🔄 Продлить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton("🎁 Мои подписки", callback_data="my_subscriptions")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton("👥 Пригласить", callback_data="invite"),
             InlineKeyboardButton("🎁 Подарить", callback_data="gift_menu")],
            [InlineKeyboardButton("💬 О сервисе", callback_data="about")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_referral_info(self, query, context):
        """Показать реферальную информацию"""
        user_id = query.from_user.id
        stats = self.db.get_referral_stats(user_id)
        
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        text = f"""👥 Ваша реферальная ссылка:

{referral_link}

🎁 Приглашайте друзей и получайте крутые бонусы на каждом уровне! 💰

🏆 Бонусы за приглашения:
1 уровень: ⭐ 25% бонуса
2 уровень: ⭐ 10% бонуса  
3 уровень: ⭐ 6% бонуса
4 уровень: ⭐ 5% бонуса
5 уровень: ⭐ 4% бонуса

📊 Статистика приглашений:
👤 Всего приглашено: {stats['invited_count']} человек
💰 Общий бонус от рефералов: {stats['total_bonus']:.0f} RUB"""
        
        keyboard = [
            [InlineKeyboardButton("📱 Показать QR-код", callback_data="show_ref_qr")],
            [InlineKeyboardButton("🏆 Топ-5", callback_data="top_referrers")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_gift_menu(self, query, context):
        """Показать меню подарков"""
        text = """🎁 Дарите подарки и следите, чтобы они дошли до адресата! 🎁

Выберите срок подписки для подарка:"""
        
        keyboard = [
            [InlineKeyboardButton("🎁 1 месяц — 125 ₽", callback_data="gift_1_month")],
            [InlineKeyboardButton("🎁 3 месяца — 474 ₽", callback_data="gift_3_months")],
            [InlineKeyboardButton("🎁 6 месяцев — 919 ₽", callback_data="gift_6_months")],
            [InlineKeyboardButton("🎁 12 месяцев — 1549 ₽", callback_data="gift_12_months")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_about(self, query, context):
        """Информация о сервисе"""
        text = """💬 Контакты:

⚠️ Подпишись на наш канал!
🚀 Следи за всеми новостями сервиса!
📱 Получай свежие обновления.
🎯 Узнавай о новых тарифах.
👑 Лови эксклюзивные подарки!

🔧 Техническая поддержка
😎 Пиши нам без стеснения!
❓ Решаем любые вопросы по VPN.
⚙️ Помогаем с настройкой.
⚠️ Разбираемся с любыми сложностями!

📱 Продолжая использование сервиса, вы соглашаетесь с правилами предоставления услуг:
Политика конфиденциальности"""
        
        keyboard = [
            [InlineKeyboardButton("💬 Поддержка", url="https://t.me/support")],
            [InlineKeyboardButton("📢 Канал", url="https://t.me/channel")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_main_menu(self, query, context):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("🔑 Мои подписки", callback_data="my_subscriptions")],
            [InlineKeyboardButton("💳 Купить VPN", callback_data="buy_vpn"),
             InlineKeyboardButton("🎁 Продлить VPN", callback_data="extend_vpn")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")],
            [InlineKeyboardButton("💝 Пригласить", callback_data="invite"),
             InlineKeyboardButton("🎁 Подарить", callback_data="gift_menu")],
            [InlineKeyboardButton("💬 О сервисе", callback_data="about")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""🎭 Добро пожаловать в VPN бота!

👤 Ваш ID: {query.from_user.id}
🔗 Статус: Активный пользователь

Выберите действие из меню ниже:"""
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin для входа в админ-панель"""
        await self.admin_handlers.admin_panel(update, context)

def main():
    """Запуск бота"""
    bot = VPNBot()
    
    application = Application.builder().token(bot.token).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("admin", bot.admin_command))
    
    # Обработчики платежей
    application.add_handler(PreCheckoutQueryHandler(bot.payment_handler.handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, bot.payment_handler.handle_successful_payment))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Запуск бота
    print("🚀 VPN Bot запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
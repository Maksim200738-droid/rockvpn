import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class AdminHandlers:
    def __init__(self, db, admin_ids):
        self.db = db
        self.admin_ids = admin_ids
    
    def is_admin(self, user_id):
        """Проверка, является ли пользователь администратором"""
        return user_id in self.admin_ids
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главная админ-панель"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ У вас нет доступа к админ-панели")
            return
        
        # Статистика
        stats = self.get_bot_stats()
        
        text = f"""👑 **АДМИН-ПАНЕЛЬ**

📊 **Статистика:**
👥 Всего пользователей: {stats['total_users']}
📱 Активных подписок: {stats['active_subscriptions']}
💰 Общий доход: {stats['total_revenue']:.2f} ₽
🎁 Созданных подарков: {stats['total_gifts']}

📅 **За сегодня:**
👤 Новых пользователей: {stats['today_users']}
💳 Новых подписок: {stats['today_subscriptions']}"""

        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
             InlineKeyboardButton("📱 Подписки", callback_data="admin_subscriptions")],
            [InlineKeyboardButton("💳 Тарифы", callback_data="admin_tariffs"),
             InlineKeyboardButton("🎁 Подарки", callback_data="admin_gifts")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
             InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def admin_users(self, query, context):
        """Управление пользователями"""
        text = """👥 **Управление пользователями**

Выберите действие:"""
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_find_user")],
            [InlineKeyboardButton("📋 Список пользователей", callback_data="admin_list_users")],
            [InlineKeyboardButton("💰 Изменить баланс", callback_data="admin_change_balance")],
            [InlineKeyboardButton("🚫 Заблокировать", callback_data="admin_ban_user")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def admin_tariffs(self, query, context):
        """Управление тарифами"""
        tariffs = self.db.get_tariffs()
        
        text = "💳 **Управление тарифами**\n\n"
        text += "📋 **Текущие тарифы:**\n"
        
        for tariff in tariffs:
            text += f"• {tariff['name']} - {tariff['price']}₽ ({tariff['duration_days']} дн.)\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тариф", callback_data="admin_add_tariff")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data="admin_edit_tariff")],
            [InlineKeyboardButton("❌ Удалить", callback_data="admin_delete_tariff")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def admin_gifts(self, query, context):
        """Управление подарками"""
        text = """🎁 **Управление подарками**

Выберите действие:"""
        
        keyboard = [
            [InlineKeyboardButton("🆕 Создать подарок", callback_data="admin_create_gift")],
            [InlineKeyboardButton("📋 Список подарков", callback_data="admin_list_gifts")],
            [InlineKeyboardButton("🔍 Статистика подарков", callback_data="admin_gift_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def admin_broadcast(self, query, context):
        """Рассылка сообщений"""
        text = """📢 **Рассылка сообщений**

⚠️ Используйте с осторожностью!

Выберите тип рассылки:"""
        
        keyboard = [
            [InlineKeyboardButton("👥 Всем пользователям", callback_data="broadcast_all")],
            [InlineKeyboardButton("🔑 Пользователям с подписками", callback_data="broadcast_subscribers")],
            [InlineKeyboardButton("💰 По балансу", callback_data="broadcast_balance")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    def get_bot_stats(self):
        """Получение статистики бота"""
        self.db.ensure_connected()
        c = self.db.conn.cursor()
        
        # Общее количество пользователей
        c.execute("SELECT COUNT(*) as count FROM users")
        total_users = c.fetchone()['count']
        
        # Активные подписки
        c.execute("SELECT COUNT(*) as count FROM subscriptions WHERE is_active = 1 AND end_date > datetime('now')")
        active_subscriptions = c.fetchone()['count']
        
        # Общий доход (примерный расчет)
        c.execute("SELECT COUNT(*) * 500 as revenue FROM subscriptions WHERE is_active = 1")
        total_revenue = c.fetchone()['revenue'] or 0
        
        # Созданные подарки
        c.execute("SELECT COUNT(*) as count FROM gifts")
        total_gifts = c.fetchone()['count']
        
        # Пользователи за сегодня
        c.execute("SELECT COUNT(*) as count FROM users WHERE date(registration_date) = date('now')")
        today_users = c.fetchone()['count']
        
        # Подписки за сегодня
        c.execute("SELECT COUNT(*) as count FROM subscriptions WHERE date(start_date) = date('now')")
        today_subscriptions = c.fetchone()['count']
        
        return {
            'total_users': total_users,
            'active_subscriptions': active_subscriptions,
            'total_revenue': total_revenue,
            'total_gifts': total_gifts,
            'today_users': today_users,
            'today_subscriptions': today_subscriptions
        }

    async def broadcast_message(self, context, message_text, target_users):
        """Отправка рассылки"""
        sent_count = 0
        failed_count = 0
        
        for user_id in target_users:
            try:
                await context.bot.send_message(user_id, message_text, parse_mode='Markdown')
                sent_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Failed to send message to {user_id}: {e}")
        
        return sent_count, failed_count

    def get_users_by_criteria(self, criteria="all"):
        """Получение списка пользователей по критериям"""
        self.db.ensure_connected()
        c = self.db.conn.cursor()
        
        if criteria == "all":
            c.execute("SELECT user_id FROM users")
        elif criteria == "subscribers":
            c.execute("""
                SELECT DISTINCT u.user_id FROM users u 
                JOIN subscriptions s ON u.user_id = s.user_id 
                WHERE s.is_active = 1 AND s.end_date > datetime('now')
            """)
        elif criteria == "balance":
            c.execute("SELECT user_id FROM users WHERE balance > 0")
        
        return [row['user_id'] for row in c.fetchall()]
import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes

class PaymentHandler:
    def __init__(self, db):
        self.db = db
        self.payment_token = os.getenv('PAYMENT_TOKEN')
        self.yookassa_shop_id = os.getenv('YOOKASSA_SHOP_ID')
        self.yookassa_secret = os.getenv('YOOKASSA_SECRET_KEY')
    
    async def create_payment(self, query, context, tariff_id):
        """Создание платежа для тарифа"""
        user_id = query.from_user.id
        
        # Получаем информацию о тарифе
        tariffs = self.db.get_tariffs()
        tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
        
        if not tariff:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        # Создаем описание платежа
        title = f"VPN подписка: {tariff['name']}"
        description = f"Подписка на {tariff['duration_days']} дней"
        payload = f"tariff_{tariff_id}_{user_id}_{int(datetime.now().timestamp())}"
        
        # Цена в копейках
        price = int(tariff['price'] * 100)
        
        # Создаем кнопки оплаты
        keyboard = [
            [InlineKeyboardButton("💳 Telegram Pay", callback_data=f"pay_telegram_{tariff_id}")],
            [InlineKeyboardButton("💰 YooKassa", callback_data=f"pay_yookassa_{tariff_id}")],
            [InlineKeyboardButton("🔗 Криптовалюта", callback_data=f"pay_crypto_{tariff_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="buy_vpn")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""💳 **Оплата подписки**

📦 Тариф: {tariff['name']}
⏰ Длительность: {tariff['duration_days']} дней
💰 Цена: {tariff['price']} ₽

Выберите способ оплаты:"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def telegram_payment(self, query, context, tariff_id):
        """Обработка оплаты через Telegram Payments"""
        if not self.payment_token:
            await query.answer("❌ Telegram Payments не настроен", show_alert=True)
            return
        
        user_id = query.from_user.id
        tariffs = self.db.get_tariffs()
        tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
        
        if not tariff:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        title = f"VPN подписка: {tariff['name']}"
        description = f"Подписка на {tariff['duration_days']} дней"
        payload = f"tariff_{tariff_id}_{user_id}"
        currency = "RUB"
        price = int(tariff['price'] * 100)  # В копейках
        
        prices = [LabeledPrice(title, price)]
        
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=self.payment_token,
            currency=currency,
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            send_phone_number_to_provider=False,
            send_email_to_provider=False,
            is_flexible=False
        )

    async def yookassa_payment(self, query, context, tariff_id):
        """Создание ссылки для оплаты через YooKassa"""
        if not self.yookassa_shop_id or not self.yookassa_secret:
            await query.answer("❌ YooKassa не настроен", show_alert=True)
            return
        
        user_id = query.from_user.id
        tariffs = self.db.get_tariffs()
        tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
        
        if not tariff:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        # Здесь должна быть интеграция с YooKassa API
        # Для примера создаем простую ссылку
        payment_url = f"https://yoomoney.ru/quickpay/shop-widget?writer=seller&targets=VPN%20{tariff['name']}&targets-hint=&default-sum={tariff['price']}&button-text=11&payment-type-choice=on&mobile-payment-type-choice=on&hint=&successURL=&quickpay=shop&account={self.yookassa_shop_id}"
        
        keyboard = [
            [InlineKeyboardButton("💰 Оплатить", url=payment_url)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"check_payment_{tariff_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"pay_tariff_{tariff_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""💰 **Оплата через YooMoney**

📦 Тариф: {tariff['name']}
💰 Цена: {tariff['price']} ₽

1. Нажмите "Оплатить"
2. Выполните платеж
3. Вернитесь и нажмите "Я оплатил"

⚠️ Подписка активируется автоматически после подтверждения платежа."""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def crypto_payment(self, query, context, tariff_id):
        """Оплата криптовалютой"""
        tariffs = self.db.get_tariffs()
        tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
        
        if not tariff:
            await query.answer("❌ Тариф не найден", show_alert=True)
            return
        
        # Курс криптовалют (в реальном проекте получать с API)
        btc_rate = 6500000  # BTC в рублях
        usdt_rate = 92  # USDT в рублях
        
        btc_amount = tariff['price'] / btc_rate
        usdt_amount = tariff['price'] / usdt_rate
        
        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin", callback_data=f"crypto_btc_{tariff_id}")],
            [InlineKeyboardButton("💎 USDT", callback_data=f"crypto_usdt_{tariff_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"pay_tariff_{tariff_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""₿ **Оплата криптовалютой**

📦 Тариф: {tariff['name']}
💰 Цена: {tariff['price']} ₽

💰 Курсы:
₿ Bitcoin: {btc_amount:.8f} BTC
💎 USDT: {usdt_amount:.2f} USDT

Выберите валюту для оплаты:"""
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def process_successful_payment(self, user_id, tariff_id):
        """Обработка успешного платежа"""
        tariffs = self.db.get_tariffs()
        tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
        
        if not tariff:
            return False
        
        # Добавляем подписку пользователю
        subscription_id = self.db.add_subscription(
            user_id=user_id,
            subscription_name=tariff['name'],
            subscription_type="premium",
            duration_days=tariff['duration_days']
        )
        
        # Здесь можно добавить генерацию VPN ключа
        # vpn_config = self.generate_vpn_config(user_id, subscription_id)
        
        return True

    async def check_payment(self, query, context, tariff_id):
        """Проверка платежа (заглушка)"""
        user_id = query.from_user.id
        
        # В реальном проекте здесь должна быть проверка через API платежной системы
        # Для демонстрации просто активируем подписку
        
        success = await self.process_successful_payment(user_id, tariff_id)
        
        if success:
            tariffs = self.db.get_tariffs()
            tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
            
            text = f"""✅ **Платеж успешно обработан!**

🎉 Подписка "{tariff['name']}" активирована
⏰ Срок действия: {tariff['duration_days']} дней

🔑 Ваши ключи доступны в разделе "Мои подписки"

Спасибо за покупку! 💝"""
            
            keyboard = [
                [InlineKeyboardButton("🔑 Мои подписки", callback_data="my_subscriptions")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.answer("❌ Ошибка при обработке платежа", show_alert=True)

    def generate_payment_hash(self, data):
        """Генерация хеша для проверки платежа"""
        if not self.yookassa_secret:
            return None
        
        message = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
        return hmac.new(
            self.yookassa_secret.encode(),
            message.encode(),
            hashlib.sha1
        ).hexdigest()

    async def handle_pre_checkout_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка предварительной проверки платежа Telegram"""
        query = update.pre_checkout_query
        
        # Проверяем payload
        if query.invoice_payload.startswith("tariff_"):
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Некорректный платеж")

    async def handle_successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка успешного платежа Telegram"""
        payment = update.message.successful_payment
        payload = payment.invoice_payload
        
        if payload.startswith("tariff_"):
            parts = payload.split("_")
            tariff_id = int(parts[1])
            user_id = int(parts[2])
            
            # Активируем подписку
            success = await self.process_successful_payment(user_id, tariff_id)
            
            if success:
                tariffs = self.db.get_tariffs()
                tariff = next((t for t in tariffs if t['id'] == tariff_id), None)
                
                await update.message.reply_text(
                    f"✅ Спасибо за оплату! Подписка '{tariff['name']}' активирована.\n"
                    f"🔑 Ваши ключи доступны в разделе 'Мои подписки'."
                )
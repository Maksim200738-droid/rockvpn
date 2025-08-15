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

class VPNManager:
    def __init__(self):
        self.panel_url = os.getenv('PANEL_URL')
        self.username = os.getenv('PANEL_USERNAME')
        self.password = os.getenv('PANEL_PASSWORD')
        self.server_address = os.getenv('SERVER_ADDRESS')
        self.reality_port = os.getenv('REALITY_PORT')
        self.reality_public_key = os.getenv('REALITY_PUBLIC_KEY')
        self.reality_short_id = os.getenv('REALITY_SHORT_ID')
        self.sni = os.getenv('SNI')
        self.session = requests.Session()
        self.login()

    def login(self):
        login_data = {
            'username': self.username,
            'password': self.password
        }
        response = self.session.post(f"{self.panel_url}/login", json=login_data)
        if response.status_code != 200:
            raise Exception("Failed to login to 3X-UI panel")

    def get_inbounds(self):
        response = self.session.get(f"{self.panel_url}/panel/api/inbounds/list")
        return response.json()['obj']

    def create_inbound(self):
        inbound_data = {
            "up": 0,
            "down": 0,
            "total": 0,
            "remark": "VLESS-REALITY",
            "enable": True,
            "expiryTime": 0,
            "listen": "",
            "port": int(self.reality_port),
            "protocol": "vless",
            "settings": json.dumps({
                "clients": [],
                "decryption": "none",
                "fallbacks": []
            }),
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "yahoo.com:443",
                    "xver": 0,
                    "serverNames": [self.sni],
                    "privateKey": "WEctUqeG9v10LRUD84AizelHQZpm9qPPKiNaJwW9IXM",
                    "minClient": "",
                    "maxClient": "",
                    "maxTimediff": 0,
                    "shortIds": [self.reality_short_id],
                    "settings": {
                        "publicKey": self.reality_public_key,
                        "fingerprint": "chrome",
                        "serverName": "",
                        "spiderX": "/"
                    }
                },
                "tcpSettings": {
                    "acceptProxyProtocol": False,
                    "header": {
                        "type": "none"
                    }
                }
            }),
            "sniffing": json.dumps({
                "enabled": False,
                "destOverride": ["http", "tls", "quic", "fakedns"],
                "metadataOnly": False,
                "routeOnly": False
            }),
            "allocate": json.dumps({
                "strategy": "always",
                "refresh": 5,
                "concurrency": 3
            })
        }
        print("Creating inbound with data:", json.dumps(inbound_data, indent=2))
        response = self.session.post(f"{self.panel_url}/panel/api/inbounds/add", json=inbound_data)
        print("Response status:", response.status_code)
        print("Response content:", response.text)
        return response.json()

    def create_client(self, inbound_id):
        print(f"Creating client for inbound {inbound_id}")
        client_id = str(uuid.uuid4())
        print(f"Generated client_id: {client_id}")
        
        client_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_id,
                    "flow": "xtls-rprx-vision",
                    "email": f"user_{client_id[:8]}",
                    "enable": True,
                    "expiryTime": 0,
                    "subId": "",
                    "tgId": "",
                    "totalGB": 0,
                    "limitIp": 0,
                    "reset": 0
                }]
            })
        }
        print("Creating client with data:", json.dumps(client_data, indent=2))
        
        try:
            response = self.session.post(f"{self.panel_url}/panel/api/inbounds/addClient", json=client_data)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content: {response.text}")
            
            if response.status_code == 200:
                # Возвращаем информацию о клиенте независимо от ответа сервера,
                # так как клиент уже создан с нашим client_id
                client_info = {
                    'id': client_id,
                    'email': f"user_{client_id[:8]}"
                }
                print(f"Returning client info: {json.dumps(client_info, indent=2)}")
                return client_info
            else:
                print(f"Request failed with status {response.status_code}")
                print(f"Response content: {response.text}")
        except Exception as e:
            print(f"Error during client creation request: {e}")
        
        return None

    def delete_client(self, inbound_id, client_id):
        """Удаляет клиента с VPN-сервера"""
        try:
            # Преобразуем inbound_id в число для корректного сравнения
            inbound_id = int(inbound_id)
            
            # Проверяем существование клиента
            inbounds = self.get_inbounds()
            inbound = next((inb for inb in inbounds if int(inb['id']) == inbound_id), None)
            
            if not inbound:
                raise Exception(f"Inbound {inbound_id} not found")
                
            # Проверяем наличие клиента в inbound
            settings = json.loads(inbound['settings'])
            clients = settings.get('clients', [])
            
            print(f"Current clients in inbound {inbound_id}:")
            for client in clients:
                print(f"- {client['id']}")
            
            client_exists = any(client['id'] == client_id for client in clients)
            
            if not client_exists:
                print(f"Client {client_id} not found in inbound {inbound_id}")
                return True  # Считаем успешным, так как клиента уже нет
            
            # Удаляем клиента
            print(f"Attempting to delete client {client_id} from inbound {inbound_id}")
            response = self.session.post(
                f"{self.panel_url}/panel/api/inbounds/delClient/{inbound_id}/{client_id}"
            )
            print(f"Delete response status: {response.status_code}")
            print(f"Delete response content: {response.text}")
            
            # Проверяем, действительно ли клиент удален
            inbounds_after = self.get_inbounds()
            inbound_after = next((inb for inb in inbounds_after if int(inb['id']) == inbound_id), None)
            if inbound_after:
                settings_after = json.loads(inbound_after['settings'])
                clients_after = settings_after.get('clients', [])
                client_still_exists = any(client['id'] == client_id for client in clients_after)
                
                if client_still_exists:
                    print(f"Warning: Client {client_id} still exists after deletion!")
                    # Пробуем альтернативный метод удаления
                    print("Trying alternative deletion method...")
                    new_clients = [c for c in clients if c['id'] != client_id]
                    settings['clients'] = new_clients
                    update_data = {
                        'up': inbound['up'],
                        'down': inbound['down'],
                        'total': inbound['total'],
                        'remark': inbound['remark'],
                        'enable': inbound['enable'],
                        'expiryTime': inbound['expiryTime'],
                        'listen': inbound['listen'],
                        'port': inbound['port'],
                        'protocol': inbound['protocol'],
                        'settings': json.dumps(settings),
                        'streamSettings': inbound['streamSettings'],
                        'sniffing': inbound['sniffing']
                    }
                    
                    update_response = self.session.post(
                        f"{self.panel_url}/panel/api/inbounds/update/{inbound_id}",
                        json=update_data
                    )
                    print(f"Update response status: {update_response.status_code}")
                    print(f"Update response content: {update_response.text}")
                    
                    if update_response.status_code != 200:
                        raise Exception("Failed to update inbound settings")
                else:
                    print(f"Client {client_id} successfully deleted")
            
            return True
            
        except Exception as e:
            print(f"Error in delete_client: {str(e)}")
            print(f"Client ID: {client_id}")
            print(f"Inbound ID: {inbound_id}")
            raise

    def generate_vless_link(self, client):
        client_id = client['id']  # Получаем ID из объекта клиента
        link = f"vless://{client_id}@{self.server_address}:{self.reality_port}?type=tcp&security=reality&pbk={self.reality_public_key}&fp=chrome&sni={self.sni}&sid={self.reality_short_id}&spx=%2F&flow=xtls-rprx-vision#{client_id[:8]}"
        print("Generated VLESS link:", link)
        return link

# Состояния для ConversationHandler
MAIN_MENU, PAYMENT_AMOUNT, PAYMENT_CONFIRMATION = range(3)

# Состояния для админ-панели
ADMIN_BROADCAST, ADMIN_BROADCAST_PREVIEW = range(10, 12)

TARIFFS = {
    "trial": {"name": "Пробный период", "price": 0, "duration": 3},
    "1_99": {"name": "1 месяц", "price": 99, "duration": 30},
    "2_179": {"name": "2 месяца", "price": 179, "duration": 60},
    "6_499": {"name": "6 месяцев", "price": 499, "duration": 180},
    "12_899": {"name": "1 год", "price": 899, "duration": 365}
}

# Словарь для хранения ожидающих подтверждения платежей
pending_payments = {}

def update_user_info(user):
    """Обновляет информацию о пользователе в базе данных"""
    if user:
        db.add_user(user.id, user.username or "Unknown", None)

async def create_trial_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Создает пробную подписку на 3 дня"""
    try:
        # Проверяем, была ли уже пробная подписка
        subscriptions = db.get_user_subscriptions(user_id)
        for sub in subscriptions:
            if sub['subscription_type'] == 'trial':
                return False, "У вас уже была пробная подписка"

        # Создаем VPN-клиента
        vpn_manager = VPNManager()
        inbound_id = vpn_manager.get_inbounds()[0]['id']
        client = vpn_manager.create_client(inbound_id)
        
        if not client:
            return False, "Ошибка при создании VPN-клиента"

        # Генерируем VPN конфигурацию
        vpn_config = vpn_manager.generate_vless_link(client)
        
        # Создаем подписку на 3 дня
        db.add_subscription(
            user_id=user_id,
            subscription_type='trial',
            vpn_config=vpn_config,
            client_id=client['id'],
            inbound_id=inbound_id
        )
        
        return True, vpn_config
    
    except Exception as e:
        return False, f"Ошибка при создании пробной подписки: {str(e)}"

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

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Нет"
    
    # Получаем активную подписку
    subscription = db.get_active_subscription(user_id)
    
    # Получаем статистику трафика
    traffic_stats = db.get_traffic_stats(user_id)
    
    # Форматируем статистику трафика в ГБ
    def format_bytes(bytes_):
        if bytes_ is None:
            return "0.00"
        return f"{bytes_ / (1024**3):.2f}"  # Конвертируем байты в ГБ
    
    # Форматируем дату
    def format_date(date_str):
        if not date_str:
            return "Нет активной подписки"
        try:
            date = datetime.fromisoformat(date_str)
            return date.strftime("%d.%m.%Y %H:%M")
        except:
            return "Ошибка формата даты"
    
    # Формируем текст профиля
    profile_text = (
        "📊 Информация о текущей подписке:\n\n"
        f"👤 Логин: {username}\n"
        "📈 Использование трафика:\n"
    )
    
    if subscription:
        upload = traffic_stats['upload_bytes']
        download = traffic_stats['download_bytes']
        total = upload + download
        profile_text += (
            f"├─ ↑ Отправлено: {format_bytes(upload)} ГБ\n"
            f"├─ ↓ Получено: {format_bytes(download)} ГБ\n"
            f"└─ 📊 Всего: {format_bytes(total)} ГБ\n\n"
            "⏳ Срок действия до:\n"
            f"└─ 📅 {format_date(subscription['end_date'])}\n\n"
            "💾 Лимиты трафика:\n"
            "├─ 📦 Общий объем: ∞\n"
            "└─ ✨ Осталось: ∞\n\n"
            "📚 Выберите вашу операционную систему для настройки:"
        )
        # --- КНОПКА MINI APP ---
        vpn_key = subscription['vpn_config']
        expires = format_date(subscription['end_date'])
        miniapp_url = f"https://maksim200738-droid.github.io/rockvpn/?key={vpn_key}&expires={expires}"
        keyboard = [
            [InlineKeyboardButton("Подключить устройство", web_app=WebAppInfo(url=miniapp_url))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        profile_text += (
            "├─ ↑ Отправлено: 0.00 ГБ\n"
            "├─ ↓ Получено: 0.00 ГБ\n"
            "└─ 📊 Всего: 0.00 ГБ\n\n"
            "⏳ Срок действия до:\n"
            "└─ 📅 Нет активной подписки\n\n"
            "💾 Лимиты трафика:\n"
            "├─ 📦 Общий объем: 0\n"
            "└─ ✨ Осталось: 0\n\n"
            "📚 Выберите вашу операционную систему для настройки:"
        )
        reply_markup = None
    # Клавиатура для выбора ОС
    os_keyboard = [
        [
            InlineKeyboardButton("📱 iOS", callback_data="ios_instructions"),
            InlineKeyboardButton("🤖 Android", callback_data="android_instructions")
        ],
        [
            InlineKeyboardButton("🖥 Windows", callback_data="windows_instructions"),
            InlineKeyboardButton("🍎 macOS", callback_data="macos_instructions")
        ],
        [InlineKeyboardButton("🐧 Linux", callback_data="linux_instructions")]
    ]
    os_reply_markup = InlineKeyboardMarkup(os_keyboard)
    # Отправляем сообщение
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text=profile_text,
            reply_markup=reply_markup or os_reply_markup
        )
    else:
        await update.message.reply_text(
            text=profile_text,
            reply_markup=reply_markup or os_reply_markup
        )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    tariffs_text = """💎 VPN ТАРИФЫ 💎

💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:
├—♦️ 1 месяц: 99₽
├—♦️ 2 месяца: 179₽
├—♦️ 6 месяцев: 499₽
└—♦️ 1 год: 899₽

⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:
├—⚡️ Максимальная скорость
├—📱 Безлимитный трафик
├—🚀 Обход блокировок
├—🔒 Надежное шифрование
└—📱 Все устройства

✨ ДОПОЛНИТЕЛЬНО:
├—↩️ Гарантия возврата 30 дней
├—🎁 Бонусная программа
└—📞 Поддержка 24/7: @rockprojectoff

🛡️ Безопасность и скорость в одном пакете!

🚀 Выберите тариф VPN

🔒 Безопасность и скорость на любой срок"""

    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        tariffs_text,
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📨 Создание рассылки\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Поддерживается форматирование Markdown."
    )
    return ADMIN_BROADCAST

async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр рассылки"""
    message_text = update.message.text
    context.user_data['broadcast_text'] = message_text
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send_broadcast"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")
        ]
    ]
    
    await update.message.reply_text(
        "📨 Предпросмотр рассылки:\n\n"
        f"{message_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ADMIN_BROADCAST_PREVIEW

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    query = update.callback_query
    await query.answer()
    
    broadcast_text = context.user_data.get('broadcast_text')
    if not broadcast_text:
        await query.message.reply_text("❌ Ошибка: текст рассылки не найден")
        return
    
    users = db.get_all_users()
    success_count = 0
    fail_count = 0
    
    progress_message = await query.message.reply_text("📤 Отправка рассылки...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=broadcast_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
        
        if (success_count + fail_count) % 10 == 0:
            await progress_message.edit_text(
                f"📤 Отправка рассылки...\n"
                f"Отправлено: {success_count + fail_count}/{len(users)}"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("❌ Рассылка отменена")
    return ConversationHandler.END

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    tariff_stats = []
    for tariff_id, tariff_data in TARIFFS.items():
        if tariff_id != 'trial':  # Пропускаем пробный период в статистике
            count = db.get_subscriptions_count_by_tariff(tariff_id)
            if count > 0:  # Показываем только тарифы с активными подписками
                tariff_stats.append(f"├—💫 {tariff_data['name']}: {count}\n")
    
    if tariff_stats:
        stats_text += "".join(tariff_stats)
    else:
        stats_text += "├—❌ Нет активных подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:\n"
        "├—♦️ 1 месяц: 99₽\n"
        "├—♦️ 2 месяца: 179₽\n"
        "├—♦️ 6 месяцев: 499₽\n"
        "└—♦️ 1 год: 899₽\n\n"
        "⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:\n"
        "├—⚡️ Максимальная скорость\n"
        "├—📱 Безлимитный трафик\n"
        "├—🚀 Обход блокировок\n"
        "├—🔒 Надежное шифрование\n"
        "└—📱 Все устройства\n\n"
        "✨ ДОПОЛНИТЕЛЬНО:\n"
        "├—↩️ Гарантия возврата 30 дней\n"
        "├—🎁 Бонусная программа\n"
        "└—📞 Поддержка 24/7: @blackvpn_support\n\n"
        "🛡️ Безопасность и скорость в одном пакете!\n\n"
        "🚀 Выберите тариф VPN\n\n"
        "🔒 Безопасность и скорость на любой срок",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📨 Создание рассылки\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Поддерживается форматирование Markdown."
    )
    return ADMIN_BROADCAST

async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр рассылки"""
    message_text = update.message.text
    context.user_data['broadcast_text'] = message_text
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send_broadcast"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")
        ]
    ]
    
    await update.message.reply_text(
        "📨 Предпросмотр рассылки:\n\n"
        f"{message_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ADMIN_BROADCAST_PREVIEW

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    query = update.callback_query
    await query.answer()
    
    broadcast_text = context.user_data.get('broadcast_text')
    if not broadcast_text:
        await query.message.reply_text("❌ Ошибка: текст рассылки не найден")
        return
    
    users = db.get_all_users()
    success_count = 0
    fail_count = 0
    
    progress_message = await query.message.reply_text("📤 Отправка рассылки...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=broadcast_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
        
        if (success_count + fail_count) % 10 == 0:
            await progress_message.edit_text(
                f"📤 Отправка рассылки...\n"
                f"Отправлено: {success_count + fail_count}/{len(users)}"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("❌ Рассылка отменена")
    return ConversationHandler.END

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    tariff_stats = []
    for tariff_id, tariff_data in TARIFFS.items():
        if tariff_id != 'trial':  # Пропускаем пробный период в статистике
            count = db.get_subscriptions_count_by_tariff(tariff_id)
            if count > 0:  # Показываем только тарифы с активными подписками
                tariff_stats.append(f"├—💫 {tariff_data['name']}: {count}\n")
    
    if tariff_stats:
        stats_text += "".join(tariff_stats)
    else:
        stats_text += "├—❌ Нет активных подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:\n"
        "├—♦️ 1 месяц: 99₽\n"
        "├—♦️ 2 месяца: 179₽\n"
        "├—♦️ 6 месяцев: 499₽\n"
        "└—♦️ 1 год: 899₽\n\n"
        "⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:\n"
        "├—⚡️ Максимальная скорость\n"
        "├—📱 Безлимитный трафик\n"
        "├—🚀 Обход блокировок\n"
        "├—🔒 Надежное шифрование\n"
        "└—📱 Все устройства\n\n"
        "✨ ДОПОЛНИТЕЛЬНО:\n"
        "├—↩️ Гарантия возврата 30 дней\n"
        "├—🎁 Бонусная программа\n"
        "└—📞 Поддержка 24/7: @blackvpn_support\n\n"
        "🛡️ Безопасность и скорость в одном пакете!\n\n"
        "🚀 Выберите тариф VPN\n\n"
        "🔒 Безопасность и скорость на любой срок",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📨 Создание рассылки\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Поддерживается форматирование Markdown."
    )
    return ADMIN_BROADCAST

async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр рассылки"""
    message_text = update.message.text
    context.user_data['broadcast_text'] = message_text
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send_broadcast"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")
        ]
    ]
    
    await update.message.reply_text(
        "📨 Предпросмотр рассылки:\n\n"
        f"{message_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ADMIN_BROADCAST_PREVIEW

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    query = update.callback_query
    await query.answer()
    
    broadcast_text = context.user_data.get('broadcast_text')
    if not broadcast_text:
        await query.message.reply_text("❌ Ошибка: текст рассылки не найден")
        return
    
    users = db.get_all_users()
    success_count = 0
    fail_count = 0
    
    progress_message = await query.message.reply_text("📤 Отправка рассылки...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=broadcast_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
        
        if (success_count + fail_count) % 10 == 0:
            await progress_message.edit_text(
                f"📤 Отправка рассылки...\n"
                f"Отправлено: {success_count + fail_count}/{len(users)}"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("❌ Рассылка отменена")
    return ConversationHandler.END

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    tariff_stats = []
    for tariff_id, tariff_data in TARIFFS.items():
        if tariff_id != 'trial':  # Пропускаем пробный период в статистике
            count = db.get_subscriptions_count_by_tariff(tariff_id)
            if count > 0:  # Показываем только тарифы с активными подписками
                tariff_stats.append(f"├—💫 {tariff_data['name']}: {count}\n")
    
    if tariff_stats:
        stats_text += "".join(tariff_stats)
    else:
        stats_text += "├—❌ Нет активных подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:\n"
        "├—♦️ 1 месяц: 99₽\n"
        "├—♦️ 2 месяца: 179₽\n"
        "├—♦️ 6 месяцев: 499₽\n"
        "└—♦️ 1 год: 899₽\n\n"
        "⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:\n"
        "├—⚡️ Максимальная скорость\n"
        "├—📱 Безлимитный трафик\n"
        "├—🚀 Обход блокировок\n"
        "├—🔒 Надежное шифрование\n"
        "└—📱 Все устройства\n\n"
        "✨ ДОПОЛНИТЕЛЬНО:\n"
        "├—↩️ Гарантия возврата 30 дней\n"
        "├—🎁 Бонусная программа\n"
        "└—📞 Поддержка 24/7: @blackvpn_support\n\n"
        "🛡️ Безопасность и скорость в одном пакете!\n\n"
        "🚀 Выберите тариф VPN\n\n"
        "🔒 Безопасность и скорость на любой срок",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📨 Создание рассылки\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Поддерживается форматирование Markdown."
    )
    return ADMIN_BROADCAST

async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр рассылки"""
    message_text = update.message.text
    context.user_data['broadcast_text'] = message_text
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send_broadcast"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")
        ]
    ]
    
    await update.message.reply_text(
        "📨 Предпросмотр рассылки:\n\n"
        f"{message_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ADMIN_BROADCAST_PREVIEW

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    query = update.callback_query
    await query.answer()
    
    broadcast_text = context.user_data.get('broadcast_text')
    if not broadcast_text:
        await query.message.reply_text("❌ Ошибка: текст рассылки не найден")
        return
    
    users = db.get_all_users()
    success_count = 0
    fail_count = 0
    
    progress_message = await query.message.reply_text("📤 Отправка рассылки...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=broadcast_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
        
        if (success_count + fail_count) % 10 == 0:
            await progress_message.edit_text(
                f"📤 Отправка рассылки...\n"
                f"Отправлено: {success_count + fail_count}/{len(users)}"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("❌ Рассылка отменена")
    return ConversationHandler.END

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    tariff_stats = []
    for tariff_id, tariff_data in TARIFFS.items():
        if tariff_id != 'trial':  # Пропускаем пробный период в статистике
            count = db.get_subscriptions_count_by_tariff(tariff_id)
            if count > 0:  # Показываем только тарифы с активными подписками
                tariff_stats.append(f"├—💫 {tariff_data['name']}: {count}\n")
    
    if tariff_stats:
        stats_text += "".join(tariff_stats)
    else:
        stats_text += "├—❌ Нет активных подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:\n"
        "├—♦️ 1 месяц: 99₽\n"
        "├—♦️ 2 месяца: 179₽\n"
        "├—♦️ 6 месяцев: 499₽\n"
        "└—♦️ 1 год: 899₽\n\n"
        "⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:\n"
        "├—⚡️ Максимальная скорость\n"
        "├—📱 Безлимитный трафик\n"
        "├—🚀 Обход блокировок\n"
        "├—🔒 Надежное шифрование\n"
        "└—📱 Все устройства\n\n"
        "✨ ДОПОЛНИТЕЛЬНО:\n"
        "├—↩️ Гарантия возврата 30 дней\n"
        "├—🎁 Бонусная программа\n"
        "└—📞 Поддержка 24/7: @blackvpn_support\n\n"
        "🛡️ Безопасность и скорость в одном пакете!\n\n"
        "🚀 Выберите тариф VPN\n\n"
        "🔒 Безопасность и скорость на любой срок",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📨 Создание рассылки\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n"
        "Поддерживается форматирование Markdown."
    )
    return ADMIN_BROADCAST

async def preview_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпросмотр рассылки"""
    message_text = update.message.text
    context.user_data['broadcast_text'] = message_text
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send_broadcast"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")
        ]
    ]
    
    await update.message.reply_text(
        "📨 Предпросмотр рассылки:\n\n"
        f"{message_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ADMIN_BROADCAST_PREVIEW

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    query = update.callback_query
    await query.answer()
    
    broadcast_text = context.user_data.get('broadcast_text')
    if not broadcast_text:
        await query.message.reply_text("❌ Ошибка: текст рассылки не найден")
        return
    
    users = db.get_all_users()
    success_count = 0
    fail_count = 0
    
    progress_message = await query.message.reply_text("📤 Отправка рассылки...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=broadcast_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
        
        if (success_count + fail_count) % 10 == 0:
            await progress_message.edit_text(
                f"📤 Отправка рассылки...\n"
                f"Отправлено: {success_count + fail_count}/{len(users)}"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text("❌ Рассылка отменена")
    return ConversationHandler.END

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    tariff_stats = []
    for tariff_id, tariff_data in TARIFFS.items():
        if tariff_id != 'trial':  # Пропускаем пробный период в статистике
            count = db.get_subscriptions_count_by_tariff(tariff_id)
            if count > 0:  # Показываем только тарифы с активными подписками
                tariff_stats.append(f"├—💫 {tariff_data['name']}: {count}\n")
    
    if tariff_stats:
        stats_text += "".join(tariff_stats)
    else:
        stats_text += "├—❌ Нет активных подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_info(user)
    
    keyboard = [
        [InlineKeyboardButton("🚀 1 месяц", callback_data="tariff_1_99")],
        [InlineKeyboardButton("⭐ 2 месяца", callback_data="tariff_2_179")],
        [InlineKeyboardButton("💎 6 месяцев", callback_data="tariff_6_499")],
        [InlineKeyboardButton("👑 1 год", callback_data="tariff_12_899")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 СТОИМОСТЬ ПОДКЛЮЧЕНИЯ:\n"
        "├—♦️ 1 месяц: 99₽\n"
        "├—♦️ 2 месяца: 179₽\n"
        "├—♦️ 6 месяцев: 499₽\n"
        "└—♦️ 1 год: 899₽\n\n"
        "⭐️ ПРЕИМУЩЕСТВА СЕРВИСА:\n"
        "├—⚡️ Максимальная скорость\n"
        "├—📱 Безлимитный трафик\n"
        "├—🚀 Обход блокировок\n"
        "├—🔒 Надежное шифрование\n"
        "└—📱 Все устройства\n\n"
        "✨ ДОПОЛНИТЕЛЬНО:\n"
        "├—↩️ Гарантия возврата 30 дней\n"
        "├—🎁 Бонусная программа\n"
        "└—📞 Поддержка 24/7: @blackvpn_support\n\n"
        "🛡️ Безопасность и скорость в одном пакете!\n\n"
        "🚀 Выберите тариф VPN\n\n"
        "🔒 Безопасность и скорость на любой срок",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def process_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Проверяем наличие активной подписки
    active_subscription = db.get_active_subscription(user_id)
    if active_subscription:
        await query.answer("❌ У вас уже есть активная подписка!", show_alert=True)
        await query.message.reply_text(
            "Дождитесь окончания текущей подписки или обратитесь к администратору для её продления."
        )
        return MAIN_MENU
    
    # Получаем выбранный тариф
    tariff_id = query.data.replace("tariff_", "")  # Например, из "tariff_1_month" получаем "1_month"
    if tariff_id not in TARIFFS:
        await query.answer("❌ Неверный тариф", show_alert=True)
        return MAIN_MENU
        
    tariff = TARIFFS[tariff_id]
    
    # Создаем запись о платеже в базе данных
    db.add_pending_transaction(
        user_id=user_id,
        amount=tariff['price'],
        transaction_type=tariff_id,
        username=query.from_user.username
    )
    
    # Отправляем инструкции по оплате
    await query.message.reply_text(
        f"💳 Оплата {tariff['name']}\n\n"
        f"Сумма к оплате: {tariff['price']}₽\n\n"
        "💸 Для оплаты переведите указанную сумму на карту:\n"
        f"`{os.getenv('PAYMENT_CARD')}`\n\n"
        "❗️ После оплаты отправьте скриншот чека",
        parse_mode='Markdown'
    )
    
    await query.answer()
    return PAYMENT_CONFIRMATION

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "🔙 вернуться в меню":
        return await back_to_menu(update, context)
    
    # Если пользователь отправил фото
    if message.photo:
        # Получаем последний платеж пользователя
        payment = db.get_last_pending_transaction(user_id)
        if not payment:
            await message.reply_text(
                "❌ Не найден активный платёж.\n"
                "Пожалуйста, начните процесс оплаты заново."
            )
            return MAIN_MENU

        # Сохраняем чек для проверки админом
        await message.reply_text(
            "✅ Ваш чек принят и отправлен на проверку администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        
        # Получаем file_id фотографии
        photo_file_id = message.photo[-1].file_id
        
        # Создаем клавиатуру для админа
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"admin_confirm_{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data=f"admin_reject_{payment['id']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Уведомляем админов
        admin_ids = os.getenv('ADMIN_IDS', '').split(',')
        for admin_id in admin_ids:
            try:
                admin_id = admin_id.strip()  # Убираем лишние пробелы
                if admin_id:  # Проверяем, что ID не пустой
                    # Отправляем фото чека
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=(
                            f"💰 Новый платёж\n\n"
                            f"От: @{message.from_user.username}\n"
                            f"ID: {user_id}\n"
                            f"Тариф: {TARIFFS[payment['transaction_type']]['name']}\n"
                            f"Сумма: {payment['amount']}₽\n"
                            f"ID платежа: {payment['id']}"
                        ),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
        
        return MAIN_MENU
    
    # Если пользователь отправил что-то кроме фото
    await message.reply_text(
        "❌ Пожалуйста, отправьте скриншот чека об оплате."
    )
    return PAYMENT_CONFIRMATION

async def show_referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_referral_stats(user_id)
    user_data = db.get_user(user_id)
    current_balance = user_data.get('balance', 0) if user_data else 0
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"
    
    message = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте 50% от их покупок!\n\n"
        f"👥 Ваши рефералы: {stats['referral_count']}\n"
        f"💰 Заработано: {stats['total_earnings']} ₽\n"
        f"💳 Текущий баланс: {current_balance} ₽\n\n"
        "🔗 Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        "Отправьте эту ссылку друзьям, и когда они совершат покупку, "
        "вы автоматически получите 50% от суммы на свой баланс!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("💰 Финансы", callback_data="admin_finances")]
    ]
    
    await update.message.reply_text(
        "⚙️ Админ-панель\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расширенную статистику админ-панели"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    active_subscriptions = db.get_active_subscriptions_count()
    total_revenue = db.get_total_revenue()
    new_users_today = db.get_new_users_count_today()
    
    stats_text = (
        "📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📅 Новых за сегодня: {new_users_today}\n"
        f"✨ Активных подписок: {active_subscriptions}\n"
        f"💰 Общий доход: {total_revenue}₽\n\n"
        "📈 *Статистика по тарифам:*\n"
    )
    
    # Добавляем статистику по каждому тарифу
    for tariff_id, tariff_data in TARIFFS.items():
        count = db.get_subscriptions_count_by_tariff(tariff_id)
        stats_text += f"- {tariff_data['name']}: {count} подписок\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("« Назад", callback_data="admin_back")]
    ]
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def setup_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    os_type, client_id = query.data.split('_')[0:2]
    
    instructions = {
        "ios": (
            "📱 Настройка VPN на iOS:\n\n"
            "1. Установка приложения:\n▫️ Скачайте Hiddify из App Store: https://apps.apple.com/app/hiddify/id6451357878\n\n"
            "2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию\n▫️ Нажмите 'Start' для подключения\n\n"
            "3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте переключатель в приложении"
        ),
        "android": (
            "🤖 Настройка VPN на Android:\n\n"
            "1. Установка приложения:\n▫️ Скачайте Hiddify из Google Play: https://play.google.com/store/apps/details?id=app.hiddify.com\n\n"
            "2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в нижнем правом углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию\n▫️ Нажмите на кнопку подключения\n\n"
            "3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте кнопку в приложении"
        ),
        "macos": (
            "🖥 Настройка VPN на macOS:\n\n"
            "1. Установка приложения:\n▫️ Скачайте Hiddify для macOS: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-macos-universal.zip\n\n"
            "2. Настройка:\n▫️ Распакуйте и установите приложение\n▫️ Откройте Hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию\n\n"
            "3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в строке меню"
        ),
        "windows": (
            "💻 Настройка VPN на Windows:\n\n"
            "1. Установка приложения:\n▫️ Скачайте Hiddify для Windows: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-windows-x64.zip\n\n"
            "2. Настройка:\n▫️ Распакуйте архив\n▫️ Запустите Hiddify.exe\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию\n\n"
            "3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в трее"
        ),
        "linux": (
            "🐧 Настройка VPN на Linux:\n\n"
            "1. Установка приложения:\n▫️ Скачайте Hiddify для Linux: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-linux-x64.zip\n\n"
            "2. Настройка:\n▫️ Распакуйте архив:\n   unzip hiddify-linux-x64.zip\n▫️ Сделайте файл исполняемым:\n   chmod +x hiddify\n▫️ Запустите приложение:\n   ./hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию\n\n"
            "3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в системном трее"
        )
    }
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад к выбору ОС", callback_data="instructions")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=instructions.get(os_type, "Инструкция временно недоступна"),
        reply_markup=reply_markup
    )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    text = "🏠 Главное меню"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text)
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    return MAIN_MENU

async def show_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions_text = (
        "📋 Инструкция по использованию VPN\n\n"
        "1️⃣ Выберите и оплатите подходящий тариф\n"
        "2️⃣ Дождитесь подтверждения оплаты\n"
        "3️⃣ Получите конфигурацию VPN\n"
        "4️⃣ Установите приложение для вашей системы\n"
        "5️⃣ Импортируйте полученную конфигурацию\n\n"
        "❓ Если у вас возникли вопросы, обратитесь в поддержку"
    )
    
    keyboard = [[InlineKeyboardButton("🔑 Купить VPN", callback_data="show_tariffs")]]
    await update.message.reply_text(
        instructions_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def instructions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 iOS - для iPhone и iPad", callback_data="ios_instructions")],
        [InlineKeyboardButton("🤖 Android - для смартфонов", callback_data="android_instructions")],
        [InlineKeyboardButton("🍎 macOS - для компьютеров Apple", callback_data="macos_instructions")],
        [InlineKeyboardButton("💻 Windows - для ПК", callback_data="windows_instructions")],
        [InlineKeyboardButton("🐧 Linux - для Ubuntu/Debian", callback_data="linux_instructions")],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📚 Выберите вашу операционную систему для получения подробной инструкции:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)

async def os_instructions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для инструкций по настройке VPN на разных ОС"""
    query = update.callback_query
    await query.answer()
    
    os_type = query.data.replace('setup_', '')
    
    # Получаем активную подписку пользователя
    subscription = db.get_active_subscription(query.from_user.id)
    if not subscription:
        await query.message.edit_text(
            "❌ У вас нет активной подписки. Пожалуйста, сначала приобретите подписку.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]])
        )
        return
    
    # Получаем VPN конфигурацию
    try:
        vpn_config = subscription['vpn_config']
    except KeyError:
        await query.message.edit_text(
            "❌ Ошибка при получении VPN конфигурации. Пожалуйста, обратитесь в поддержку.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]])
        )
        return
        
    instructions = {
        'ios': f"🍎 Инструкция для iOS:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify из App Store: https://apps.apple.com/app/hiddify/id6451357878\n\n2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{vpn_config}`\n\n▫️ Нажмите 'Start' для подключения\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте переключатель в приложении",
        'android': f"🤖 Инструкция для Android:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify из Google Play: https://play.google.com/store/apps/details?id=app.hiddify.com\n\n2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в нижнем правом углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{vpn_config}`\n\n▫️ Нажмите на кнопку подключения\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте кнопку в приложении",
        'macos': f"🖥 Настройка VPN на macOS:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для macOS: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-macos-universal.zip\n\n2. Настройка:\n▫️ Распакуйте и установите приложение\n▫️ Откройте Hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{vpn_config}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в строке меню",
        'windows': f"💻 Настройка VPN на Windows:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для Windows: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-windows-x64.zip\n\n2. Настройка:\n▫️ Распакуйте архив\n▫️ Запустите Hiddify.exe\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{vpn_config}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в трее",
        'linux': f"🐧 Настройка VPN на Linux:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для Linux: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-linux-x64.zip\n\n2. Настройка:\n▫️ Распакуйте архив:\n   unzip hiddify-linux-x64.zip\n▫️ Сделайте файл исполняемым:\n   chmod +x hiddify\n▫️ Запустите приложение:\n   ./hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{vpn_config}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в системном трее"
    }

    instruction_text = instructions.get(os_type, "❌ Неизвестная операционная система")
    keyboard = [[InlineKeyboardButton("⬅️ Назад к выбору ОС", callback_data="instructions")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        instruction_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def get_download_link(os_type):
    links = {
        'ios': "https://apps.apple.com/app/hiddify/id6451357878",
        'android': "https://play.google.com/store/apps/details?id=app.hiddify.com",
        'macos': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-macos-universal.zip",
        'windows': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-windows-x64.zip",
        'linux': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-linux-x64.zip"
    }
    return links.get(os_type, "https://github.com/hiddify/hiddify-next/releases")

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что команда пришла от владельца бота
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.message.from_user.id) != owner_id:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return

    # Получаем ID пользователя из аргументов команды
    if not context.args:
        await update.message.reply_text("❌ Укажите ID пользователя")
        return

    try:
        user_id = int(context.args[0])
        db.set_admin(user_id, True)
        await update.message.reply_text(f"✅ Пользователь {user_id} назначен администратором")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")
    except Exception as e:
        print(f"Ошибка при назначении администратора: {e}")
        await update.message.reply_text("❌ Произошла ошибка")

async def process_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    print(f"Processing admin action from user {user_id}")
    print(f"Callback data: {query.data}")
    
    # Проверяем, является ли пользователь администратором
    if not db.is_admin(user_id):
        print(f"User {user_id} is not admin")
        await query.answer("❌ У вас нет прав администратора", show_alert=True)
        return MAIN_MENU
    
    print(f"User {user_id} is admin, processing action")
    
    try:
        # Получаем данные из callback_query
        action_type, payment_id = query.data.split('_', 2)[1:]  # admin_confirm_ID -> ['admin', 'confirm', 'ID']
        action = "confirm" if action_type == "confirm" else "reject"
        
        print(f"Action: {action}, Payment ID: {payment_id}")
        
        # Получаем данные о платеже
        payment = db.get_transaction(payment_id)
        print(f"Payment data: {payment}")
        
        if not payment:
            print(f"Payment {payment_id} not found")
            await query.answer("❌ Платёж не найден", show_alert=True)
            return MAIN_MENU
        
        if action == "confirm":
            print("Confirming payment")
            try:
                # Создаем VPN-клиента
                vpn = VPNManager()
                inbounds = vpn.get_inbounds()
                print(f"Available inbounds: {inbounds}")
                
                if not inbounds:
                    print("No inbounds available, creating new one...")
                    inbound_response = vpn.create_inbound()
                    if not inbound_response.get('success'):
                        raise Exception("Failed to create inbound")
                    inbounds = vpn.get_inbounds()
                    if not inbounds:
                        raise Exception("No inbounds available after creation")
                
                inbound = inbounds[0]
                client = vpn.create_client(inbound['id'])
                print(f"Created client: {client}")
                
                if not client:
                    raise Exception("Failed to create client")
                
                # Генерируем ссылку для подключения
                vpn_link = vpn.generate_vless_link(client)
                print(f"Generated VPN link: {vpn_link}")
                
                if not vpn_link:
                    raise Exception("Failed to generate VPN link")
                
                # Обрабатываем реферальное начисление
                user_data = db.get_user(payment['user_id'])
                if user_data and user_data['referrer_id']:
                    print(f"Processing referral commission for referrer {user_data['referrer_id']}")
                    commission = db.add_referral_transaction(
                        user_data['referrer_id'],
                        payment['user_id'],
                        payment['amount']
                    )
                    # Уведомляем реферера о начислении
                    try:
                        await context.bot.send_message(
                            chat_id=user_data['referrer_id'],
                            text=f"🎉 Вам начислено {commission}₽ за покупку вашего реферала!"
                        )
                    except Exception as e:
                        print(f"Failed to notify referrer: {e}")
                
                # Обновляем статус транзакции
                db.update_transaction_status(payment_id, 'completed')
                
                # Сохраняем VPN-конфигурацию
                db.add_subscription(
                    user_id=payment['user_id'],
                    subscription_type=payment['transaction_type'],
                    vpn_config=vpn_link,
                    client_id=client['id'],
                    inbound_id=inbound['id']
                )
                
                # Уведомляем пользователя
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text=(
                        "✅ Ваш платёж подтверждён!\n\n"
                        "🔗 Вот ваша ссылка для подключения:\n"
                        f"`{vpn_link}`\n\n"
                        "📱 Выберите вашу операционную систему для получения инструкций по настройке:"
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📱 iOS", callback_data="ios_instructions"),
                            InlineKeyboardButton("🤖 Android", callback_data="android_instructions")
                        ],
                        [
                            InlineKeyboardButton("🖥 Windows", callback_data="windows_instructions"),
                            InlineKeyboardButton("🍎 macOS", callback_data="macos_instructions")
                        ],
                        [InlineKeyboardButton("🐧 Linux", callback_data="linux_instructions")]
                    ])
                )
                
                # Обновляем сообщение с чеком
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n✅ Платёж подтверждён",
                    reply_markup=None
                )
                
            except Exception as e:
                print(f"Error while confirming payment: {e}")
                await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
                return MAIN_MENU
            
        else:  # reject
            print("Rejecting payment")
            # Обновляем статус транзакции
            db.update_transaction_status(payment_id, 'rejected')
            
            # Уведомляем пользователя
            await context.bot.send_message(
                chat_id=payment['user_id'],
                text="❌ Ваш платёж отклонён. Пожалуйста, свяжитесь с администратором."
            )
            
            # Обновляем сообщение с чеком
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Платёж отклонён",
                reply_markup=None
            )
        
        await query.answer()
        return MAIN_MENU
        
    except Exception as e:
        print(f"Error in process_admin_action: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)
        return MAIN_MENU

async def show_subscriptions_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню управления подписками"""
    query = update.callback_query
    await query.answer()
    
    # Получаем все активные подписки
    subscriptions = db.get_all_active_subscriptions()
    
    if not subscriptions:
        await query.message.edit_text(
            "👥 *Управление подписками*\n\n"
            "На данный момент нет активных подписок.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="admin_back")
            ]])
        )
        return
    
    text = "👥 *Управление подписками*\n\n"
    keyboard = []
    
    # Маппинг старых тарифов на новые
    tariff_mapping = {
        "1_month": "1_99",
        "2_months": "2_179",
        "6_months": "6_499",
        "12_months": "12_899"
    }
    
    for sub in subscriptions:
        username = sub['username'] or f"ID: {sub['user_id']}"
        end_date = datetime.fromisoformat(sub['end_date']).strftime("%d.%m.%Y")
        
        # Используем маппинг для конвертации старых тарифов в новые
        tariff_type = tariff_mapping.get(sub['subscription_type'], sub['subscription_type'])
        try:
            tariff_name = TARIFFS[tariff_type]['name']
        except KeyError:
            tariff_name = "Неизвестный тариф"
        
        text += (
            f"👤 *{username}*\n"
            f"📅 До: {end_date}\n"
            f"📦 Тариф: {tariff_name}\n"
            "➖➖➖➖➖➖➖➖\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Удалить {username}",
                callback_data=f"admin_delete_sub_{sub['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_back")])
    
    await query.message.edit_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_subscription_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление подписки администратором"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID подписки из callback_data
    subscription_id = query.data.split('_')[-1]
    
    try:
        # Получаем информацию о подписке
        subscription = db.get_subscription_by_id(subscription_id)
        if not subscription:
            await query.message.edit_text(
                "❌ Подписка не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="admin_subscriptions")
                ]])
            )
            return
        
        # Выводим список доступных inbounds
        vpn_manager = VPNManager()
        inbounds = vpn_manager.get_inbounds()
        print("Available inbounds:", json.dumps(inbounds, indent=2))
        
        # Удаляем VPN клиента только если есть client_id и inbound_id
        if subscription['client_id'] and subscription.get('inbound_id'):
            try:
                vpn_manager.delete_client(subscription['inbound_id'], subscription['client_id'])
            except Exception as e:
                print(f"Error deleting VPN client: {e}")
                # Продолжаем выполнение даже при ошибке удаления VPN клиента
        
        # Деактивируем подписку в базе данных
        db.deactivate_subscription(subscription_id)
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=subscription['user_id'],
                text="❌ Ваша подписка была отменена администратором."
            )
        except Exception as e:
            print(f"Error notifying user: {e}")
        
        # Возвращаемся к списку подписок
        await show_subscriptions_management(update, context)
        
    except Exception as e:
        print(f"Error deleting subscription: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при удалении подписки",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="admin_subscriptions")
            ]])
        )

async def delete_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if not db.is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return
    
    # Проверяем, указан ли ID пользователя
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите ID пользователя\n"
            "Пример: /delete_subscription 123456789"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        print(f"Attempting to delete subscription for user {target_user_id}")
        
        # Проверяем доступные инбаунды
        vpn_manager = VPNManager()
        inbounds = vpn_manager.get_inbounds()
        print("Available inbounds:", json.dumps(inbounds, indent=2))
        
        # Удаляем подписку
        subscription = db.delete_subscription(target_user_id)
        print(f"Subscription data: {subscription}")
        print(f"Subscription keys: {dict(subscription).keys()}")
        print(f"Raw inbound_id value: {subscription['inbound_id']}")
        
        if subscription:
            # Проверяем данные подписки
            print("VPN config type:", type(subscription['vpn_config']))
            print("VPN config value:", subscription['vpn_config'])
            print("Client ID:", subscription['client_id'])
            
            if not subscription['vpn_config']:
                await update.message.reply_text(
                    f"⚠️ Подписка пользователя {target_user_id} деактивирована в базе данных. "
                    "VPN конфигурация отсутствует."
                )
                return
                
            # Удаляем клиента из VPN-сервера
            try:
                vpn_manager = VPNManager()
                client_id = subscription['client_id']
                inbound_id = inbounds[0]['id'] if inbounds else None  # Берем ID первого inbound'а
                
                if not client_id:
                    raise Exception("ID клиента отсутствует в данных подписки")
                
                if not inbound_id:
                    raise Exception("ID inbound отсутствует в данных подписки")
                
                print(f"Client ID: {client_id}")
                print(f"Inbound ID: {inbound_id}")
                
                # Удаляем клиента
                if vpn_manager.delete_client(inbound_id, client_id):
                    await update.message.reply_text(
                        f"✅ Подписка пользователя {target_user_id} успешно удалена"
                    )
                    
                    # Уведомляем пользователя
                    try:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text="❌ Ваша подписка была деактивирована администратором"
                        )
                    except Exception as e:
                        print(f"Failed to notify user about subscription deletion: {e}")
                    
                    return
                    
            except Exception as e:
                error_msg = str(e)
                print(f"Error removing VPN client: {error_msg}")
                await update.message.reply_text(
                    f"⚠️ Подписка пользователя {target_user_id} деактивирована в базе данных, "
                    f"но возникла ошибка при удалении с VPN-сервера:\n{error_msg}"
                )
        else:
            await update.message.reply_text(
                f"❌ Активная подписка для пользователя {target_user_id} не найдена"
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректный ID пользователя"
        )
    except Exception as e:
        error_msg = str(e)
        print(f"Error in delete_subscription: {error_msg}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при удалении подписки: {error_msg}"
        )

async def subtract_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вычитает указанную сумму с баланса пользователя"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if not db.is_admin(user_id):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды"
        )
        return
        
    # Проверяем аргументы команды
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды\n"
            "Используйте: /subtract_balance <user_id> <amount>\n"
            "Пример: /subtract_balance 123456789 100"
        )
        return
        
    try:
        target_user_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительным числом")
            return
            
        # Вычитаем с баланса
        try:
            new_balance = db.subtract_from_balance(target_user_id, amount)
            
            # Отправляем сообщение администратору
            await update.message.reply_text(
                f"✅ С баланса пользователя {target_user_id} списано {amount}₽\n"
                f"Новый баланс: {new_balance}₽"
            )
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💰 С вашего баланса списано {amount}₽\n"
                         f"Текущий баланс: {new_balance}₽"
                )
            except Exception as e:
                print(f"Failed to notify user about balance subtraction: {e}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ID пользователя или суммы\n"
            "ID должен быть целым числом, а сумма - положительным числом"
        )

async def os_instructions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    os_type = query.data.replace('_instructions', '')
    
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" not in str(e):
            raise e
        pass

    # Получаем активную подписку пользователя
    subscription = db.get_active_subscription(query.from_user.id)
    if not subscription:
        await query.edit_message_text(
            "❌ У вас нет активной подписки. Пожалуйста, сначала приобретите подписку.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]])
        )
        return

    # Получаем VPN конфигурацию
    try:
        if not subscription['vpn_config']:
            print(f"VPN config is None for user {query.from_user.id}")
            raise ValueError("VPN configuration is missing")
            
        vpn_config = subscription['vpn_config']
        config_link = None
        
        # Пробуем распарсить как JSON
        try:
            if isinstance(vpn_config, str):
                vpn_config = json.loads(vpn_config)
            if isinstance(vpn_config, dict):
                config_link = vpn_config.get('link')
            if not config_link and isinstance(vpn_config, str):
                if vpn_config.startswith('vless://') or vpn_config.startswith('vmess://'):
                    config_link = vpn_config
        except json.JSONDecodeError:
            if isinstance(vpn_config, str) and (vpn_config.startswith('vless://') or vpn_config.startswith('vmess://')):
                config_link = vpn_config
            else:
                print(f"Failed to parse VPN config for user {query.from_user.id}")
                print(f"Raw config: {vpn_config}")
                raise ValueError("Invalid VPN configuration format")
        
        if not config_link:
            print(f"VPN config link is missing for user {query.from_user.id}")
            print(f"Processed config: {vpn_config}")
            raise ValueError("VPN configuration link is missing")
            
    except Exception as e:
        print(f"Error processing VPN config for user {query.from_user.id}: {str(e)}")
        subscription_dict = dict(zip(subscription.keys(), subscription))
        print(f"Subscription data: {subscription_dict}")
        await query.edit_message_text(
            "❌ Ошибка при получении VPN конфигурации. Пожалуйста, обратитесь в поддержку.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]])
        )
        return

    instructions = {
        'ios': f"🍎 Инструкция для iOS:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify из App Store: https://apps.apple.com/app/hiddify/id6451357878\n\n2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{config_link}`\n\n▫️ Нажмите 'Start' для подключения\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте переключатель в приложении",
        'android': f"🤖 Инструкция для Android:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify из Google Play: https://play.google.com/store/apps/details?id=app.hiddify.com\n\n2. Настройка:\n▫️ Откройте приложение\n▫️ Нажмите на '+' в нижнем правом углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{config_link}`\n\n▫️ Нажмите на кнопку подключения\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Для включения/выключения используйте кнопку в приложении",
        'macos': f"🖥 Настройка VPN на macOS:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для macOS: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-macos-universal.zip\n\n2. Настройка:\n▫️ Распакуйте и установите приложение\n▫️ Откройте Hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{config_link}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в строке меню",
        'windows': f"💻 Настройка VPN на Windows:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для Windows: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-windows-x64.zip\n\n2. Настройка:\n▫️ Распакуйте архив\n▫️ Запустите Hiddify.exe\n▫️ Нажмите на '+' в правом верхнем углу\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{config_link}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в трее",
        'linux': f"🐧 Настройка VPN на Linux:\n\n1. Установка приложения:\n▫️ Скачайте Hiddify для Linux: https://github.com/hiddify/hiddify-next/releases\n▫️ Выберите версию hiddify-linux-x64.zip\n\n2. Настройка:\n▫️ Распакуйте архив:\n   unzip hiddify-linux-x64.zip\n▫️ Сделайте файл исполняемым:\n   chmod +x hiddify\n▫️ Запустите приложение:\n   ./hiddify\n▫️ Нажмите на '+' в верхней панели\n▫️ Выберите 'Import from Clipboard'\n▫️ Вставьте скопированную конфигурацию:\n\n`{config_link}`\n\n3. Готово!\n▫️ Теперь вы можете пользоваться VPN\n▫️ Управление через значок в системном трее"
    }

    instruction_text = instructions.get(os_type, "❌ Неизвестная операционная система")
    keyboard = [[InlineKeyboardButton("⬅️ Назад к выбору ОС", callback_data="instructions")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        instruction_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def get_download_link(os_type):
    links = {
        'ios': "https://apps.apple.com/app/hiddify/id6451357878",
        'android': "https://play.google.com/store/apps/details?id=app.hiddify.com",
        'macos': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-macos-universal.zip",
        'windows': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-windows-x64.zip",
        'linux': "https://github.com/hiddify/hiddify-next/releases/latest/download/hiddify-linux-x64.zip"
    }
    return links.get(os_type, "https://github.com/hiddify/hiddify-next/releases")

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что команда пришла от владельца бота
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.message.from_user.id) != owner_id:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
        return

    # Получаем ID пользователя из аргументов команды
    if not context.args:
        await update.message.reply_text("❌ Укажите ID пользователя")
        return

    try:
        user_id = int(context.args[0])
        db.set_admin(user_id, True)
        await update.message.reply_text(f"✅ Пользователь {user_id} назначен администратором")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")
    except Exception as e:
        print(f"Ошибка при назначении администратора: {e}")
        await update.message.reply_text("❌ Произошла ошибка")

async def process_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    print(f"Processing admin action from user {user_id}")
    print(f"Callback data: {query.data}")
    
    # Проверяем, является ли пользователь администратором
    if not db.is_admin(user_id):
        print(f"User {user_id} is not admin")
        await query.answer("❌ У вас нет прав администратора", show_alert=True)
        return MAIN_MENU
    
    print(f"User {user_id} is admin, processing action")
    
    try:
        # Получаем данные из callback_query
        action_type, payment_id = query.data.split('_', 2)[1:]  # admin_confirm_ID -> ['admin', 'confirm', 'ID']
        action = "confirm" if action_type == "confirm" else "reject"
        
        print(f"Action: {action}, Payment ID: {payment_id}")
        
        # Получаем данные о платеже
        payment = db.get_transaction(payment_id)
        print(f"Payment data: {payment}")
        
        if not payment:
            print(f"Payment {payment_id} not found")
            await query.answer("❌ Платёж не найден", show_alert=True)
            return MAIN_MENU
        
        if action == "confirm":
            print("Confirming payment")
            try:
                # Создаем VPN-клиента
                vpn = VPNManager()
                inbounds = vpn.get_inbounds()
                print(f"Available inbounds: {inbounds}")
                
                if not inbounds:
                    print("No inbounds available, creating new one...")
                    inbound_response = vpn.create_inbound()
                    if not inbound_response.get('success'):
                        raise Exception("Failed to create inbound")
                    inbounds = vpn.get_inbounds()
                    if not inbounds:
                        raise Exception("No inbounds available after creation")
                
                inbound = inbounds[0]
                client = vpn.create_client(inbound['id'])
                print(f"Created client: {client}")
                
                if not client:
                    raise Exception("Failed to create client")
                
                # Генерируем ссылку для подключения
                vpn_link = vpn.generate_vless_link(client)
                print(f"Generated VPN link: {vpn_link}")
                
                if not vpn_link:
                    raise Exception("Failed to generate VPN link")
                
                # Обрабатываем реферальное начисление
                user_data = db.get_user(payment['user_id'])
                if user_data and user_data['referrer_id']:
                    print(f"Processing referral commission for referrer {user_data['referrer_id']}")
                    commission = db.add_referral_transaction(
                        user_data['referrer_id'],
                        payment['user_id'],
                        payment['amount']
                    )
                    # Уведомляем реферера о начислении
                    try:
                        await context.bot.send_message(
                            chat_id=user_data['referrer_id'],
                            text=f"🎉 Вам начислено {commission}₽ за покупку вашего реферала!"
                        )
                    except Exception as e:
                        print(f"Failed to notify referrer: {e}")
                
                # Обновляем статус транзакции
                db.update_transaction_status(payment_id, 'completed')
                
                # Сохраняем VPN-конфигурацию
                db.add_subscription(
                    user_id=payment['user_id'],
                    subscription_type=payment['transaction_type'],
                    vpn_config=vpn_link,
                    client_id=client['id'],
                    inbound_id=inbound['id']
                )
                
                # Уведомляем пользователя
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text=(
                        "✅ Ваш платёж подтверждён!\n\n"
                        "🔗 Вот ваша ссылка для подключения:\n"
                        f"`{vpn_link}`\n\n"
                        "📱 Выберите вашу операционную систему для получения инструкций по настройке:"
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📱 iOS", callback_data="ios_instructions"),
                            InlineKeyboardButton("🤖 Android", callback_data="android_instructions")
                        ],
                        [
                            InlineKeyboardButton("🖥 Windows", callback_data="windows_instructions"),
                            InlineKeyboardButton("🍎 macOS", callback_data="macos_instructions")
                        ],
                        [InlineKeyboardButton("🐧 Linux", callback_data="linux_instructions")]
                    ])
                )
                
                # Обновляем сообщение с чеком
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n✅ Платёж подтверждён",
                    reply_markup=None
                )
                
            except Exception as e:
                print(f"Error while confirming payment: {e}")
                await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
                return MAIN_MENU
            
        else:  # reject
            print("Rejecting payment")
            # Обновляем статус транзакции
            db.update_transaction_status(payment_id, 'rejected')
            
            # Уведомляем пользователя
            await context.bot.send_message(
                chat_id=payment['user_id'],
                text="❌ Ваш платёж отклонён. Пожалуйста, свяжитесь с администратором."
            )
            
            # Обновляем сообщение с чеком
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Платёж отклонён",
                reply_markup=None
            )
        
        await query.answer()
        return MAIN_MENU
        
    except Exception as e:
        print(f"Error in process_admin_action: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)
        return MAIN_MENU

async def show_subscriptions_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню управления подписками"""
    query = update.callback_query
    await query.answer()
    
    # Получаем все активные подписки
    subscriptions = db.get_all_active_subscriptions()
    
    if not subscriptions:
        await query.message.edit_text(
            "👥 *Управление подписками*\n\n"
            "На данный момент нет активных подписок.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="admin_back")
            ]])
        )
        return
    
    text = "👥 *Управление подписками*\n\n"
    keyboard = []
    
    # Маппинг старых тарифов на новые
    tariff_mapping = {
        "1_month": "1_99",
        "2_months": "2_179",
        "6_months": "6_499",
        "12_months": "12_899"
    }
    
    for sub in subscriptions:
        username = sub['username'] or f"ID: {sub['user_id']}"
        end_date = datetime.fromisoformat(sub['end_date']).strftime("%d.%m.%Y")
        
        # Используем маппинг для конвертации старых тарифов в новые
        tariff_type = tariff_mapping.get(sub['subscription_type'], sub['subscription_type'])
        try:
            tariff_name = TARIFFS[tariff_type]['name']
        except KeyError:
            tariff_name = "Неизвестный тариф"
        
        text += (
            f"👤 *{username}*\n"
            f"📅 До: {end_date}\n"
            f"📦 Тариф: {tariff_name}\n"
            "➖➖➖➖➖➖➖➖\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Удалить {username}",
                callback_data=f"admin_delete_sub_{sub['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_back")])
    
    await query.message.edit_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_subscription_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление подписки администратором"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID подписки из callback_data
    subscription_id = query.data.split('_')[-1]
    
    try:
        # Получаем информацию о подписке
        subscription = db.get_subscription_by_id(subscription_id)
        if not subscription:
            await query.message.edit_text(
                "❌ Подписка не найдена",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data="admin_subscriptions")
                ]])
            )
            return
        
        # Выводим список доступных inbounds
        vpn_manager = VPNManager()
        inbounds = vpn_manager.get_inbounds()
        print("Available inbounds:", json.dumps(inbounds, indent=2))
        
        # Удаляем VPN клиента только если есть client_id и inbound_id
        if subscription['client_id'] and subscription.get('inbound_id'):
            try:
                vpn_manager.delete_client(subscription['inbound_id'], subscription['client_id'])
            except Exception as e:
                print(f"Error deleting VPN client: {e}")
                # Продолжаем выполнение даже при ошибке удаления VPN клиента
        
        # Деактивируем подписку в базе данных
        db.deactivate_subscription(subscription_id)
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=subscription['user_id'],
                text="❌ Ваша подписка была отменена администратором."
            )
        except Exception as e:
            print(f"Error notifying user: {e}")
        
        # Возвращаемся к списку подписок
        await show_subscriptions_management(update, context)
        
    except Exception as e:
        print(f"Error deleting subscription: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при удалении подписки",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="admin_subscriptions")
            ]])
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "Выберите действие из меню ниже:",
        reply_markup=reply_markup
    )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data in ("renew_vpn", "buy_vpn"):
        # Получаем текущую подписку пользователя
        subscription = db.get_active_subscription(user_id)
        if subscription:
            key = subscription['vpn_config']
            expires = subscription['end_date']
            from datetime import datetime
            try:
                days_left = (datetime.fromisoformat(expires) - datetime.now()).days
                expires_str = f"{days_left} дня" if days_left > 0 else "сегодня"
            except Exception:
                expires_str = expires
            sub_text = f"🔑 {key} (⏳ {expires_str})"
        else:
            sub_text = "У вас нет активных подписок."
        keyboard = [
            [InlineKeyboardButton(sub_text, callback_data="current_sub")],
            [InlineKeyboardButton("➕ Добавить новую подписку", callback_data="add_sub")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption="Выберите подписку для продления или купите новую",
            reply_markup=reply_markup
        )
        await query.answer()
        return
    if data == "my_subs":
        # Получаем все подписки пользователя
        subscriptions = db.get_user_subscriptions(user_id)
        if not subscriptions:
            await query.answer("У вас нет подписок.")
            await query.message.reply_text("У вас нет активных подписок.")
            return

        # Формируем красивый список
        caption = "🔑 <b>Список ваших подписок:</b>\n\n"
        buttons = []
        for sub in subscriptions:
            # Имя подписки: если есть email или user_X, иначе первые 8 символов ключа
            name = sub.get('name') or sub.get('vpn_config') or f"user_{sub.get('client_id', '')[:8]}"
            # Если ключ vless://...#username, то вытащить username
            import re
            key = sub.get('vpn_config', '')
            username = None
            if key:
                m = re.search(r'#([\w\-@.]+)$', key)
                if m:
                    username = m.group(1)
                else:
                    m = re.search(r'email=([\w\-@.]+)', key)
                    if m:
                        username = m.group(1)
            if username:
                name = username
            end_date = sub.get('end_date', '')
            caption += f"│ <code>{name}</code> (до {end_date})\n"
            # Кнопка для просмотра подписки и переименования (заглушка)
            buttons.append([
                InlineKeyboardButton(f"🔑 {name}", callback_data=f"sub_{sub['id']}"),
                InlineKeyboardButton("✏️", callback_data=f"rename_{sub['id']}")
            ])
        caption += "\n<i>Нажмите на ✏️ чтобы переименовать подписку.</i>"

        # Кнопка личного кабинета
        buttons.append([InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")])

        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        await query.answer()
        return
    if data == "invite":
        user_id = query.from_user.id
        username = query.from_user.username or ""
        referral_link = f"https://t.me/{context.bot.username}?start=ref{user_id}"

        # Здесь можно получить статистику из базы, если реализовано
        total_invited = 0
        total_bonus = 0.0
        # Если есть функция db.get_referral_stats(user_id):
        if hasattr(db, 'get_referral_stats'):
            stats = db.get_referral_stats(user_id)
            total_invited = stats.get('referral_count', 0)
            total_bonus = stats.get('total_earnings', 0.0)
            # Можно добавить детализацию по уровням, если есть
            level_stats = stats.get('level_stats', {})
            if level_stats:
                details = "\n".join([f"{lvl} уровень: {cnt} чел." for lvl, cnt in level_stats.items()])
            else:
                details = "—"
        else:
            details = "—"

        text = (
            "👥 <b>Ваша реферальная ссылка:</b>\n\n"
            f"<a href=\"{referral_link}\">{referral_link}</a>\n\n"
            "🤝 <b>Приглашайте друзей и получайте крутые бонусы на каждом уровне!</b> 💰\n\n"
            "🏆 <b>Бонусы за приглашения:</b>\n"
            "<pre>"
            "1 уровень: 🌟 25% бонуса\n"
            "2 уровень: 🌟 10% бонуса\n"
            "3 уровень: 🌟 6% бонуса\n"
            "4 уровень: 🌟 5% бонуса\n"
            "5 уровень: 🌟 4% бонуса\n"
            "</pre>\n"
            "📊 <b>Статистика приглашений:</b>\n"
            f"👥 Всего приглашено: {total_invited} человек\n"
            "📝 Детальная статистика по уровням:\n"
            f"<pre>{details}</pre>\n"
            f"💰 <b>Общий бонус от рефералов: {total_bonus} RUB</b>"
        )

        keyboard = [
            [InlineKeyboardButton("📨 Пригласить", switch_inline_query="")],
            [InlineKeyboardButton("📷 Показать QR-код", callback_data="show_qr")],
            [InlineKeyboardButton("🏆 Top-5", callback_data="top5")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        await query.answer()
        return
    if data == "gift":
        text = "Дарите подарки и следите, чтобы они дошли до адресата! 🎄"
        keyboard = [
            [InlineKeyboardButton("🎁 Подарить подписку", callback_data="gift_give")],
            [InlineKeyboardButton("🎁 Мои подарки", callback_data="gift_my")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption=text,
            reply_markup=reply_markup
        )
        await query.answer()
        return
    if data == "about":
        text = (
            "📬 <b>Контакты:</b>\n\n"
            "<b>🔔 Подпишись на наш канал!</b>\n"
            "Следи за всеми новостями сервиса!\n"
            "Получай свежие обновления.\n"
            "Узнавай о новых тарифах.\n"
            "Участвуй в крутых акциях.\n"
            "Лови эксклюзивные подарки!\n\n"
            "<b>🛠 Техническая поддержка</b>\n"
            "Пиши нам без стеснения!\n"
            "Решаем любые вопросы по VPN.\n"
            "Помогаем с настройкой.\n"
            "Разбираемся с любыми сложностями!\n\n"
            "<i>Продолжая использование сервиса, вы соглашаетесь с правилами предоставления услуг:</i>\n"
            "<a href='https://t.me/your_channel'>Политика конфиденциальности</a>"
        )
        keyboard = [
            [InlineKeyboardButton("💬 Поддержка", url="https://t.me/your_support")],
            [InlineKeyboardButton("📢 Канал", url="https://t.me/your_channel")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        await query.answer()
        return
    if data == "balance":
        # Получаем баланс пользователя из базы (пример: db.get_user(user_id))
        user = db.get_user(user_id)
        balance = user.get('balance', 0) if user else 0

        text = (
            "Управление вашим балансом 💰\n\n"
            f"Ваш баланс: {balance}"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Пополнить баланс", callback_data="balance_topup")],
            [InlineKeyboardButton("📊 История пополнения", callback_data="balance_history")],
            [InlineKeyboardButton("🎫 Активировать купон", callback_data="balance_coupon")],
            [InlineKeyboardButton("👤 Личный кабинет", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo="https://i.imgur.com/your-image.png",  # замени на свою картинку
            caption=text,
            reply_markup=reply_markup
        )
        await query.answer()
        return
    # ... остальная логика для других кнопок ...

def main():
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("delete_subscription", delete_subscription))
    application.add_handler(CommandHandler("subtract_balance", subtract_balance))
    application.add_handler(CommandHandler("makeadmin", make_admin))
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(MessageHandler(filters.Regex("^Главное меню$"), show_main_menu))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^(buy_vpn|renew_vpn|my_subs|balance|invite|gift|about)$"))
    
    # Добавляем обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(process_tariff_selection, pattern="^tariff_"))
    application.add_handler(CallbackQueryHandler(show_admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(process_admin_action, pattern="^admin_(confirm|reject)_"))
    application.add_handler(CallbackQueryHandler(setup_instructions, pattern="^(ios|android|macos|windows)_setup_"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(instructions_handler, pattern="^instructions$"))
    application.add_handler(CallbackQueryHandler(os_instructions_handler, pattern="^(ios|android|macos|windows|linux)_instructions$"))
    application.add_handler(CallbackQueryHandler(setup_instructions, pattern="^setup_"))
    application.add_handler(CallbackQueryHandler(setup_instructions, pattern="^instructions_vpn$"))
    
    # Обработка платежей
    application.add_handler(MessageHandler(filters.PHOTO, check_payment))
    
    # Добавляем обработчик для рассылки
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern='^admin_broadcast$')],
        states={
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, preview_broadcast)],
            ADMIN_BROADCAST_PREVIEW: [
                CallbackQueryHandler(send_broadcast, pattern='^send_broadcast$'),
                CallbackQueryHandler(cancel_broadcast, pattern='^cancel_broadcast$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_broadcast)]
    )
    
    application.add_handler(broadcast_handler)
    
    # Добавляем обработчики для управления подписками
    application.add_handler(CallbackQueryHandler(
        show_subscriptions_management,
        pattern="^admin_subscriptions$"
    ))
    application.add_handler(CallbackQueryHandler(
        delete_subscription_admin,
        pattern="^admin_delete_sub_"
    ))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()

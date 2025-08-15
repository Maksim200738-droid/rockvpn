# VPN Telegram Bot

Полнофункциональный Telegram-бот для продажи VPN-подписок с системой реферальных программ, подарков и управления подписками.

## 🚀 Возможности

- 🔑 **Управление подписками** - создание, продление, удаление
- 💳 **Система тарифов** - гибкая настройка планов подписки
- 👥 **Реферальная программа** - многоуровневая система бонусов
- 🎁 **Система подарков** - создание и активация промо-кодов
- 👤 **Личный кабинет** - статистика и управление аккаунтом
- 📱 **QR-коды** - для удобного подключения устройств
- 💰 **Баланс пользователя** - внутренняя валюта
- 🔧 **Админ-панель** - управление пользователями и подписками

## 📋 Требования

- Python 3.8+
- SQLite3
- Telegram Bot Token (от @BotFather)

## 🔧 Установка

1. **Клонируйте репозиторий:**
```bash
git clone <your-repo-url>
cd vpn_bot_copy
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
cp .env.example .env
```

Отредактируйте файл `.env` и укажите ваши данные:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
CHANNEL_ID=@your_channel
```

4. **Запустите бота:**
```bash
python bot_main.py
```

## ⚙️ Настройка

### Получение токена бота

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в файл `.env`

### Настройка админов

Добавьте ваш Telegram ID в переменную `ADMIN_IDS` в файле `.env`:
```env
ADMIN_IDS=123456789,987654321
```

Чтобы узнать ваш ID, напишите [@userinfobot](https://t.me/userinfobot).

### Настройка канала (опционально)

Если вы хотите обязательную подписку на канал:
```env
CHANNEL_ID=@your_channel_username
```

## 🗄️ База данных

Бот автоматически создает SQLite базу данных `vpn_bot_copy.db` со следующими таблицами:

- `users` - пользователи
- `subscriptions` - подписки
- `tariffs` - тарифные планы
- `referral_bonuses` - реферальные бонусы
- `gifts` - подарочные коды

## 📱 Основные функции

### Главное меню
- 🔑 **Мои подписки** - просмотр активных подписок
- 💳 **Купить VPN** - выбор и покупка тарифов
- 👤 **Личный кабинет** - профиль пользователя
- 💝 **Пригласить** - реферальная программа
- 🎁 **Подарить** - создание подарочных кодов
- 💬 **О сервисе** - контакты и поддержка

### Тарифы по умолчанию
- 1 месяц — 179₽
- 3 месяца — 474₽
- 6 месяцев — 919₽
- 12 месяцев — 1549₽

### Реферальная система
- 1 уровень: 25% бонуса
- 2 уровень: 10% бонуса
- 3 уровень: 6% бонуса
- 4 уровень: 5% бонуса
- 5 уровень: 4% бонуса

## 🔌 Интеграции

### Платежные системы
Бот поддерживает интеграцию с различными платежными системами:
- YooKassa
- Telegram Payments
- Другие (требуется дополнительная настройка)

### VPN панели
Поддержка автоматической генерации ключей через:
- 3X-UI панель
- Outline VPN
- Другие (требуется дополнительная разработка)

## 🚀 Запуск в производстве

### Systemd сервис
Создайте файл `/etc/systemd/system/vpn-bot.service`:
```ini
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/vpn_bot_copy
ExecStart=/usr/bin/python3 /path/to/vpn_bot_copy/bot_main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vpn-bot
sudo systemctl start vpn-bot
```

### Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "bot_main.py"]
```

## 🛠️ Разработка

### Добавление новых тарифов
```python
db.add_tariff("Название", дни, цена, трафик_гб, "Описание")
```

### Создание подарочного кода
```python
gift_code = db.create_gift("тип_подписки", дни, создатель_id)
```

### Добавление бонуса пользователю
```python
db.update_user_balance(user_id, сумма)
```

## 📝 Логирование

Бот ведет подробные логи всех операций. Для настройки уровня логирования измените в коде:
```python
logging.basicConfig(level=logging.DEBUG)  # для отладки
logging.basicConfig(level=logging.INFO)   # для производства
```

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи бота
2. Убедитесь в правильности настройки `.env`
3. Проверьте права доступа к базе данных
4. Создайте Issue в репозитории

## 📄 Лицензия

MIT License

## 🤝 Вклад в проект

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📞 Контакты

- Telegram: [@your_username](https://t.me/your_username)
- Email: your.email@example.com

---

**Примечание:** Данный бот создан исключительно в образовательных целях. Убедитесь, что использование VPN-сервисов в вашей юрисдикции является законным.
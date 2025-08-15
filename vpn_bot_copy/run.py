#!/usr/bin/env python3
"""
Скрипт для запуска VPN Telegram бота
"""

import sys
import os
import subprocess

def check_requirements():
    """Проверка установленных зависимостей"""
    try:
        import telegram
        import sqlite3
        import dotenv
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False

def check_env_file():
    """Проверка файла .env"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден")
        print("📝 Скопируйте .env.example в .env и заполните настройки")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_bot_token_here':
        print("❌ BOT_TOKEN не настроен в файле .env")
        print("🤖 Получите токен от @BotFather и добавьте в .env")
        return False
    
    print("✅ Конфигурация в порядке")
    return True

def run_bot():
    """Запуск бота"""
    print("🚀 Запуск VPN бота...")
    try:
        from bot_main import main
        main()
    except KeyboardInterrupt:
        print("\n⛔ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False
    return True

if __name__ == "__main__":
    print("🎭 VPN Telegram Bot")
    print("=" * 30)
    
    # Проверки
    if not check_requirements():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    # Запуск
    run_bot()
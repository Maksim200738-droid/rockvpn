import logging
import os
import json
import requests
from datetime import datetime
from database import Database
from dotenv import load_dotenv
import time

load_dotenv()

class SubscriptionChecker:
    def __init__(self):
        self.db = Database()
        self.panel_url = os.getenv('PANEL_URL')
        self.username = os.getenv('PANEL_USERNAME')
        self.password = os.getenv('PANEL_PASSWORD')
        self.session = requests.Session()
        self.login()

    def login(self):
        try:
            login_data = {
                'username': self.username,
                'password': self.password
            }
            response = self.session.post(f"{self.panel_url}/login", json=login_data)
            if response.status_code != 200:
                print("❌ Ошибка входа в панель")
                raise Exception("Ошибка входа в панель")
            print("✅ Успешный вход в панель")
        except Exception as e:
            print(f"❌ Ошибка при входе: {str(e)}")
            raise

    def check_client_exists(self, client_id, inbound_id):
        """Проверяет существование клиента в панели"""
        try:
            response = self.session.get(f"{self.panel_url}/panel/api/inbounds/get/{inbound_id}")
            if response.status_code != 200:
                print(f"❌ Не удалось получить данные inbound {inbound_id}")
                return False

            inbound_data = response.json()['obj']
            settings = json.loads(inbound_data['settings'])
            
            exists = any(client.get('id') == client_id for client in settings['clients'])
            if exists:
                print(f"✅ Клиент {client_id} существует")
            else:
                print(f"❌ Клиент {client_id} не найден")
            return exists
        except Exception as e:
            print(f"❌ Ошибка при проверке клиента {client_id}: {str(e)}")
            return False

    def deactivate_client(self, client_id, inbound_id):
        """Деактивирует клиента в панели"""
        try:
            print(f"\n🔄 Попытка отключения клиента {client_id}...")
            
            # Проверяем существование клиента
            if not self.check_client_exists(client_id, inbound_id):
                print(f"ℹ️ Клиент {client_id} уже отключен")
                return True

            # Получаем текущие настройки inbound
            print(f"📥 Получение настроек inbound {inbound_id}...")
            response = self.session.get(f"{self.panel_url}/panel/api/inbounds/get/{inbound_id}")
            if response.status_code != 200:
                print(f"❌ Ошибка получения настроек inbound {inbound_id}")
                return False

            inbound_data = response.json()['obj']
            settings = json.loads(inbound_data['settings'])
            
            # Удаляем клиента из списка
            print(f"🗑️ Удаление клиента из списка...")
            settings['clients'] = [client for client in settings['clients'] 
                                 if client.get('id') != client_id]
            
            # Обновляем настройки
            print(f"📤 Обновление настроек inbound...")
            inbound_data['settings'] = json.dumps(settings)
            response = self.session.post(
                f"{self.panel_url}/panel/api/inbounds/update/{inbound_id}",
                json=inbound_data
            )
            
            if response.status_code == 200:
                print(f"✅ Клиент {client_id} успешно отключен")
                return True
            else:
                print(f"❌ Ошибка при обновлении настроек inbound")
            return False
        except Exception as e:
            print(f"❌ Ошибка при деактивации клиента {client_id}: {str(e)}")
            return False

    def check_all_subscriptions(self):
        """Проверяет все активные подписки и отключает истекшие"""
        try:
            self.db.ensure_connected()
            cursor = self.db.conn.cursor()
            
            current_time = datetime.now()
            print(f"\n⏰ Проверка подписок [{current_time.strftime('%d.%m.%Y %H:%M:%S')}]")
            print("-------------------")
            
            # Получаем все активные подписки
            print("🔄 Получение списка активных подписок...")
            query = """
                SELECT 
                    s.*,
                    COALESCE(NULLIF(u.username, ''), 'Unknown') as username,
                    u.user_id
                FROM subscriptions s
                LEFT JOIN users u ON s.user_id = u.user_id
                WHERE s.is_active = 1
            """
            cursor.execute(query)
            subscriptions = cursor.fetchall()
            
            print(f"📊 Найдено активных подписок: {len(subscriptions)}")
            print("-------------------")
            
            for sub in subscriptions:
                try:
                    # Проверяем дату окончания
                    end_date = datetime.fromisoformat(sub['end_date'])
                    
                    print(f"\n🔍 Проверка подписки:")
                    print(f"   • ID подписки: {sub['id']}")
                    print(f"   • Пользователь: @{sub['username']}")
                    print(f"   • ID пользователя: {sub['user_id']}")
                    print(f"   • Дата окончания: {end_date.strftime('%d.%m.%Y %H:%M')}")
                    print(f"   • Текущее время: {current_time.strftime('%d.%m.%Y %H:%M')}")
                    
                    # Сравниваем даты с учетом только даты и времени
                    if end_date > current_time:
                        print(f"✅ Подписка активна")
                        print("-------------------")
                        continue

                    print(f"⚠️ Подписка истекла")

                    # Отключаем подписку
                    try:
                        print("📦 Парсинг VPN конфигурации...")
                        vpn_config = json.loads(sub['vpn_config'])
                        inbound_id = vpn_config.get('inbound_id')
                        if not inbound_id:
                            raise ValueError("inbound_id не найден в конфигурации")
                            
                        client_id = sub['client_id']
                        if not client_id:
                            raise ValueError("client_id не найден")

                        print(f"🔄 Отключение клиента {client_id} из inbound {inbound_id}...")
                        if self.deactivate_client(client_id, inbound_id):
                            # Обновляем статус подписки
                            print("📝 Обновление статуса в базе данных...")
                            cursor.execute("""
                                UPDATE subscriptions 
                                SET is_active = 0 
                                WHERE id = ?
                            """, (sub['id'],))
                            self.db.conn.commit()
                            
                            print("\n🔴 Подписка успешно отключена:")
                            print(f"   • ID подписки: {sub['id']}")
                            print(f"   • Пользователь: @{sub['username']}")
                            print(f"   • ID пользователя: {sub['user_id']}")
                            print(f"   • Дата окончания: {end_date.strftime('%d.%m.%Y %H:%M')}")
                            print(f"   • Время отключения: {current_time.strftime('%d.%m.%Y %H:%M')}")
                        else:
                            print("❌ Не удалось отключить клиента в панели")
                            
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"❌ Ошибка: {str(e)}")
                        print(f"📝 Отмечаем подписку как неактивную...")
                        cursor.execute("""
                            UPDATE subscriptions 
                            SET is_active = 0 
                            WHERE id = ?
                        """, (sub['id'],))
                        self.db.conn.commit()
                        print(f"✅ Подписка {sub['id']} отмечена как неактивная")
                    
                    print("-------------------")

                except Exception as e:
                    print(f"❌ Ошибка при обработке подписки {sub['id']}: {str(e)}")
                    print("-------------------")
                    continue

        except Exception as e:
            print(f"❌ Ошибка при проверке подписок: {str(e)}")
            print("-------------------")

def main():
    print("\n🚀 Запуск системы проверки подписок")
    print("⚡ Скрипт запущен и работает")
    print("📝 Нажмите Ctrl+C для остановки")
    print("-------------------")
    
    while True:
        try:
            checker = SubscriptionChecker()
            checker.check_all_subscriptions()
            print("\n💤 Ожидание 10 секунд...")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n⛔ Скрипт остановлен пользователем")
            break
        except Exception as e:
            print(f"❌ Критическая ошибка: {str(e)}")
            print("🔄 Перезапуск через 10 секунд...")
            print("-------------------")
            time.sleep(10)

if __name__ == "__main__":
    main()

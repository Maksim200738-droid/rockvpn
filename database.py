import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file="vpn_bot.db"):
        self.db_file = db_file
        self.conn = None
        self.ensure_connected()
        self.create_tables()
        self.add_missing_columns()

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
        
        # Создание таблицы пользователей
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
        
        # Создание таблицы подписок
        c.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_type TEXT,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                vpn_config TEXT,
                client_id TEXT,
                inbound_id TEXT,
                duration INTEGER,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Создание таблицы реферальных транзакций
        c.execute('''
            CREATE TABLE IF NOT EXISTS referral_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                amount REAL,
                commission REAL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # Создание таблицы транзакций
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                transaction_type TEXT,
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Создание таблицы реферальных бонусов
        c.execute('''
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                bonus_amount REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # Создание таблицы статистики трафика
        c.execute('''
            CREATE TABLE IF NOT EXISTS traffic_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                upload_bytes BIGINT DEFAULT 0,
                download_bytes BIGINT DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()

    def add_missing_columns(self):
        """Добавляет отсутствующие колонки в таблицы"""
        cursor = self.conn.cursor()
        
        # Проверяем наличие колонки inbound_id
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'inbound_id' not in columns:
            print("Adding inbound_id column to subscriptions table")
            cursor.execute('''
                ALTER TABLE subscriptions
                ADD COLUMN inbound_id TEXT
            ''')
            
        if 'duration' not in columns:
            print("Adding duration column to subscriptions table")
            cursor.execute('''
                ALTER TABLE subscriptions
                ADD COLUMN duration INTEGER DEFAULT 30
            ''')
        
        self.conn.commit()

    def add_user(self, user_id, username, referrer_id=None):
        """Добавляет нового пользователя или обновляет существующего"""
        self.ensure_connected()
        c = self.conn.cursor()
        
        username = username or "Unknown"  # Используем "Unknown" если username is None
        
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        existing_user = c.fetchone()
        
        if not existing_user:
            # Создаем нового пользователя
            c.execute('''INSERT INTO users 
                        (user_id, username, referrer_id)
                        VALUES (?, ?, ?)''',
                     (user_id, username, referrer_id))
            if referrer_id:
                c.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?",
                         (referrer_id,))
        else:
            # Обновляем username существующего пользователя
            c.execute('''UPDATE users 
                        SET username = ?
                        WHERE user_id = ?''',
                     (username, user_id))
        
        self.conn.commit()

    def get_user(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        if user:
            return {
                'user_id': user['user_id'],
                'username': user['username'],
                'referrer_id': user['referrer_id'],
                'balance': user['balance'],
                'is_admin': user['is_admin'],
                'registration_date': user['registration_date']
            }
        return None

    def update_user_balance(self, user_id, amount):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?",
                 (amount, user_id))
        self.conn.commit()

    def add_subscription(self, user_id, subscription_type, vpn_config, client_id, inbound_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        start_date = datetime.now()
        
        # Определяем длительность подписки в днях
        duration_map = {
            "trial": timedelta(days=3),
            "test_1min": timedelta(minutes=1),
            "1_99": timedelta(days=30),
            "2_179": timedelta(days=60),
            "6_499": timedelta(days=180),
            "12_899": timedelta(days=365)
        }
        
        duration = duration_map.get(subscription_type)
        if not duration:
            raise ValueError(f"Неизвестный тип подписки: {subscription_type}")
            
        end_date = start_date + duration
        
        c.execute('''INSERT INTO subscriptions 
                    (user_id, subscription_type, start_date, end_date, 
                     vpn_config, client_id, inbound_id, duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (user_id, subscription_type, start_date.isoformat(), end_date.isoformat(),
                  vpn_config, client_id, inbound_id, duration.days))
        self.conn.commit()

    def get_active_subscription(self, user_id):
        """Получает активную подписку пользователя"""
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND is_active = 1 
            AND end_date > datetime('now')
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,))
        subscription = c.fetchone()
        if subscription:
            return dict(subscription)
        return None

    def get_user_subscriptions(self, user_id):
        """Получает все подписки пользователя"""
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM subscriptions 
            WHERE user_id = ?
            ORDER BY end_date DESC
        """, (user_id,))
        subscriptions = c.fetchall()
        return [dict(sub) for sub in subscriptions] if subscriptions else []

    def update_traffic_stats(self, user_id, upload, download):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('''INSERT OR REPLACE INTO traffic_stats 
                    (user_id, upload_bytes, download_bytes)
                    VALUES (?, ?, ?)''',
                 (user_id, upload, download))
        self.conn.commit()

    def get_traffic_stats(self, user_id):
        """Получает статистику трафика пользователя"""
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT * FROM traffic_stats WHERE user_id = ?", (user_id,))
        stats = c.fetchone()
        if stats:
            return {
                'id': stats['id'],
                'user_id': stats['user_id'],
                'upload_bytes': stats['upload_bytes'] or 0,
                'download_bytes': stats['download_bytes'] or 0,
                'timestamp': stats['timestamp']
            }
        return {
            'id': None,
            'user_id': user_id,
            'upload_bytes': 0,
            'download_bytes': 0,
            'timestamp': None
        }

    def add_transaction(self, user_id, amount, type_, payment_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('''INSERT INTO transactions 
                    (id, user_id, amount, transaction_type, status)
                    VALUES (?, ?, ?, ?, ?)''',
                 (payment_id, user_id, amount, type_, 'pending'))
        self.conn.commit()

    def update_transaction_status(self, payment_id, status):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("UPDATE transactions SET status = ? WHERE id = ?",
                 (status, payment_id))
        self.conn.commit()

    def get_transaction(self, payment_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT * FROM transactions WHERE id = ?", (payment_id,))
        transaction = c.fetchone()
        if transaction:
            return {
                'id': transaction['id'],
                'user_id': transaction['user_id'],
                'amount': transaction['amount'],
                'transaction_type': transaction['transaction_type'],
                'status': transaction['status'],
                'timestamp': transaction['timestamp']
            }
        return None

    def get_last_pending_transaction(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM transactions 
            WHERE user_id = ? AND status = 'pending' 
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        transaction = c.fetchone()
        if transaction:
            return {
                'id': transaction['id'],
                'user_id': transaction['user_id'],
                'amount': transaction['amount'],
                'transaction_type': transaction['transaction_type'],
                'status': transaction['status'],
                'timestamp': transaction['timestamp']
            }
        return None

    def add_referral_bonus(self, referrer_id, referred_id, bonus_amount):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('''INSERT INTO referral_bonuses 
                    (referrer_id, referred_id, bonus_amount)
                    VALUES (?, ?, ?)''',
                 (referrer_id, referred_id, bonus_amount))
        self.conn.commit()

    def process_referral_bonus(self, referrer_id, referred_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('''UPDATE referral_bonuses SET status = 'completed' 
                    WHERE referrer_id = ? AND referred_id = ?''',
                 (referrer_id, referred_id))
        c.execute('''UPDATE users SET balance = balance + 
                    (SELECT bonus_amount FROM referral_bonuses 
                     WHERE referrer_id = ? AND referred_id = ?)
                    WHERE user_id = ?''',
                 (referrer_id, referred_id, referrer_id))
        self.conn.commit()

    def get_referral_stats(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Получаем количество рефералов
        c.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        total_referrals = c.fetchone()[0]
        
        # Получаем сумму бонусов
        c.execute("SELECT COALESCE(SUM(bonus_amount), 0) FROM referral_bonuses WHERE referrer_id = ?", (user_id,))
        total_earnings = c.fetchone()[0]
        
        return (total_referrals, total_earnings)

    def is_admin(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        is_admin = bool(result and result[0])
        print(f"Checking admin rights for user {user_id}: {is_admin}")
        return is_admin

    def set_admin(self, user_id, is_admin=True):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Проверяем существует ли пользователь
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not c.fetchone():
            # Если пользователя нет, создаем его
            c.execute('''INSERT INTO users 
                        (user_id, is_admin)
                        VALUES (?, ?)''',
                     (user_id, 1 if is_admin else 0))
        else:
            # Если пользователь существует, обновляем права
            c.execute("UPDATE users SET is_admin = ? WHERE user_id = ?",
                     (1 if is_admin else 0, user_id))
        
        self.conn.commit()
        print(f"Set admin status for user {user_id} to {is_admin}")

    def get_all_active_subscriptions(self):
        """Возвращает все активные подписки с информацией о пользователях"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                s.id,
                s.user_id,
                s.subscription_type,
                s.end_date,
                s.client_id,
                COALESCE(s.inbound_id, '') as inbound_id,
                u.username
            FROM subscriptions s
            LEFT JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1
            ORDER BY s.end_date ASC
        ''')
        
        columns = ['id', 'user_id', 'subscription_type', 'end_date', 'client_id', 'inbound_id', 'username']
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_subscription_by_id(self, subscription_id):
        """Возвращает информацию о подписке по её ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                s.id,
                s.user_id,
                s.subscription_type,
                s.end_date,
                s.client_id,
                COALESCE(s.inbound_id, '') as inbound_id,
                u.username
            FROM subscriptions s
            LEFT JOIN users u ON s.user_id = u.user_id
            WHERE s.id = ?
        ''', (subscription_id,))
        
        row = cursor.fetchone()
        if row:
            columns = ['id', 'user_id', 'subscription_type', 'end_date', 'client_id', 'inbound_id', 'username']
            return dict(zip(columns, row))
        return None

    def deactivate_subscription(self, subscription_id):
        """Деактивирует подписку"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE subscriptions 
            SET is_active = 0 
            WHERE id = ?
        ''', (subscription_id,))
        self.conn.commit()

    def get_recent_transactions(self, limit=10):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('''SELECT t.*, u.username FROM transactions t
                    JOIN users u ON t.user_id = u.user_id
                    ORDER BY t.timestamp DESC LIMIT ?''', (limit,))
        transactions = c.fetchall()
        return transactions

    def add_pending_transaction(self, user_id, amount, transaction_type, username):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Генерируем уникальный ID транзакции
        payment_id = f"PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        
        c.execute('''INSERT INTO transactions 
                    (id, user_id, amount, transaction_type, status)
                    VALUES (?, ?, ?, ?, ?)''',
                 (payment_id, user_id, amount, transaction_type, 'pending'))
        self.conn.commit()
        
        return payment_id

    def get_user_balance(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result['balance'] if result else 0

    def add_referral_transaction(self, referrer_id, referred_id, amount):
        self.ensure_connected()
        c = self.conn.cursor()
        commission = amount * 0.5  # 50% commission
        
        # Add transaction record
        c.execute('''
            INSERT INTO referral_transactions 
            (referrer_id, referred_id, amount, commission) 
            VALUES (?, ?, ?, ?)
        ''', (referrer_id, referred_id, amount, commission))
        
        # Update referrer's balance
        c.execute('''
            UPDATE users 
            SET balance = balance + ? 
            WHERE user_id = ?
        ''', (commission, referrer_id))
        
        self.conn.commit()
        return commission

    def get_referral_stats(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Get number of referrals
        c.execute('SELECT COUNT(*) as ref_count FROM users WHERE referrer_id = ?', (user_id,))
        ref_count = c.fetchone()['ref_count']
        
        # Get total earnings
        c.execute('''
            SELECT COALESCE(SUM(commission), 0) as total_earnings 
            FROM referral_transactions 
            WHERE referrer_id = ?
        ''', (user_id,))
        total_earnings = c.fetchone()['total_earnings']
        
        return {
            'referral_count': ref_count,
            'total_earnings': total_earnings
        }

    def update_user_info(self, user_data):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Проверяем, существует ли пользователь
        c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_data['user_id'],))
        exists = c.fetchone()
        
        if exists:
            # Обновляем существующего пользователя
            if 'referrer_id' in user_data:
                c.execute('''
                    UPDATE users 
                    SET username = ?, referrer_id = ?
                    WHERE user_id = ? AND referrer_id IS NULL
                ''', (user_data['username'], user_data['referrer_id'], user_data['user_id']))
            else:
                c.execute('''
                    UPDATE users 
                    SET username = ?
                    WHERE user_id = ?
                ''', (user_data['username'], user_data['user_id']))
        else:
            # Создаем нового пользователя
            if 'referrer_id' in user_data:
                c.execute('''
                    INSERT INTO users (user_id, username, referrer_id)
                    VALUES (?, ?, ?)
                ''', (user_data['user_id'], user_data['username'], user_data['referrer_id']))
            else:
                c.execute('''
                    INSERT INTO users (user_id, username)
                    VALUES (?, ?)
                ''', (user_data['user_id'], user_data['username']))
        
        self.conn.commit()

    def delete_subscription(self, user_id):
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Получаем информацию о подписке перед удалением
        c.execute('''
            SELECT client_id, vpn_config, inbound_id
            FROM subscriptions 
            WHERE user_id = ?
            ORDER BY start_date DESC
            LIMIT 1
        ''', (user_id,))
        subscription = c.fetchone()
        
        if subscription:
            # Деактивируем подписку
            c.execute('''
                UPDATE subscriptions 
                SET is_active = 0 
                WHERE user_id = ?
            ''', (user_id,))
            
            self.conn.commit()
            return subscription
        return None

    def subtract_from_balance(self, user_id, amount):
        """Вычитает сумму с баланса пользователя"""
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Проверяем текущий баланс
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            raise Exception("Пользователь не найден")
            
        current_balance = result['balance']
        if current_balance < amount:
            raise Exception(f"Недостаточно средств на балансе (текущий баланс: {current_balance})")
        
        # Вычитаем сумму
        c.execute("""
            UPDATE users 
            SET balance = balance - ? 
            WHERE user_id = ?
        """, (amount, user_id))
        
        self.conn.commit()
        return current_balance - amount

    def get_total_users_count(self):
        """Возвращает общее количество пользователей"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        return cursor.fetchone()[0]

    def get_active_subscriptions_count(self):
        """Возвращает количество активных подписок"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = 1')
        return cursor.fetchone()[0]

    def get_total_revenue(self):
        """Возвращает общую сумму доходов"""
        self.ensure_connected()
        c = self.conn.cursor()
        c.execute("""
            SELECT SUM(amount) as total
            FROM transactions
            WHERE status = 'completed'
        """)
        result = c.fetchone()
        return result['total'] if result['total'] else 0

    def get_subscriptions_count_by_tariff(self, tariff_id):
        """Возвращает количество подписок определенного типа"""
        self.ensure_connected()
        c = self.conn.cursor()
        
        # Маппинг старых типов подписок на новые
        old_to_new = {
            "1_month": "1_99",
            "2_months": "2_179",
            "6_months": "6_499",
            "12_months": "12_899"
        }
        
        # Если это новый тип подписки, ищем по нему
        # Если старый - ищем по соответствующему старому
        if tariff_id in old_to_new.values():
            old_type = next((k for k, v in old_to_new.items() if v == tariff_id), None)
            if old_type:
                c.execute("""
                    SELECT COUNT(*) as count
                    FROM subscriptions
                    WHERE (subscription_type = ? OR subscription_type = ?) AND is_active = 1
                """, (tariff_id, old_type))
            else:
                c.execute("""
                    SELECT COUNT(*) as count
                    FROM subscriptions
                    WHERE subscription_type = ? AND is_active = 1
                """, (tariff_id,))
        else:
            c.execute("""
                SELECT COUNT(*) as count
                FROM subscriptions
                WHERE subscription_type = ? AND is_active = 1
            """, (tariff_id,))
            
        result = c.fetchone()
        return result['count'] if result else 0

    def get_new_users_count_today(self):
        """Возвращает количество новых пользователей за сегодня"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE DATE(registration_date) = DATE('now')
        ''')
        return cursor.fetchone()[0]

    def get_all_users(self):
        """Возвращает список всех пользователей"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id, username FROM users')
        return [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]

    def had_trial_subscription(self, user_id: int) -> bool:
        """Проверяет, была ли у пользователя пробная подписка"""
        self.ensure_connected()
        c = self.conn.cursor()
        
        c.execute('''
            SELECT COUNT(*) as count 
            FROM subscriptions 
            WHERE user_id = ? AND subscription_type = 'trial'
        ''', (user_id,))
        
        result = c.fetchone()
        return result['count'] > 0

    def user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь в базе данных"""
        self.ensure_connected()
        c = self.conn.cursor()
        
        c.execute('SELECT COUNT(*) as count FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result['count'] > 0

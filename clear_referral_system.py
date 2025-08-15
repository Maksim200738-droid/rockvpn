import sqlite3

def clear_referral_system():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('vpn_bot.db')
        cursor = conn.cursor()

        # Начинаем транзакцию
        conn.execute('BEGIN TRANSACTION')

        try:
            # Очищаем баланс пользователей
            cursor.execute('UPDATE users SET balance = 0')
            
            # Очищаем реферальные связи
            cursor.execute('UPDATE users SET referrer_id = NULL')
            
            # Очищаем таблицу реферальных транзакций
            cursor.execute('DELETE FROM referral_transactions')
            
            # Очищаем таблицу реферальных бонусов
            cursor.execute('DELETE FROM referral_bonuses')
            
            # Фиксируем изменения
            conn.commit()
            print('✅ Реферальная система успешно очищена!')
            print('- Балансы пользователей обнулены')
            print('- Реферальные связи удалены')
            print('- Реферальные транзакции очищены')
            print('- Реферальные бонусы очищены')

        except Exception as e:
            # Если произошла ошибка, откатываем изменения
            conn.rollback()
            print(f'❌ Ошибка при очистке: {str(e)}')
            raise

    except Exception as e:
        print(f'❌ Ошибка при подключении к базе данных: {str(e)}')
    
    finally:
        # Закрываем соединение
        if conn:
            conn.close()

if __name__ == '__main__':
    clear_referral_system()

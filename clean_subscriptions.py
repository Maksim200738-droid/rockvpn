from database import Database
import sqlite3

def clean_subscriptions():
    db = Database()
    cursor = db.conn.cursor()
    
    print("\n🧹 Начинаем очистку подписок...")
    
    try:
        # Получаем количество подписок до очистки
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        before_count = cursor.fetchone()[0]
        print(f"📊 Текущее количество подписок: {before_count}")
        
        # Очищаем таблицу подписок
        cursor.execute("DELETE FROM subscriptions")
        db.conn.commit()
        
        # Проверяем количество подписок после очистки
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        after_count = cursor.fetchone()[0]
        print(f"✅ Удалено подписок: {before_count - after_count}")
        print("🎉 Очистка завершена успешно!")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при очистке базы данных: {str(e)}")
    finally:
        db.conn.close()

if __name__ == "__main__":
    clean_subscriptions()

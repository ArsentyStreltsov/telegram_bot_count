"""
Force update exchange rates script for Railway
"""
from db import get_db, init_db
from models import ExchangeRate, Currency
from datetime import datetime, timezone

def force_update_rates():
    """Force update exchange rates by deleting all and creating new ones"""
    db = next(get_db())
    
    try:
        print("🔄 Принудительное обновление курсов валют...")
        
        # Delete ALL existing exchange rates
        deleted_count = db.query(ExchangeRate).delete()
        print(f"🗑 Удалено {deleted_count} старых курсов валют")
        
        # Create new exchange rates
        exchange_rates_data = [
            {
                "from_currency": Currency.EUR,
                "to_currency": Currency.SEK,
                "rate": 11.30,
                "description": "EUR/SEK"
            },
            {
                "from_currency": Currency.RUB,
                "to_currency": Currency.SEK,
                "rate": 0.12,
                "description": "RUB/SEK"
            }
        ]
        
        for rate_data in exchange_rates_data:
            rate = ExchangeRate(
                from_currency=rate_data["from_currency"],
                to_currency=rate_data["to_currency"],
                rate=rate_data["rate"],
                valid_from=datetime.now(timezone.utc)
            )
            db.add(rate)
            print(f"✅ Создан курс {rate_data['description']}: {rate_data['rate']}")
        
        db.commit()
        print("🎉 Курсы валют успешно обновлены!")
        
        # Verify the rates were created
        rates = db.query(ExchangeRate).all()
        print(f"📊 Всего курсов в базе: {len(rates)}")
        for rate in rates:
            print(f"   {rate.from_currency.value} → {rate.to_currency.value}: {rate.rate}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при обновлении курсов: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database first
    init_db()
    print("Database initialized")
    
    # Force update rates
    force_update_rates()

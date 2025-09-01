"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Create database directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/expenses.db')

# Create engine
if DATABASE_URL.startswith('sqlite'):
    # For SQLite, use file-based database
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # For PostgreSQL (Railway), use connection pooling
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    # Import models to ensure they are registered
    from models import User, Profile, ProfileMember, ShoppingItem, Expense, ExpenseAllocation, ExchangeRate, MonthSnapshot
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Force create exchange rates if they don't exist
    force_create_exchange_rates()

def force_create_exchange_rates():
    """Force create exchange rates if they don't exist"""
    from models import Currency, ExchangeRate
    from datetime import datetime, timezone
    
    db = next(get_db())
    try:
        # Check if EUR/SEK rate exists
        eur_rate = db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == Currency.EUR,
            ExchangeRate.to_currency == Currency.SEK
        ).first()
        
        # Check if RUB/SEK rate exists
        rub_rate = db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == Currency.RUB,
            ExchangeRate.to_currency == Currency.SEK
        ).first()
        
        if not eur_rate or not rub_rate:
            print("🔄 Создаем курсы валют...")
            
            # Delete all existing rates
            db.query(ExchangeRate).delete()
            
            # Create new rates
            rates_data = [
                {
                    "from_currency": Currency.EUR,
                    "to_currency": Currency.SEK,
                    "rate": 11.30
                },
                {
                    "from_currency": Currency.RUB,
                    "to_currency": Currency.SEK,
                    "rate": 0.12
                }
            ]
            
            for rate_data in rates_data:
                rate = ExchangeRate(
                    from_currency=rate_data["from_currency"],
                    to_currency=rate_data["to_currency"],
                    rate=rate_data["rate"],
                    valid_from=datetime.now(timezone.utc)
                )
                db.add(rate)
                print(f"✅ Создан курс {rate_data['from_currency'].value} → {rate_data['to_currency'].value}: {rate_data['rate']}")
            
            db.commit()
            print("🎉 Курсы валют созданы!")
        else:
            print("✅ Курсы валют уже существуют")
            
    except Exception as e:
        print(f"❌ Ошибка при создании курсов валют: {e}")
        db.rollback()
    finally:
        db.close()

def reset_db():
    """Reset database (drop all tables and recreate)"""
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Database reset successfully")

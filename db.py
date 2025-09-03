"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables from env.production if it exists
if os.path.exists('env.production'):
    load_dotenv('env.production')

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
    """Get database session with connection error handling"""
    db = SessionLocal()
    try:
        # Test connection
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        # Close session on error
        db.close()
        # Re-raise the error
        raise e
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
    
    # Force create hardcoded users if they don't exist
    force_create_users()

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

def force_create_users():
    """Force create 5 hardcoded users if they don't exist"""
    from models import User, Profile, ProfileMember
    
    db = next(get_db())
    try:
        print("🔄 Создаем захардкоженных пользователей...")
        
        # Захардкоженные данные пользователей
        HARDCODED_USERS = [
            {
                "telegram_id": 804085588,
                "first_name": "Сеня",
                "last_name": "Стрельцов",
                "username": "the_lodka"
            },
            {
                "telegram_id": 252901018, 
                "first_name": "Катя",
                "last_name": "Стрельцова",
                "username": "katrine_streltsova"
            },
            {
                "telegram_id": 350653235,
                "first_name": "Дима", 
                "last_name": "Стрельцов",
                "username": None
            },
            {
                "telegram_id": 916228993,
                "first_name": "Даша",
                "last_name": "Ше",
                "username": "dashok_she"
            },
            {
                "telegram_id": 6379711500,
                "first_name": "Миша",
                "last_name": "Брат",
                "username": "l_tyti"
            }
        ]
        
        # Создаем или обновляем каждого пользователя
        for user_data in HARDCODED_USERS:
            # Проверяем, существует ли пользователь по telegram_id
            existing_user = db.query(User).filter(
                User.telegram_id == user_data["telegram_id"]
            ).first()
            
            if existing_user:
                # Обновляем существующего пользователя
                existing_user.first_name = user_data["first_name"]
                existing_user.last_name = user_data["last_name"]
                existing_user.username = user_data["username"]
                print(f"✅ Обновлен пользователь: {user_data['first_name']} (ID: {user_data['telegram_id']})")
            else:
                # Создаем нового пользователя
                new_user = User(
                    telegram_id=user_data["telegram_id"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    username=user_data["username"]
                )
                db.add(new_user)
                print(f"✅ Создан пользователь: {user_data['first_name']} (ID: {user_data['telegram_id']})")
        
        # Создаем профиль "Home" если его нет
        home_profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not home_profile:
            home_profile = Profile(name="Home", is_default=True)
            db.add(home_profile)
            print("✅ Создан профиль Home")
        
        # Добавляем всех пользователей в профиль Home с весом 1
        for user_data in HARDCODED_USERS:
            user = db.query(User).filter(User.telegram_id == user_data["telegram_id"]).first()
            if user:
                # Проверяем, есть ли уже связь
                existing_member = db.query(ProfileMember).filter(
                    ProfileMember.profile_id == home_profile.id,
                    ProfileMember.user_id == user.id
                ).first()
                
                if not existing_member:
                    member = ProfileMember(
                        profile_id=home_profile.id,
                        user_id=user.id,
                        weight=1.0
                    )
                    db.add(member)
                    print(f"✅ Добавлен {user_data['first_name']} в профиль Home")
                else:
                    print(f"✅ {user_data['first_name']} уже в профиле Home")
        
        db.commit()
        print("🎉 Все захардкоженные пользователи созданы/обновлены!")
        
    except Exception as e:
        print(f"❌ Ошибка при создании пользователей: {e}")
        db.rollback()
    finally:
        db.close()

def reset_db():
    """Reset database (drop all tables and recreate)"""
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Database reset successfully")

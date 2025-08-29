"""
Seed script to add initial data (profiles and exchange rates)
"""
from db import get_db, init_db
from models import Profile, ExchangeRate, Currency
from datetime import datetime

def seed_data():
    """Add initial data to the database"""
    db = next(get_db())
    
    try:
        # Create basic profiles (without members yet)
        profiles_data = [
            {
                "name": "Home",
                "description": "Домашние расходы",
                "is_default": True,
            },
            {
                "name": "Trip",
                "description": "Расходы на поездки",
                "is_default": False,
            }
        ]
        
        for profile_data in profiles_data:
            # Check if profile already exists
            existing_profile = db.query(Profile).filter(Profile.name == profile_data["name"]).first()
            if existing_profile:
                print(f"Profile {profile_data['name']} already exists")
                continue
            
            # Create profile
            profile = Profile(
                name=profile_data["name"],
                description=profile_data["description"],
                is_default=profile_data["is_default"]
            )
            db.add(profile)
            print(f"Created profile: {profile_data['name']}")
        
        # Set default exchange rate
        existing_rate = db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == Currency.EUR,
            ExchangeRate.to_currency == Currency.SEK
        ).first()
        
        if not existing_rate:
            rate = ExchangeRate(
                from_currency=Currency.EUR,
                to_currency=Currency.SEK,
                rate=11.30,
                valid_from=datetime.utcnow()
            )
            db.add(rate)
            print("Set default EUR/SEK rate: 11.30")
        
        db.commit()
        print("Seed data created successfully!")
        print("\n📝 Next steps:")
        print("1. Let all family members join the bot with /start")
        print("2. Run setup_profiles.py to configure family members and profiles")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating seed data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database first
    init_db()
    print("Database initialized")
    
    # Add seed data
    seed_data()

"""
Base handler with common functionality
"""
from typing import Optional
from sqlalchemy.orm import Session
from models import User
from db import get_db
from utils.texts import get_welcome_message

class BaseHandler:
    """Base handler with common functionality"""
    
    @staticmethod
    def get_or_create_user(db: Session, telegram_user) -> User:
        """Get existing user or create new one"""
        user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
    
    @staticmethod
    def get_user_name(user: User) -> str:
        """Get user display name"""
        if user.first_name:
            return user.first_name
        elif user.username:
            return user.username
        else:
            return f"User {user.telegram_id}"
    
    @staticmethod
    def validate_amount(amount_str: str) -> Optional[float]:
        """Validate and parse amount string"""
        try:
            amount = float(amount_str.replace(',', '.'))
            if amount <= 0:
                return None
            return amount
        except ValueError:
            return None
    
    @staticmethod
    def validate_exchange_rate(rate_str: str) -> Optional[float]:
        """Validate and parse exchange rate string"""
        try:
            rate = float(rate_str.replace(',', '.'))
            if rate <= 0:
                return None
            return rate
        except ValueError:
            return None

"""
Special splitting logic for new expense categories
"""
from sqlalchemy.orm import Session
from models import ExpenseCategory, Profile, ProfileMember, User
from typing import List, Dict

def get_users_for_category(db: Session, category: ExpenseCategory) -> List[User]:
    """Get users who should participate in expense splitting for given category"""
    if category == ExpenseCategory.FOOD:
        # Продукты - все участники
        return db.query(User).all()
    
    elif category == ExpenseCategory.ALCOHOL:
        # Алкоголь - все кроме Миши (брата)
        return db.query(User).filter(User.username != "l_tyti").all()
    
    elif category == ExpenseCategory.OTHER:
        # Другое - все участники (будет уточняться позже)
        return db.query(User).all()
    
    else:
        # По умолчанию - все участники
        return db.query(User).all()

def calculate_special_split(db: Session, amount: float, category: ExpenseCategory, profile_id: int) -> Dict[int, float]:
    """Calculate expense split based on special category rules"""
    # Get users for this category
    users = get_users_for_category(db, category)
    
    if not users:
        return {}
    
    # Equal split among participating users
    user_count = len(users)
    share_per_user = amount / user_count
    
    # Create allocation dict
    allocations = {}
    for user in users:
        allocations[user.id] = share_per_user
    
    return allocations

def get_category_description(category: ExpenseCategory, custom_name: str = None) -> str:
    """Get description for expense category"""
    if category == ExpenseCategory.FOOD:
        return "Продукты (делится на всех)"
    elif category == ExpenseCategory.ALCOHOL:
        return "Алкоголь (делится на всех кроме Миши)"
    elif category == ExpenseCategory.OTHER and custom_name:
        return f"Другое: {custom_name}"
    else:
        return "Другое"

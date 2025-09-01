"""
Expense management service
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import (
    Expense, ExpenseAllocation, ExchangeRate, Currency, 
    ExpenseCategory, User, Profile
)
from services.split import SplitService
from datetime import datetime, date

class ExpenseService:
    """Service for managing expenses"""
    
    @staticmethod
    def get_current_exchange_rate(
        db: Session, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> float:
        """Get current exchange rate for currency pair"""
        if from_currency == to_currency:
            return 1.0
        
        # Get the most recent valid rate
        rate = db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
            (ExchangeRate.valid_until.is_(None) | (ExchangeRate.valid_until > datetime.utcnow()))
        ).order_by(ExchangeRate.valid_from.desc()).first()
        
        if not rate:
            raise ValueError(f"No exchange rate found for {from_currency.value} to {to_currency.value}")
        
        return rate.rate
    
    @staticmethod
    def create_expense(
        db: Session,
        amount: float,
        currency: Currency,
        category: ExpenseCategory,
        payer_id: int,
        profile_id: int,
        note: Optional[str] = None,
        allocations: Optional[dict] = None,
        custom_category_name: Optional[str] = None
    ) -> Expense:
        """Create a new expense with automatic allocation"""
        
        # Get current exchange rate to SEK
        if currency == Currency.SEK:
            exchange_rate = 1.0
            amount_sek = amount
        else:
            exchange_rate = ExpenseService.get_current_exchange_rate(db, currency, Currency.SEK)
            amount_sek = amount * exchange_rate
        
        # Create expense
        expense = Expense(
            amount=amount,
            currency=currency,
            exchange_rate=exchange_rate,
            amount_sek=amount_sek,
            category=category,
            custom_category_name=custom_category_name,
            note=note,
            payer_id=payer_id,
            profile_id=profile_id,
            month=datetime.now().replace(day=1).date()
        )
        
        db.add(expense)
        db.flush()  # Get the ID
        
        # Use provided allocations or calculate using profile
        if allocations:
            # Use special splitting logic
            for user_id, share_amount in allocations.items():
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount,
                    weight_used=1.0
                )
                db.add(allocation)
        else:
            # Use profile-based splitting
            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")
            
            profile_allocations = SplitService.calculate_expense_split(db, expense, profile)
            
            # Save allocations
            for allocation in profile_allocations:
                db.add(allocation)
        
        db.commit()
        return expense
    
    @staticmethod
    def get_monthly_expenses(
        db: Session, 
        month: Optional[date] = None
    ) -> List[Expense]:
        """Get all expenses for a given month"""
        if month is None:
            month = datetime.now().replace(day=1).date()
        
        return db.query(Expense).filter(Expense.month == month).all()
    
    @staticmethod
    def get_expenses_by_category(
        db: Session, 
        month: Optional[date] = None
    ) -> dict:
        """Get expenses grouped by category for a month"""
        if month is None:
            month = datetime.now().replace(day=1).date()
        
        # Query expenses with category totals
        category_totals = db.query(
            Expense.category,
            func.sum(Expense.amount_sek).label('total_sek'),
            func.count(Expense.id).label('count')
        ).filter(
            Expense.month == month
        ).group_by(Expense.category).all()
        
        result = {}
        for category, total_sek, count in category_totals:
            result[category.value] = {
                'total_sek': float(total_sek),
                'count': count
            }
            
            # Add custom category names for "OTHER" category
            if category == ExpenseCategory.OTHER:
                custom_names = db.query(Expense.custom_category_name).filter(
                    Expense.category == ExpenseCategory.OTHER,
                    Expense.month == month,
                    Expense.custom_category_name.isnot(None)
                ).distinct().all()
                
                if custom_names:
                    result[category.value]['custom_names'] = {name[0] for name in custom_names if name[0]}
        
        return result
    
    @staticmethod
    def get_user_expenses(
        db: Session, 
        user_id: int, 
        month: Optional[date] = None
    ) -> List[Expense]:
        """Get expenses paid by a specific user"""
        if month is None:
            month = datetime.now().replace(day=1).date()
        
        return db.query(Expense).filter(
            Expense.payer_id == user_id,
            Expense.month == month
        ).all()
    
    @staticmethod
    def get_user_allocations(
        db: Session, 
        user_id: int, 
        month: Optional[date] = None
    ) -> List[ExpenseAllocation]:
        """Get expense allocations for a specific user"""
        if month is None:
            month = datetime.now().replace(day=1).date()
        
        return db.query(ExpenseAllocation).join(Expense).filter(
            ExpenseAllocation.user_id == user_id,
            Expense.month == month
        ).all()
    
    @staticmethod
    def delete_expense(db: Session, expense_id: int) -> bool:
        """Delete expense and its allocations"""
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return False
        
        # Delete allocations first (due to foreign key constraints)
        db.query(ExpenseAllocation).filter(ExpenseAllocation.expense_id == expense_id).delete()
        
        # Delete the expense
        db.delete(expense)
        db.commit()
        
        return True
    
    @staticmethod
    def get_expense_by_id(db: Session, expense_id: int) -> Optional[Expense]:
        """Get expense by ID"""
        return db.query(Expense).filter(Expense.id == expense_id).first()

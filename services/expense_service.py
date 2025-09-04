"""
Expense management service
"""
from typing import List, Optional, Set
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
        custom_category_name: Optional[str] = None,
        split_type: str = None,
        selected_participants: Set[int] = None
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
        
        # Use provided allocations or calculate using special category rules
        if allocations:
            # Use special splitting logic
            for user_id, share_amount in allocations.items():
                # Convert share_amount to SEK if needed
                if currency == Currency.SEK:
                    share_amount_sek = share_amount
                else:
                    share_amount_sek = share_amount * exchange_rate
                
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount_sek,
                    weight_used=1.0
                )
                db.add(allocation)
        elif split_type == "split_families":
            # Use family split logic
            print(f"🔍 DEBUG: Creating expense with split_type='split_families'")
            print(f"🔍 DEBUG: amount_sek={amount_sek}, payer_id={payer_id}")
            
            from services.flexible_split import FlexibleSplitService
            
            # Получаем telegram_id плательщика
            payer_user = db.query(User).filter(User.id == payer_id).first()
            if not payer_user:
                print(f"❌ DEBUG: Пользователь с ID {payer_id} не найден!")
                return expense
            
            print(f"🔍 DEBUG: Плательщик: {payer_user.first_name} (telegram_id: {payer_user.telegram_id})")
            
            family_allocations = FlexibleSplitService.calculate_family_split(
                db, amount_sek, payer_user.telegram_id
            )
            
            print(f"🔍 DEBUG: Family allocations received: {family_allocations}")
            
            for user_id, share_amount in family_allocations.items():
                print(f"🔍 DEBUG: Creating allocation for user_id={user_id}, share_amount={share_amount}")
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount,
                    weight_used=1.0
                )
                db.add(allocation)
                print(f"🔍 DEBUG: Allocation added to session")
        elif split_type == "participants" and selected_participants:
            # Use participant selection logic
            from services.flexible_split import FlexibleSplitService
            participant_allocations = FlexibleSplitService.calculate_participant_split(
                db, amount_sek, selected_participants, payer_id
            )
            
            for user_id, share_amount in participant_allocations.items():
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount,
                    weight_used=1.0
                )
                db.add(allocation)
        else:
            # Use special category-based splitting
            from services.special_split import calculate_special_split
            category_allocations = calculate_special_split(db, amount_sek, category, profile_id)
            
            # Save allocations
            for user_id, share_amount in category_allocations.items():
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount,
                    weight_used=1.0
                )
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
            
            # For "OTHER" category, get individual expenses with custom names
            if category == ExpenseCategory.OTHER:
                individual_expenses = db.query(
                    Expense.custom_category_name,
                    Expense.amount_sek
                ).filter(
                    Expense.category == ExpenseCategory.OTHER,
                    Expense.month == month,
                    Expense.custom_category_name.isnot(None)
                ).all()
                
                if individual_expenses:
                    result[category.value]['individual_expenses'] = [
                        {
                            'name': expense.custom_category_name,
                            'amount_sek': float(expense.amount_sek)
                        }
                        for expense in individual_expenses
                    ]
        
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

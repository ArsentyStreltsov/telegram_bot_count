"""
Shopping list management service
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models import ShoppingItem, ExpenseCategory, User, Currency
from services.expense_service import ExpenseService
from models import ExpenseCategory
from datetime import datetime

class ShoppingService:
    """Service for managing shopping list"""
    
    @staticmethod
    def add_item(
        db: Session,
        title: str,
        category: ExpenseCategory,
        created_by: int,
        note: Optional[str] = None
    ) -> ShoppingItem:
        """Add item to shopping list"""
        item = ShoppingItem(
            title=title,
            category=category,
            note=note,
            created_by=created_by
        )
        
        db.add(item)
        db.commit()
        return item
    
    @staticmethod
    def get_items(
        db: Session, 
        checked_only: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ShoppingItem]:
        """Get shopping list items with optional filtering"""
        query = db.query(ShoppingItem)
        
        if checked_only is not None:
            query = query.filter(ShoppingItem.is_checked == checked_only)
        
        return query.order_by(ShoppingItem.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def remove_item(db: Session, item_id: int) -> bool:
        """Remove item from shopping list"""
        item = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
        if not item:
            return False
        
        db.delete(item)
        db.commit()
        return True
    
    @staticmethod
    def check_items(
        db: Session,
        item_ids: List[int],
        checked_by: int
    ) -> List[ShoppingItem]:
        """Mark items as checked"""
        items = db.query(ShoppingItem).filter(
            ShoppingItem.id.in_(item_ids)
        ).all()
        
        for item in items:
            item.is_checked = True
            item.checked_at = datetime.utcnow()
            item.checked_by = checked_by
        
        db.commit()
        return items
    
    @staticmethod
    def create_shopping_expense(
        db: Session,
        item_ids: List[int],
        total_amount: float,
        currency: Currency,
        payer_id: int,
        profile_id: int,
        note: Optional[str] = None
    ) -> dict:
        """
        Create expense from checked shopping items
        
        Returns:
            Dict with expense and checked items
        """
        # Check the items
        checked_items = ShoppingService.check_items(db, item_ids, payer_id)
        
        # Create expense
        expense = ExpenseService.create_expense(
            db=db,
            amount=total_amount,
            currency=currency,
            category=ExpenseCategory.SHOPPING,
            payer_id=payer_id,
            profile_id=profile_id,
            note=note or f"Покупки: {', '.join(item.title for item in checked_items[:3])}"
        )
        
        return {
            'expense': expense,
            'checked_items': checked_items
        }
    
    @staticmethod
    def get_item_by_id(db: Session, item_id: int) -> Optional[ShoppingItem]:
        """Get shopping item by ID"""
        return db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()

#!/usr/bin/env python3
"""
Todo list management service
"""

from sqlalchemy.orm import Session
from models import TodoItem, User
from typing import List, Optional
from datetime import datetime

class TodoService:
    """Service for managing todo items"""
    
    @staticmethod
    def add_item(db: Session, title: str, created_by: int, priority: str = "medium", note: str = None) -> TodoItem:
        """Add new todo item"""
        item = TodoItem(
            title=title.strip(),
            priority=priority,
            note=note.strip() if note else None,
            created_by=created_by
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    
    @staticmethod
    def get_items(db: Session, completed_only: Optional[bool] = None, limit: int = 50) -> List[TodoItem]:
        """Get todo items with optional filtering"""
        query = db.query(TodoItem)
        
        if completed_only is not None:
            query = query.filter(TodoItem.is_completed == completed_only)
        
        return query.order_by(TodoItem.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_item_by_id(db: Session, item_id: int) -> Optional[TodoItem]:
        """Get todo item by ID"""
        return db.query(TodoItem).filter(TodoItem.id == item_id).first()
    
    @staticmethod
    def toggle_item(db: Session, item_id: int, user_id: int) -> bool:
        """Toggle completion status of todo item"""
        item = db.query(TodoItem).filter(TodoItem.id == item_id).first()
        if not item:
            return False
        
        if item.is_completed:
            # Mark as not completed
            item.is_completed = False
            item.completed_at = None
            item.completed_by = None
        else:
            # Mark as completed
            item.is_completed = True
            item.completed_at = datetime.utcnow()
            item.completed_by = user_id
        
        db.commit()
        return True
    
    @staticmethod
    def remove_item(db: Session, item_id: int) -> bool:
        """Remove todo item"""
        item = db.query(TodoItem).filter(TodoItem.id == item_id).first()
        if not item:
            return False
        
        db.delete(item)
        db.commit()
        return True
    
    @staticmethod
    def update_item(db: Session, item_id: int, title: str = None, priority: str = None, note: str = None) -> bool:
        """Update todo item"""
        item = db.query(TodoItem).filter(TodoItem.id == item_id).first()
        if not item:
            return False
        
        if title is not None:
            item.title = title.strip()
        if priority is not None:
            item.priority = priority
        if note is not None:
            item.note = note.strip() if note else None
        
        db.commit()
        return True

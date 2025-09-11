#!/usr/bin/env python3
"""
Force remove user and all related data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_db
from models import User, Expense, ExpenseAllocation, Profile, ProfileMember
from sqlalchemy.orm import Session
from sqlalchemy import text

def force_remove_user(telegram_id: int):
    """Force remove user and all related data using raw SQL"""
    db = next(get_db())
    
    try:
        # Get user info first
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return
        
        user_name = user.first_name or user.username or f'User {user.telegram_id}'
        user_id = user.id
        
        print(f"🔍 Удаляем пользователя: {user_name} (ID: {user_id})")
        
        # Use raw SQL to delete all related data
        print("🗑️  Удаляем все связанные данные...")
        
        # Delete expense allocations
        result = db.execute(text("DELETE FROM expense_allocations WHERE user_id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из expense_allocations")
        
        # Delete expenses paid by this user
        result = db.execute(text("DELETE FROM expenses WHERE payer_id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из expenses")
        
        # Delete profile memberships
        result = db.execute(text("DELETE FROM profile_members WHERE user_id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из profile_members")
        
        # Delete shopping items created by this user
        result = db.execute(text("DELETE FROM shopping_items WHERE created_by = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из shopping_items")
        
        # Delete shopping items checked by this user
        result = db.execute(text("UPDATE shopping_items SET checked_by = NULL WHERE checked_by = :user_id"), {"user_id": user_id})
        print(f"  ✅ Обновлено {result.rowcount} записей в shopping_items (checked_by)")
        
        # Delete todo items created by this user
        result = db.execute(text("DELETE FROM todo_items WHERE created_by = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из todo_items")
        
        # Delete todo items completed by this user
        result = db.execute(text("UPDATE todo_items SET completed_by = NULL WHERE completed_by = :user_id"), {"user_id": user_id})
        print(f"  ✅ Обновлено {result.rowcount} записей в todo_items (completed_by)")
        
        # Delete duty schedules assigned to this user
        result = db.execute(text("DELETE FROM duty_schedules WHERE assigned_user_id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из duty_schedules")
        
        # Delete month snapshots
        result = db.execute(text("DELETE FROM month_snapshots WHERE user_id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удалено {result.rowcount} записей из month_snapshots")
        
        # Finally delete the user
        result = db.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
        print(f"  ✅ Удален пользователь из users")
        
        # Commit all changes
        db.commit()
        print("✅ Все изменения сохранены в базе данных")
        print(f"🎉 Пользователь {user_name} полностью удален из системы!")
        
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Использование: python force_remove_user.py <telegram_id>")
        print("Пример: python force_remove_user.py 396299503")
        return
    
    try:
        telegram_id = int(sys.argv[1])
        force_remove_user(telegram_id)
    except ValueError:
        print("❌ Telegram ID должен быть числом")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()

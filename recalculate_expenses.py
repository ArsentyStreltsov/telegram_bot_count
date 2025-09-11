#!/usr/bin/env python3
"""
Script to recalculate all expenses after user removal
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_db
from models import User, Expense, ExpenseAllocation
from sqlalchemy.orm import Session
from datetime import datetime, date
from utils.texts import get_category_name, get_currency_name, format_amount

def recalculate_all_expenses():
    """Recalculate all expenses using current user base"""
    db = next(get_db())
    
    try:
        print("🔄 Пересчитываем все расходы...")
        
        # Get current month
        current_month = datetime.now().replace(day=1).date()
        
        # Get all expenses for current month
        expenses = db.query(Expense).filter(Expense.month == current_month).all()
        
        print(f"📊 Найдено {len(expenses)} расходов для пересчета")
        
        recalculated_count = 0
        
        for expense in expenses:
            print(f"\n🔄 Пересчитываем расход {expense.id}:")
            print(f"  💰 {format_amount(expense.amount, expense.currency)} - {get_category_name(expense.category)}")
            if expense.custom_category_name:
                print(f"  📝 Описание: {expense.custom_category_name}")
            print(f"  💳 Оплатил: {expense.payer.first_name or expense.payer.username or f'User {expense.payer.telegram_id}'}")
            
            # Delete all current allocations for this expense
            deleted_allocations = db.query(ExpenseAllocation).filter(
                ExpenseAllocation.expense_id == expense.id
            ).delete()
            print(f"  🗑️  Удалено {deleted_allocations} старых записей о долгах")
            
            # Recalculate allocations using special split logic
            from services.special_split import calculate_special_split
            allocations = calculate_special_split(db, expense.amount, expense.category, expense.profile_id)
            
            print(f"  👥 Новое распределение между {len(allocations)} участниками:")
            
            # Create new allocations
            for user_id, share_amount in allocations.items():
                # Get user info
                user = db.query(User).filter(User.id == user_id).first()
                user_name = user.first_name or user.username or f'User {user.telegram_id}'
                
                # Convert share_amount to SEK if needed
                if expense.currency.value == 'SEK':
                    share_amount_sek = share_amount
                else:
                    share_amount_sek = share_amount * expense.exchange_rate
                
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount_sek=share_amount_sek,
                    weight_used=1.0
                )
                db.add(allocation)
                
                print(f"    • {user_name}: {share_amount_sek:.2f} SEK")
            
            recalculated_count += 1
        
        # Commit all changes
        db.commit()
        print(f"\n✅ Пересчитано {recalculated_count} расходов")
        print("🎉 Все долги пересчитаны без участия удаленного пользователя!")
        
        # Show summary
        print("\n📊 Сводка по текущим участникам:")
        users = db.query(User).all()
        for user in users:
            user_name = user.first_name or user.username or f'User {user.telegram_id}'
            
            # Calculate user's balance
            paid_expenses = db.query(Expense).filter(
                Expense.payer_id == user.id,
                Expense.month == current_month
            ).all()
            
            allocations = db.query(ExpenseAllocation).join(Expense).filter(
                ExpenseAllocation.user_id == user.id,
                Expense.month == current_month
            ).all()
            
            total_paid = sum(exp.amount_sek for exp in paid_expenses)
            total_owed = sum(allocation.amount_sek for allocation in allocations)
            net_balance = total_paid - total_owed
            
            print(f"  👤 {user_name}:")
            print(f"    💳 Оплачено: {total_paid:.2f} SEK")
            print(f"    💸 Должен: {total_owed:.2f} SEK")
            print(f"    ⚖️  Баланс: {net_balance:.2f} SEK")
        
    except Exception as e:
        print(f"❌ Ошибка при пересчете расходов: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """Main function"""
    recalculate_all_expenses()

if __name__ == "__main__":
    main()

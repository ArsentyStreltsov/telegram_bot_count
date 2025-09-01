"""
Reports and balances handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import back_keyboard, confirmation_keyboard
from utils.texts import format_expense_report, format_balance_report
from services.expense_service import ExpenseService
from services.split import SplitService
from models import User, Expense
from datetime import datetime

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get expenses by category for current month
        expenses_by_category = ExpenseService.get_expenses_by_category(db)
        current_month = datetime.now()
        
        if not expenses_by_category:
            text = "📊 Отчет за текущий месяц\n\nНет расходов в этом месяце"
        else:
            text = format_expense_report(expenses_by_category, current_month)
        
        keyboard = back_keyboard("main_menu")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def balances_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balances button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Calculate balances
        balances = SplitService.calculate_user_balances(db)
        
        if not balances:
            text = "💳 Балансы\n\nНет данных для расчета балансов"
            keyboard = back_keyboard("main_menu")
        else:
            # Get user details
            user_ids = list(balances.keys())
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            users_dict = {user.id: user for user in users}
            
            # Calculate settlement plan
            settlements = SplitService.calculate_settlement_plan(db, balances)
            
            text = format_balance_report(balances, users_dict, settlements)
            keyboard = back_keyboard("main_menu")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def delete_expenses_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete expenses button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get current month expenses
        current_month = datetime.now().replace(day=1).date()
        expenses = db.query(Expense).filter(Expense.month == current_month).all()
        
        if not expenses:
            text = "🗑 Удаление расходов\n\nНет расходов в текущем месяце для удаления"
            keyboard = back_keyboard("main_menu")
        else:
            text = "🗑 Выберите расход для удаления:\n\n"
            for i, expense in enumerate(expenses, 1):
                # Get payer name
                payer = db.query(User).filter(User.id == expense.payer_id).first()
                payer_name = payer.first_name or payer.username or f"User {expense.payer_id}" if payer else "Unknown"
                
                # Format amount
                from utils.texts import format_amount, get_currency_name
                amount_text = f"{format_amount(expense.amount, expense.currency)}"
                
                # Format category
                from utils.texts import get_category_name
                category_name = get_category_name(expense.category)
                if expense.custom_category_name:
                    category_name = expense.custom_category_name
                
                text += f"{i}. {category_name} - {amount_text} ({payer_name})\n"
            
            # Create keyboard with expense selection
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = []
            for i, expense in enumerate(expenses, 1):
                keyboard.append([InlineKeyboardButton(
                    f"{i}. {expense.amount} {expense.currency.value}", 
                    callback_data=f"delete_expense_{expense.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def delete_expense_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete specific expense confirmation"""
    query = update.callback_query
    await query.answer()
    
    # Parse expense ID from callback data
    callback_data = query.data
    if not callback_data.startswith("delete_expense_"):
        return
    
    try:
        expense_id = int(callback_data.replace("delete_expense_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID расхода")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get expense details
        expense = ExpenseService.get_expense_by_id(db, expense_id)
        if not expense:
            await query.edit_message_text("❌ Расход не найден")
            return
        
        # Get payer name
        payer = db.query(User).filter(User.id == expense.payer_id).first()
        payer_name = payer.first_name or payer.username or f"User {expense.payer_id}" if payer else "Unknown"
        
        # Format amount
        from utils.texts import format_amount, get_currency_name
        amount_text = f"{format_amount(expense.amount, expense.currency)}"
        
        # Format category
        from utils.texts import get_category_name
        category_name = get_category_name(expense.category)
        if expense.custom_category_name:
            category_name = expense.custom_category_name
        
        text = f"🗑 Подтвердите удаление расхода:\n\n"
        text += f"📂 Категория: {category_name}\n"
        text += f"💰 Сумма: {amount_text}\n"
        text += f"💳 Оплатил: {payer_name}\n"
        text += f"📅 Дата: {expense.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        text += "⚠️ Это действие нельзя отменить!"
        
        keyboard = confirmation_keyboard(f"delete_expense_{expense_id}")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def confirm_delete_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense deletion confirmation"""
    query = update.callback_query
    await query.answer()
    
    # Parse expense ID from callback data
    callback_data = query.data
    
    if not callback_data.startswith("confirm_delete_expense_"):
        return
    
    try:
        expense_id = int(callback_data.replace("confirm_delete_expense_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID расхода")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Delete expense
        success = ExpenseService.delete_expense(db, expense_id)
        
        if not success:
            await query.edit_message_text("❌ Ошибка при удалении расхода")
            return
        
        # Return to expenses list
        await delete_expenses_callback(update, context)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка при удалении: {str(e)}")
    finally:
        db.close()

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel button"""
    query = update.callback_query
    await query.answer()
    
    # Return to main menu
    from utils.keyboards import main_menu_keyboard
    text = "🔙 Возврат в главное меню"
    keyboard = main_menu_keyboard()
    
    await query.edit_message_text(text, reply_markup=keyboard)



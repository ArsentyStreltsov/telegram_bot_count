"""
Reports and balances handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import back_keyboard
from utils.texts import format_expense_report, format_balance_report
from services.expense_service import ExpenseService
from services.split import SplitService
from models import User
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

async def exchange_rates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle exchange rates button"""
    query = update.callback_query
    await query.answer()
    
    text = "💱 Курсы валют\n\nИспользуйте команду:\n/set_rate EUR 11.30\n\nдля установки курса EUR к SEK"
    keyboard = back_keyboard("main_menu")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def close_month_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle close month button"""
    query = update.callback_query
    await query.answer()
    
    text = "📅 Закрытие месяца\n\nФункция в разработке..."
    keyboard = back_keyboard("main_menu")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def profiles_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profiles button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get profiles
        from models import Profile
        profiles = db.query(Profile).all()
        
        if not profiles:
            text = "👥 Профили\n\nНет доступных профилей"
        else:
            text = "👥 Профили разделения расходов:\n\n"
            for profile in profiles:
                text += f"• {profile.name}"
                if profile.is_default:
                    text += " (по умолчанию)"
                if profile.description:
                    text += f" - {profile.description}"
                text += "\n"
        
        keyboard = back_keyboard("main_menu")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

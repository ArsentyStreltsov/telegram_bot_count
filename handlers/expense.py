"""
Expense handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import category_keyboard, back_keyboard, currency_selection_keyboard, expenses_menu_keyboard
from utils.texts import get_category_name, get_currency_name, format_amount
from services.expense_service import ExpenseService
from models import ExpenseCategory, Currency, Profile
import re

# User state storage moved to context.bot_data

async def expenses_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expenses menu button"""
    query = update.callback_query
    await query.answer()
    
    text = "💰 Меню расходов\n\nВыберите действие:"
    keyboard = expenses_menu_keyboard()
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def add_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add expense button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        # Set user state to ask for currency first
        user_id = update.effective_user.id
        if 'user_states' not in context.bot_data:
            context.bot_data['user_states'] = {}
        
        context.bot_data['user_states'][user_id] = {
            'action': 'add_expense',
            'step': 'currency'
        }
        
        # Ask for currency first
        text = "💱 Выберите валюту:"
        keyboard = currency_selection_keyboard()
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse category from callback data
    callback_data = query.data
    if not callback_data.startswith("category_"):
        return
    
    category_value = callback_data.replace("category_", "")
    try:
        category = ExpenseCategory(category_value)
    except ValueError:
        await query.edit_message_text("❌ Неверная категория")
        return
    
    # Update user state with category
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    user_states[user_id]['category'] = category
    
    # Special handling for "OTHER" category - ask for custom name
    if category == ExpenseCategory.OTHER:
        user_states[user_id]['step'] = 'custom_category'
        
        text = f"💰 Сумма: {format_amount(user_states[user_id]['amount'], user_states[user_id]['currency'])}\n"
        text += f"📂 Категория: {get_category_name(category)}\n\n"
        text += "✏️ Введите описание покупки:\n"
        text += "Например: билеты, такси, ресторан, кино"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("add_expense")
        
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        # Create expense directly without profile selection
        # Get database session
        db = next(get_db())
        
        try:
            # Get default profile (Home) or create one if doesn't exist
            profile = db.query(Profile).filter(Profile.name == "Home").first()
            if not profile:
                # Create default profile if it doesn't exist
                profile = Profile(name="Home", is_default=True)
                db.add(profile)
                db.commit()
                db.refresh(profile)
            
            # Get user
            user = BaseHandler.get_or_create_user(db, update.effective_user)
            
            # Store values before clearing state
            amount = user_states[user_id]['amount']
            currency = user_states[user_id]['currency']
            custom_category_name = user_states[user_id].get('custom_category_name')
            
            # Create expense with special splitting logic
            from services.special_split import calculate_special_split
            
            # Calculate allocations based on category
            allocations = calculate_special_split(db, amount, category, profile.id)
            
            # Create expense
            expense = ExpenseService.create_expense(
                db=db,
                amount=amount,
                currency=currency,
                category=category,
                payer_id=user.id,
                profile_id=profile.id,
                allocations=allocations,
                custom_category_name=custom_category_name
            )
            
            # Clear user state
            del context.bot_data['user_states'][user_id]
            
            # Show success message
            text = f"✅ Расход добавлен!\n\n"
            if custom_category_name:
                text += f"📂 Категория: {get_category_name(category)}: {custom_category_name}\n"
            else:
                text += f"📂 Категория: {get_category_name(category)}\n"
            text += f"💱 Валюта: {get_currency_name(currency)}\n"
            text += f"💰 Сумма: {format_amount(amount, currency)}\n"
            text += f"💳 Оплатил: {BaseHandler.get_user_name(user)}"
            
            from utils.keyboards import back_keyboard
            keyboard = back_keyboard("main_menu")
            
            await query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при создании расхода: {str(e)}")
        finally:
            db.close()



async def handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input"""
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        return
    
    amount_str = update.message.text
    amount = BaseHandler.validate_amount(amount_str)
    
    if amount is None:
        await update.message.reply_text(
            "❌ Неверный формат суммы. Введите положительное число (например: 100.50)"
        )
        return
    
    # Update user state with amount
    user_states[user_id]['amount'] = amount
    user_states[user_id]['step'] = 'category'
    
    # Show category selection
    currency = user_states[user_id]['currency']
    text = f"💱 Валюта: {get_currency_name(currency)}\n"
    text += f"💰 Сумма: {format_amount(amount, currency)}\n\n"
    text += "📂 Выберите категорию расхода:"
    
    from utils.keyboards import category_keyboard
    keyboard = category_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse currency from callback data
    callback_data = query.data
    if not callback_data.startswith("currency_"):
        return
    
    currency_value = callback_data.replace("currency_", "")
    try:
        currency = Currency(currency_value)
    except ValueError:
        await query.edit_message_text("❌ Неверная валюта")
        return
    
    # Update user state with currency
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    user_states[user_id]['currency'] = currency
    user_states[user_id]['step'] = 'amount'
    
    # Ask for amount
    text = f"💱 Валюта: {get_currency_name(currency)}\n\n"
    text += "💰 Введите сумму:"
    
    keyboard = back_keyboard("add_expense")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def split_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle split choice for OTHER category expenses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    # Parse split type from callback data
    callback_data = query.data
    if not callback_data.startswith("split_"):
        return
    
    split_type = callback_data
    user_states[user_id]['split_type'] = split_type
    
    # Create expense with chosen split
    db = next(get_db())
    
    try:
        # Get default profile (Home)
        profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not profile:
            # Create default profile if it doesn't exist
            profile = Profile(name="Home", is_default=True)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        # Get user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        # Get values from state
        amount = user_states[user_id]['amount']
        currency = user_states[user_id]['currency']
        category = user_states[user_id]['category']
        custom_category_name = user_states[user_id]['custom_category_name']
        
        # Create expense with flexible splitting logic
        from services.flexible_split import FlexibleSplitService
        
        # Calculate allocations based on split choice
        allocations = FlexibleSplitService.calculate_flexible_split(
            db, amount, split_type, profile.id, user.telegram_id
        )
        
        # Create expense
        expense = ExpenseService.create_expense(
            db=db,
            amount=amount,
            currency=currency,
            category=category,
            payer_id=user.id,
            profile_id=profile.id,
            allocations=allocations,
            custom_category_name=custom_category_name
        )
        
        # Clear user state
        del context.bot_data['user_states'][user_id]
        
        # Show success message
        split_description = FlexibleSplitService.get_split_description(split_type)
        text = f"✅ Расход добавлен!\n\n"
        text += f"📂 Категория: {custom_category_name}\n"
        text += f"💱 Валюта: {get_currency_name(currency)}\n"
        text += f"💰 Сумма: {format_amount(amount, currency)}\n"
        text += f"👥 Разделение: {split_description}\n"
        text += f"💳 Оплатил: {BaseHandler.get_user_name(user)}"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("main_menu")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка при создании расхода: {str(e)}")
    finally:
        db.close()



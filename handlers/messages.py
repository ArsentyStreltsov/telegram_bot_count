"""
Universal message handler for text input
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import back_keyboard, category_keyboard
from services.shopping_service import ShoppingService
from models import ExpenseCategory, Profile

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages based on user state"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Get user state from context
    user_states = context.bot_data.get('user_states', {})
    user_state = user_states.get(user_id, {})
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        if user_state.get('action') == 'add_shopping_item':
            await handle_shopping_item_input(update, context, db, user, text, user_state)
        elif user_state.get('action') == 'add_expense':
            if user_state.get('step') == 'custom_category':
                await handle_custom_category_input(update, context, db, user, text, user_state)
            else:
                await handle_expense_amount_input(update, context, db, user, text, user_state)
        else:
            # Unknown state, send back to main menu
            await update.message.reply_text(
                "❌ Неизвестное состояние. Используйте /start для возврата в главное меню."
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def handle_shopping_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session, user, text: str, user_state: dict):
    """Handle shopping item input"""
    user_id = update.effective_user.id
    
    if user_state.get('step') == 'title':
        # Split items by comma and clean them
        items = [item.strip() for item in text.split(',') if item.strip()]
        
        if not items:
            await update.message.reply_text(
                "❌ Не найдено товаров для добавления. Введите названия товаров через запятую."
            )
            return
        
        # Add items directly without asking for category (shopping items don't need categories)
        added_items = []
        for title in items:
            item = ShoppingService.add_item(
                db=db,
                title=title,
                category=ExpenseCategory.FOOD,  # Default category for shopping items
                created_by=user.id
            )
            added_items.append(item)
        
        # Clear user state
        del context.bot_data['user_states'][user_id]
        
        # Show success message
        success_text = f"✅ Добавлено {len(added_items)} товаров в список покупок!\n\n"
        success_text += f"👤 Добавил: {BaseHandler.get_user_name(user)}\n\n"
        success_text += "📝 Товары:\n"
        for item in added_items:
            success_text += f"• {item.title}\n"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("shopping_list")
        
        await update.message.reply_text(success_text, reply_markup=keyboard)

async def handle_custom_category_input(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session, user, text: str, user_state: dict):
    """Handle custom category name input for OTHER category"""
    user_id = update.effective_user.id
    
    # Store custom category name
    user_state['custom_category_name'] = text.strip()
    user_state['step'] = 'split_choice'
    
    # Update state in context
    context.bot_data['user_states'][user_id] = user_state
    
    # Ask for split choice
    from utils.texts import get_category_name, get_currency_name, format_amount
    from utils.keyboards import split_choice_keyboard
    
    text = f"💰 Сумма: {format_amount(user_state['amount'], user_state['currency'])}\n"
    text += f"📂 Категория: {user_state['custom_category_name']}\n\n"
    text += "👥 Выберите, как разделить расход:\n\n"
    text += "P.S. если ты заплатил за другого и расход делить не надо - выбирай 'без разделения'"
    
    keyboard = split_choice_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def handle_expense_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session, user, text: str, user_state: dict):
    """Handle expense amount input (existing functionality)"""
    from handlers.expense import handle_amount_input
    await handle_amount_input(update, context)

async def handle_shopping_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection for expenses (not shopping items)"""
    # This is only for expense category selection
    from handlers.expense import category_callback
    await category_callback(update, context)

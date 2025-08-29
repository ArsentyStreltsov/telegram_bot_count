"""
Shopping list handlers
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import shopping_actions_keyboard, back_keyboard
from utils.texts import format_shopping_list, get_category_name
from services.shopping_service import ShoppingService
from models import ExpenseCategory

async def shopping_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shopping list button"""
    query = update.callback_query
    await query.answer()
    
    text = "🛒 Управление списком покупок\n\nВыберите действие:"
    keyboard = shopping_actions_keyboard()
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def add_shopping_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add shopping item button"""
    query = update.callback_query
    await query.answer()
    
    # Store state for adding item
    user_id = update.effective_user.id
    if 'user_states' not in context.bot_data:
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {
        'action': 'add_shopping_item',
        'step': 'title'
    }
    
    text = "➕ Добавление товаров в список покупок\n\nВведите названия товаров через запятую:\n\nПример: Молоко, Хлеб, Яйца, Сыр"
    keyboard = back_keyboard("shopping_list")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def list_shopping_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle list shopping items button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get shopping items
        items = ShoppingService.get_items(db, checked_only=False, limit=20)
        
        if not items:
            text = "🛒 Список покупок пуст"
            keyboard = back_keyboard("shopping_list")
        else:
            text = format_shopping_list(items)
            keyboard = create_shopping_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def go_shopping_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle go shopping button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get unchecked items
        items = ShoppingService.get_items(db, checked_only=False, limit=20)
        
        if not items:
            text = "🛒 Нет товаров для покупки"
            keyboard = back_keyboard("shopping_list")
        else:
            text = "🛒 Выберите купленные товары:\n\n"
            for i, item in enumerate(items, 1):
                text += f"{i}. {item.title}\n"
            
            # Store items for selection
            user_id = update.effective_user.id
            if 'user_states' not in context.bot_data:
                context.bot_data['user_states'] = {}
            
            context.bot_data['user_states'][user_id] = {
                'action': 'go_shopping',
                'items': items
            }
            
            keyboard = back_keyboard("shopping_list")
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def remove_shopping_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove shopping item button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get shopping items
        items = ShoppingService.get_items(db, checked_only=False, limit=20)
        
        if not items:
            text = "🛒 Список покупок пуст"
            keyboard = back_keyboard("shopping_list")
        else:
            text = "🗑 Выберите товар для удаления:\n\n"
            for i, item in enumerate(items, 1):
                text += f"{i}. {item.title}\n"
            
            keyboard = create_remove_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def toggle_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle toggle item (check/uncheck)"""
    query = update.callback_query
    await query.answer()
    
    # Parse item ID from callback data
    callback_data = query.data
    if not callback_data.startswith("toggle_"):
        return
    
    try:
        item_id = int(callback_data.replace("toggle_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID товара")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get item
        item = ShoppingService.get_item_by_id(db, item_id)
        if not item:
            await query.edit_message_text("❌ Товар не найден")
            return
        
        # Toggle checked status
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        if item.is_checked:
            # Uncheck item
            item.is_checked = False
            item.checked_at = None
            item.checked_by = None
            status_text = "⭕ Отмечено как не купленное"
        else:
            # Check item
            item.is_checked = True
            from datetime import datetime
            item.checked_at = datetime.utcnow()
            item.checked_by = user.id
            status_text = "✅ Отмечено как купленное"
        
        db.commit()
        
        # Show updated list
        items = ShoppingService.get_items(db, checked_only=False, limit=20)
        
        if not items:
            text = "🛒 Список покупок пуст"
            keyboard = back_keyboard("shopping_list")
        else:
            text = format_shopping_list(items)
            keyboard = create_shopping_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

async def remove_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove specific item"""
    query = update.callback_query
    await query.answer()
    
    # Parse item ID from callback data
    callback_data = query.data
    if not callback_data.startswith("remove_"):
        return
    
    try:
        item_id = int(callback_data.replace("remove_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID товара")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Remove item
        success = ShoppingService.remove_item(db, item_id)
        
        if not success:
            await query.edit_message_text("❌ Товар не найден")
            return
        
        # Show updated list
        items = ShoppingService.get_items(db, checked_only=False, limit=20)
        
        if not items:
            text = "🛒 Список покупок пуст"
            keyboard = back_keyboard("shopping_list")
        else:
            text = "🗑 Выберите товар для удаления:\n\n"
            for i, item in enumerate(items, 1):
                text += f"{i}. {item.title}\n"
            
            keyboard = create_remove_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

def create_shopping_items_keyboard(items):
    """Create keyboard with toggle buttons for shopping items"""
    keyboard = []
    
    for item in items:
        status = "✅" if item.is_checked else "⭕"
        button_text = f"{status} {item.title}"
        callback_data = f"toggle_{item.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="shopping_list")])
    return InlineKeyboardMarkup(keyboard)

def create_remove_items_keyboard(items):
    """Create keyboard with remove buttons for shopping items"""
    keyboard = []
    
    for item in items:
        button_text = f"🗑 {item.title}"
        callback_data = f"remove_{item.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="shopping_list")])
    return InlineKeyboardMarkup(keyboard)

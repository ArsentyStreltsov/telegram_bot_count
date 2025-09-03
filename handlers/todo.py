#!/usr/bin/env python3
"""
Todo list handlers
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import back_keyboard
from services.todo_service import TodoService

def handle_db_error(e: Exception, action: str) -> tuple[str, InlineKeyboardMarkup]:
    """Handle database errors with user-friendly messages"""
    error_text = f"❌ Ошибка при {action}"
    
    # Check if it's a database connection error
    if "server closed the connection" in str(e) or "psycopg2.OperationalError" in str(e):
        error_text += "\n\n🔄 Проблема с подключением к базе данных.\nПопробуйте еще раз через несколько секунд."
    else:
        error_text += f"\n\n{str(e)}"
    
    keyboard = back_keyboard("main_menu")
    return error_text, keyboard

async def todo_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle todo list button"""
    query = update.callback_query
    await query.answer()
    
    text = "📝 Управление списком дел\n\nВыберите действие:"
    keyboard = todo_actions_keyboard()
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def add_todo_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add todo item button"""
    query = update.callback_query
    await query.answer()
    
    # Store state for adding item
    user_id = update.effective_user.id
    if 'user_states' not in context.bot_data:
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {
        'action': 'add_todo_item',
        'step': 'title'
    }
    
    text = "➕ Добавление дел в список\n\nВведите названия дел через запятую:\n\nПример: Поточить ножи, Помыть пол, Почистить ковер"
    keyboard = back_keyboard("todo_list")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def list_todo_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle list todo items button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get todo items - get ALL items (both completed and uncompleted)
        items = TodoService.get_items(db, completed_only=None, limit=20)
        
        if not items:
            text = "📝 Список дел пуст"
            keyboard = back_keyboard("todo_list")
        else:
            text = format_todo_list(items, db)
            keyboard = create_todo_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "загрузке списка дел")
        await query.edit_message_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

async def remove_todo_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove todo item button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get todo items - get ALL items (both completed and uncompleted)
        items = TodoService.get_items(db, completed_only=None, limit=20)
        
        if not items:
            text = "📝 Список дел пуст"
            keyboard = back_keyboard("todo_list")
        else:
            text = "🗑 Выберите дело для удаления:\n\n"
            for i, item in enumerate(items, 1):
                status = "✅" if item.is_completed else "⭕"
                text += f"{i}. {status} {item.title}\n"
            
            keyboard = create_remove_todo_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "загрузке списка дел")
        await query.edit_message_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

async def toggle_todo_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle toggle todo item (complete/uncomplete)"""
    query = update.callback_query
    await query.answer()
    
    # Parse item ID from callback data
    callback_data = query.data
    if not callback_data.startswith("toggle_todo_"):
        return
    
    try:
        item_id = int(callback_data.replace("toggle_todo_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID дела")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get item
        item = TodoService.get_item_by_id(db, item_id)
        if not item:
            await query.edit_message_text("❌ Дело не найдено")
            return
        
        # Toggle completed status
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        if item.is_completed:
            # Mark as not completed
            item.is_completed = False
            item.completed_at = None
            item.completed_by = None
            status_text = "⭕ Отмечено как не выполненное"
        else:
            # Mark as completed
            item.is_completed = True
            from datetime import datetime
            item.completed_at = datetime.utcnow()
            item.completed_by = user.id
            status_text = "✅ Отмечено как выполненное"
        
        db.commit()
        
        # Show updated list - get ALL items (both completed and uncompleted)
        items = TodoService.get_items(db, completed_only=None, limit=20)
        
        if not items:
            text = "📝 Список дел пуст"
            keyboard = back_keyboard("todo_list")
        else:
            text = format_todo_list(items, db)
            keyboard = create_todo_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "обновлении списка дел")
        await query.edit_message_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

async def remove_todo_item_specific_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove specific todo item"""
    query = update.callback_query
    await query.answer()
    
    # Parse item ID from callback data
    callback_data = query.data
    if not callback_data.startswith("remove_todo_"):
        return
    
    try:
        item_id = int(callback_data.replace("remove_todo_", ""))
    except ValueError:
        await query.edit_message_text("❌ Неверный ID дела")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Remove item
        success = TodoService.remove_item(db, item_id)
        
        if not success:
            await query.edit_message_text("❌ Дело не найдено")
            return
        
        # Show updated list - get ALL items (both completed and uncompleted)
        items = TodoService.get_items(db, completed_only=None, limit=20)
        
        if not items:
            text = "📝 Список дел пуст"
            keyboard = back_keyboard("todo_list")
        else:
            text = "🗑 Выберите дело для удаления:\n\n"
            for i, item in enumerate(items, 1):
                status = "✅" if item.is_completed else "⭕"
                text += f"{i}. {status} {item.title}\n"
            
            keyboard = create_remove_todo_items_keyboard(items)
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "удалении дела")
        await query.edit_message_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

async def handle_todo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle todo item input"""
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_todo_item':
        return
    
    text = update.message.text
    if not text.strip():
        await update.message.reply_text("❌ Введите название дела")
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        # Split by comma and add each item
        items = [item.strip() for item in text.split(',') if item.strip()]
        added_count = 0
        
        for item_title in items:
            TodoService.add_item(db, item_title, user.id)
            added_count += 1
        
        # Clear user state
        del context.bot_data['user_states'][user_id]
        
        # Show success message
        if added_count == 1:
            text = f"✅ Добавлено дело: {items[0]}"
        else:
            text = f"✅ Добавлено дел: {added_count}\n\n"
            for i, item in enumerate(items, 1):
                text += f"{i}. {item}\n"
        
        keyboard = back_keyboard("todo_list")
        await update.message.reply_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "добавлении дела")
        await update.message.reply_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

def create_todo_items_keyboard(items):
    """Create keyboard with toggle buttons for todo items"""
    keyboard = []
    
    for item in items:
        # Показываем кнопку только для невыполненных дел
        if not item.is_completed:
            button_text = f"⭕ {item.title}"
            callback_data = f"toggle_todo_{item.id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="todo_list")])
    return InlineKeyboardMarkup(keyboard)

def create_remove_todo_items_keyboard(items):
    """Create keyboard with remove buttons for todo items"""
    keyboard = []
    
    for item in items:
        button_text = f"🗑 {item.title}"
        callback_data = f"remove_todo_{item.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="todo_list")])
    return InlineKeyboardMarkup(keyboard)

def todo_actions_keyboard():
    """Create keyboard for todo actions"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить дело", callback_data="add_todo_item")],
        [InlineKeyboardButton("📋 Список дел", callback_data="list_todo_items")],
        [InlineKeyboardButton("🗑 Удалить дело", callback_data="remove_todo_item")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_todo_list(items, db):
    """Format todo list for display"""
    if not items:
        return "📝 Список дел пуст"
    
    text = "📝 Список дел:\n\n"
    
    for i, item in enumerate(items, 1):
        status = "✅" if item.is_completed else "⭕"
        priority_emoji = {
            "low": "🟢",
            "medium": "🟡", 
            "high": "🔴"
        }.get(item.priority, "🟡")
        
        text += f"{i}. {status} {priority_emoji} {item.title}\n"
        
        if item.note:
            text += f"   📝 {item.note}\n"
        
        if item.is_completed and item.completed_by:
            # Get user name from database
            completed_user = db.query(User).filter(User.id == item.completed_by).first()
            if completed_user:
                text += f"   ✅ Выполнил: {BaseHandler.get_user_name(completed_user)}\n"
        
        text += "\n"
    
    return text

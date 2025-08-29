"""
Start command handler
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import main_menu_keyboard
from utils.texts import get_welcome_message

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        user_name = BaseHandler.get_user_name(user)
        
        # Send welcome message with main menu
        welcome_text = get_welcome_message(user_name)
        keyboard = main_menu_keyboard()
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Произошла ошибка: {str(e)}"
        )
    finally:
        db.close()

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu callback"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        user_name = BaseHandler.get_user_name(user)
        
        # Send main menu
        welcome_text = get_welcome_message(user_name)
        keyboard = main_menu_keyboard()
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ Произошла ошибка: {str(e)}"
        )
    finally:
        db.close()

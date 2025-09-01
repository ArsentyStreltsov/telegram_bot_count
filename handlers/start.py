"""
Start command handler
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import main_menu_keyboard, quick_commands_keyboard
from utils.texts import get_welcome_message

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        user_name = BaseHandler.get_user_name(user)
        
        # Send welcome message with main menu and quick commands keyboard
        welcome_text = get_welcome_message(user_name)
        inline_keyboard = main_menu_keyboard()
        reply_keyboard = quick_commands_keyboard()
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=inline_keyboard
        )
        
        # Send quick commands keyboard
        await update.message.reply_text(
            "⌨️ **Быстрые команды**\n\n"
            "Нажмите кнопку «Меню» для доступа к командам:",
            reply_markup=reply_keyboard
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

async def shopping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shopping command"""
    from utils.keyboards import shopping_actions_keyboard
    
    text = "🛒 Список покупок\n\nВыберите действие:"
    keyboard = shopping_actions_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /expenses command"""
    from utils.keyboards import expenses_menu_keyboard
    
    text = "💰 Меню расходов\n\nВыберите действие:"
    keyboard = expenses_menu_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    from handlers.reports import report_callback
    
    # Create a mock callback query for compatibility
    update.callback_query = type('MockCallbackQuery', (), {
        'data': 'report',
        'answer': lambda: None,
        'edit_message_text': lambda text, reply_markup=None: update.message.reply_text(text, reply_markup=reply_markup)
    })()
    
    await report_callback(update, context)

async def balances_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balances command"""
    from handlers.reports import balances_callback
    
    # Create a mock callback query for compatibility
    update.callback_query = type('MockCallbackQuery', (), {
        'data': 'balances',
        'answer': lambda: None,
        'edit_message_text': lambda text, reply_markup=None: update.message.reply_text(text, reply_markup=reply_markup)
    })()
    
    await balances_callback(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    from utils.texts import get_help_message
    
    help_text = get_help_message()
    
    await update.message.reply_text(help_text)

async def update_commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update_commands command - force update bot commands"""
    try:
        # Force update bot commands
        from telegram import BotCommand
        
        commands = [
            BotCommand("start", "🏠 Главное меню"),
            BotCommand("shopping", "🛒 Список покупок"),
            BotCommand("expenses", "💰 Расходы"),
            BotCommand("report", "📊 Отчет"),
            BotCommand("balances", "💳 Балансы"),
            BotCommand("set_rate", "💱 Установить курс валюты"),
            BotCommand("help", "❓ Справка"),
            BotCommand("update_commands", "🔄 Обновить команды")
        ]
        
        await context.bot.set_my_commands(commands)
        
        text = "✅ Команды бота обновлены!\n\n"
        text += "📱 Теперь в меню Telegram должны появиться:\n"
        for cmd in commands:
            text += f"• /{cmd.command} - {cmd.description}\n"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обновлении команд: {str(e)}")

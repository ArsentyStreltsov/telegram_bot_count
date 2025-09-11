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
from utils.access_control import AccessControl, require_access, require_access_for_callback
from models import User, Profile, ProfileMember

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    # Check access first
    if not AccessControl.check_access(update, context):
        AccessControl.log_access_attempt(update, context)
        await AccessControl.deny_access_message(update, context)
        return
    
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

@require_access_for_callback
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

@require_access
async def shopping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shopping command"""
    from utils.keyboards import shopping_actions_keyboard
    
    text = "🛒 Список покупок\n\nВыберите действие:"
    keyboard = shopping_actions_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

@require_access
async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todo command"""
    from handlers.todo import todo_actions_keyboard
    
    text = "📝 Список дел\n\nВыберите действие:"
    keyboard = todo_actions_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

@require_access
async def expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /expenses command"""
    from utils.keyboards import expenses_menu_keyboard
    
    text = "💰 Меню расходов\n\nВыберите действие:"
    keyboard = expenses_menu_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

@require_access
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    from handlers.reports import report_callback
    
    # Create a mock callback query for compatibility
    class MockCallbackQuery:
        def __init__(self, message):
            self.data = 'report'
            self.message = message
        
        async def answer(self):
            pass
        
        async def edit_message_text(self, text, reply_markup=None):
            await self.message.reply_text(text, reply_markup=reply_markup)
    
    # Create mock update with callback_query
    mock_update = type('MockUpdate', (), {
        'callback_query': MockCallbackQuery(update.message),
        'effective_user': update.effective_user
    })()
    
    await report_callback(mock_update, context)

@require_access
async def balances_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balances command - show group balances"""
    from services.group_balance import GroupBalanceService
    
    db = next(get_db())
    try:
        report = GroupBalanceService.get_detailed_balance_report(db)
        await update.message.reply_text(report)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении балансов групп: {str(e)}")
    finally:
        db.close()

@require_access
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    from utils.texts import get_help_message
    
    help_text = get_help_message()
    
    await update.message.reply_text(help_text)

@require_access
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
            BotCommand("group_balances", "👥 Балансы групп"),
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

@require_access
async def group_balances_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /group_balances command - show group balances"""
    from services.group_balance import GroupBalanceService
    
    db = next(get_db())
    try:
        report = GroupBalanceService.get_detailed_balance_report(db)
        await update.message.reply_text(report)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении балансов групп: {str(e)}")
    finally:
        db.close()

@require_access
async def db_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /db_info command - show database information"""
    db = next(get_db())
    
    try:
        # Get users info
        users = db.query(User).all()
        users_text = "👥 **Пользователи в базе:**\n\n"
        
        for user in users:
            users_text += f"• ID: {user.id}\n"
            users_text += f"  Telegram ID: {user.telegram_id}\n"
            users_text += f"  Username: @{user.username or 'нет'}\n"
            users_text += f"  Имя: {user.first_name or 'нет'}\n"
            users_text += f"  Фамилия: {user.last_name or 'нет'}\n"
            users_text += f"  Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            users_text += f"  Админ: {'Да' if user.is_admin else 'Нет'}\n\n"
        
        # Get profiles info
        profiles = db.query(Profile).all()
        profiles_text = "🏠 **Профили:**\n\n"
        
        for profile in profiles:
            profiles_text += f"• ID: {profile.id}\n"
            profiles_text += f"  Название: {profile.name}\n"
            profiles_text += f"  Описание: {profile.description or 'нет'}\n"
            profiles_text += f"  По умолчанию: {'Да' if profile.is_default else 'Нет'}\n"
            profiles_text += f"  Дата создания: {profile.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            
            # Get profile members
            members = db.query(ProfileMember).filter(ProfileMember.profile_id == profile.id).all()
            if members:
                profiles_text += "  👥 Участники:\n"
                for member in members:
                    member_user = db.query(User).filter(User.id == member.user_id).first()
                    if member_user:
                        profiles_text += f"    - {member_user.first_name or member_user.username} (вес: {member.weight})\n"
                profiles_text += "\n"
        
        # Get expenses count
        from models import Expense
        expenses_count = db.query(Expense).count()
        expenses_text = f"💰 **Расходы:** {expenses_count} записей\n\n"
        
        # Combine all info
        full_text = users_text + profiles_text + expenses_text
        
        # Split if too long
        if len(full_text) > 4000:
            await update.message.reply_text(users_text)
            await update.message.reply_text(profiles_text)
            await update.message.reply_text(expenses_text)
        else:
            await update.message.reply_text(full_text)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении информации: {str(e)}")
    finally:
        db.close()

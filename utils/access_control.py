"""
Access control utilities for the bot
"""
from telegram import Update
from telegram.ext import ContextTypes
from services.flexible_split import FlexibleSplitService
from typing import List, Set

class AccessControl:
    """Access control for the bot"""
    
    # Whitelist of allowed Telegram user IDs
    ALLOWED_USER_IDS: Set[int] = set(FlexibleSplitService.GROUP_1_IDS + FlexibleSplitService.GROUP_2_IDS)
    
    @classmethod
    def is_user_allowed(cls, telegram_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        return telegram_id in cls.ALLOWED_USER_IDS
    
    @classmethod
    def get_allowed_users(cls) -> List[int]:
        """Get list of all allowed user IDs"""
        return list(cls.ALLOWED_USER_IDS)
    
    @classmethod
    def check_access(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user has access to the bot"""
        if not update.effective_user:
            return False
        
        telegram_id = update.effective_user.id
        return cls.is_user_allowed(telegram_id)
    
    @classmethod
    async def deny_access_message(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send access denied message"""
        if update.message:
            await update.message.reply_text(
                "🚫 Доступ запрещен!\n\n"
                "Этот бот предназначен только для членов семьи.\n"
                "Если вы считаете, что получили это сообщение по ошибке, "
                "обратитесь к администратору."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "🚫 Доступ запрещен!",
                show_alert=True
            )
    
    @classmethod
    def get_access_denied_message(cls) -> str:
        """Get access denied message text"""
        return (
            "🚫 Доступ запрещен!\n\n"
            "Этот бот предназначен только для членов семьи.\n"
            "Если вы считаете, что получили это сообщение по ошибке, "
            "обратитесь к администратору."
        )
    
    @classmethod
    def log_access_attempt(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log access attempt for monitoring"""
        if not update.effective_user:
            return
        
        user = update.effective_user
        telegram_id = user.id
        username = user.username or "не указан"
        first_name = user.first_name or "не указано"
        
        # Log to console (in production, you might want to log to a file or database)
        print(f"🚫 ACCESS DENIED: User {first_name} (@{username}, ID: {telegram_id}) attempted to access the bot")
        
        # You can also log to context.bot_data for monitoring
        if 'access_attempts' not in context.bot_data:
            context.bot_data['access_attempts'] = []
        
        context.bot_data['access_attempts'].append({
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'timestamp': context.bot_data.get('current_time', 'unknown')
        })
        
        # Keep only last 100 attempts to prevent memory issues
        if len(context.bot_data['access_attempts']) > 100:
            context.bot_data['access_attempts'] = context.bot_data['access_attempts'][-100:]

def require_access(func):
    """Decorator to require access for command handlers"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not AccessControl.check_access(update, context):
            AccessControl.log_access_attempt(update, context)
            await AccessControl.deny_access_message(update, context)
            return
        
        return await func(update, context)
    
    return wrapper

def require_access_for_callback(func):
    """Decorator to require access for callback handlers"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not AccessControl.check_access(update, context):
            AccessControl.log_access_attempt(update, context)
            if update.callback_query:
                await update.callback_query.answer(
                    "🚫 Доступ запрещен!",
                    show_alert=True
                )
            return
        
        return await func(update, context)
    
    return wrapper

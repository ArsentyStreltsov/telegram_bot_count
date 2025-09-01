"""
Menu and commands handler
"""
from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import commands_list_keyboard
# Import will be done inside functions to avoid circular imports

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Menu button press - show commands list"""
    text = "📋 **Доступные команды:**\n\n"
    text += "Выберите команду из списка ниже:"
    
    keyboard = commands_list_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

# Пока не нужен - убираем сложную логику

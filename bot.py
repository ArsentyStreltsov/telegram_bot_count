"""
Main bot application
"""
import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
from db import init_db
from handlers.start import (
    start_command, main_menu_callback, shopping_command, todo_command,
    expenses_command, report_command, balances_command, help_command,
    update_commands_command, db_info_command, group_balances_command
)
# Убрали обработчик меню
from handlers.expense import (
    expenses_menu_callback, add_expense_callback, handle_amount_input, currency_callback, split_choice_callback
)
from handlers.messages import handle_text_message, handle_shopping_category_callback
from handlers.shopping import (
    shopping_list_callback, add_shopping_item_callback,
    list_shopping_items_callback, remove_shopping_item_callback, 
    toggle_item_callback, remove_item_callback
)
from handlers.todo import (
    todo_list_callback, add_todo_item_callback,
    list_todo_items_callback, remove_todo_item_callback, 
    toggle_todo_item_callback, remove_todo_item_specific_callback,
    handle_todo_input
)
from handlers.reports import (
    report_callback, delete_expenses_callback, 
    delete_expense_confirmation_callback
)
from handlers.commands import set_rate_command
from handlers.duty import (
    duty_schedule_callback, my_duties_callback, monthly_schedule_callback,
    current_week_schedule_callback, mark_completed_callback, complete_duty_callback, generate_schedule_callback
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handlers
WAITING_AMOUNT = 1

def setup_commands(application: Application):
    """Setup bot commands for Telegram menu"""
    from telegram import BotCommand
    
    commands = [
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("shopping", "🛒 Список покупок"),
        BotCommand("todo", "📝 Список дел"),
        BotCommand("expenses", "💰 Расходы"),
        BotCommand("report", "📊 Отчет"),
        BotCommand("set_rate", "💱 Установить курс валюты"),
        BotCommand("help", "❓ Справка"),
        BotCommand("db_info", "🗄️ Информация о БД")
    ]
    
    try:
        application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands set successfully")
        for cmd in commands:
            logger.info(f"   {cmd.command}: {cmd.description}")
    except Exception as e:
        logger.error(f"❌ Failed to set bot commands: {e}")

def setup_handlers(application: Application):
    """Setup all bot handlers"""
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("shopping", shopping_command))
    application.add_handler(CommandHandler("todo", todo_command))
    application.add_handler(CommandHandler("expenses", expenses_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("balances", balances_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("update_commands", update_commands_command))
    application.add_handler(CommandHandler("db_info", db_info_command))
    application.add_handler(CommandHandler("group_balances", group_balances_command))
    application.add_handler(CommandHandler("set_rate", set_rate_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(expenses_menu_callback, pattern="^expenses_menu$"))
    application.add_handler(CallbackQueryHandler(add_expense_callback, pattern="^add_expense$"))
    application.add_handler(CallbackQueryHandler(currency_callback, pattern="^currency_"))
    application.add_handler(CallbackQueryHandler(split_choice_callback, pattern=r"^(participant_[a-z]+|confirm_participants|no_split)$"))
    application.add_handler(CallbackQueryHandler(handle_shopping_category_callback, pattern="^category_"))

    # Shopping handlers
    application.add_handler(CallbackQueryHandler(shopping_list_callback, pattern="^shopping_list$"))
    application.add_handler(CallbackQueryHandler(add_shopping_item_callback, pattern="^add_shopping_item$"))
    application.add_handler(CallbackQueryHandler(list_shopping_items_callback, pattern="^list_shopping_items$"))
    application.add_handler(CallbackQueryHandler(remove_shopping_item_callback, pattern="^remove_shopping_item$"))
    application.add_handler(CallbackQueryHandler(toggle_item_callback, pattern="^toggle_shopping_"))
    application.add_handler(CallbackQueryHandler(remove_item_callback, pattern="^remove_shopping_"))
    
    # Todo handlers
    application.add_handler(CallbackQueryHandler(todo_list_callback, pattern="^todo_list$"))
    application.add_handler(CallbackQueryHandler(add_todo_item_callback, pattern="^add_todo_item$"))
    application.add_handler(CallbackQueryHandler(list_todo_items_callback, pattern="^list_todo_items$"))
    application.add_handler(CallbackQueryHandler(remove_todo_item_callback, pattern="^remove_todo_item$"))
    application.add_handler(CallbackQueryHandler(toggle_todo_item_callback, pattern="^toggle_todo_"))
    application.add_handler(CallbackQueryHandler(remove_todo_item_specific_callback, pattern="^remove_todo_"))
    
    # Report handlers
    application.add_handler(CallbackQueryHandler(report_callback, pattern="^report$"))
    application.add_handler(CallbackQueryHandler(delete_expenses_callback, pattern="^delete_expenses$"))
    application.add_handler(CallbackQueryHandler(delete_expense_confirmation_callback, pattern="^delete_expense_"))
    
    # Duty schedule handlers
    application.add_handler(CallbackQueryHandler(duty_schedule_callback, pattern="^duty_schedule$"))
    application.add_handler(CallbackQueryHandler(my_duties_callback, pattern="^my_duties$"))
    application.add_handler(CallbackQueryHandler(monthly_schedule_callback, pattern="^monthly_schedule$"))
    application.add_handler(CallbackQueryHandler(current_week_schedule_callback, pattern="^current_week_schedule$"))
    application.add_handler(CallbackQueryHandler(mark_completed_callback, pattern="^mark_completed$"))
    application.add_handler(CallbackQueryHandler(complete_duty_callback, pattern="^complete_duty_"))
    application.add_handler(CallbackQueryHandler(generate_schedule_callback, pattern="^generate_schedule$"))
    
    # Message handlers for text input
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
    
    # Убрали обработчик меню
    
    # Пока не нужен - убираем сложную логику

def main():
    """Main function to run the bot"""
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Get bot token from environment
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Setup commands
    setup_commands(application)
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()

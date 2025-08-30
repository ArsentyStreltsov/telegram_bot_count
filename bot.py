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
from handlers.start import start_command, main_menu_callback
from handlers.expense import (
    add_expense_callback, handle_amount_input, currency_callback
)
from handlers.messages import handle_text_message, handle_shopping_category_callback
from handlers.shopping import (
    shopping_list_callback, add_shopping_item_callback,
    list_shopping_items_callback, remove_shopping_item_callback, 
    toggle_item_callback, remove_item_callback
)
from handlers.reports import (
    report_callback, balances_callback
)
from handlers.commands import set_rate_command

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

def setup_handlers(application: Application):
    """Setup all bot handlers"""
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("set_rate", set_rate_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(add_expense_callback, pattern="^add_expense$"))
    application.add_handler(CallbackQueryHandler(currency_callback, pattern="^currency_"))
    application.add_handler(CallbackQueryHandler(handle_shopping_category_callback, pattern="^category_"))

    # Shopping handlers
    application.add_handler(CallbackQueryHandler(shopping_list_callback, pattern="^shopping_list$"))
    application.add_handler(CallbackQueryHandler(add_shopping_item_callback, pattern="^add_shopping_item$"))
    application.add_handler(CallbackQueryHandler(list_shopping_items_callback, pattern="^list_shopping_items$"))
    application.add_handler(CallbackQueryHandler(remove_shopping_item_callback, pattern="^remove_shopping_item$"))
    application.add_handler(CallbackQueryHandler(toggle_item_callback, pattern="^toggle_"))
    application.add_handler(CallbackQueryHandler(remove_item_callback, pattern="^remove_"))
    
    # Report handlers
    application.add_handler(CallbackQueryHandler(report_callback, pattern="^report$"))
    application.add_handler(CallbackQueryHandler(balances_callback, pattern="^balances$"))
    
    # Message handlers for text input
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_text_message
    ))

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
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()

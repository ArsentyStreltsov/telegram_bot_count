"""
Telegram inline keyboard utilities
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from models import ExpenseCategory, Currency

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🛒 Список покупок", callback_data="shopping_list"),
            InlineKeyboardButton("💰 Расходы", callback_data="expenses_menu")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="report"),
            InlineKeyboardButton("💳 Балансы", callback_data="balances")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def quick_commands_keyboard() -> ReplyKeyboardMarkup:
    """Quick commands keyboard with single Menu button"""
    keyboard = [
        [KeyboardButton("Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, input_field_placeholder="Напишите сообщение...")

def commands_list_keyboard() -> InlineKeyboardMarkup:
    """Commands list keyboard that appears when Menu button is pressed"""
    keyboard = [
        [InlineKeyboardButton("/start - Начать работу с ботом", callback_data="no_action")]
    ]
    return InlineKeyboardMarkup(keyboard)

def category_keyboard() -> InlineKeyboardMarkup:
    """Expense category selection keyboard"""
    keyboard = []
    row = []
    
    for i, category in enumerate(ExpenseCategory):
        row.append(InlineKeyboardButton(
            category.value.title(), 
            callback_data=f"category_{category.value}"
        ))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)



def shopping_actions_keyboard() -> InlineKeyboardMarkup:
    """Shopping list actions keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить товар", callback_data="add_shopping_item"),
            InlineKeyboardButton("📋 Список товаров", callback_data="list_shopping_items")
        ],
        [
            InlineKeyboardButton("🗑 Удалить товар", callback_data="remove_shopping_item")
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)



def confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ Нет", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Simple back button keyboard"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def split_choice_keyboard() -> InlineKeyboardMarkup:
    """Split choice keyboard for OTHER category expenses"""
    keyboard = [
        [
            InlineKeyboardButton("👥 На 5х", callback_data="split_5"),
            InlineKeyboardButton("👤 На 4х", callback_data="split_4")
        ],
        [
            InlineKeyboardButton("👨‍👩‍👦 На 3х", callback_data="split_3"),
            InlineKeyboardButton("👨‍👩 На 2х", callback_data="split_2")
        ],
        [
            InlineKeyboardButton("👨‍👩‍👧‍👦 За другую семью", callback_data="split_families")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="add_expense")]
    ]
    return InlineKeyboardMarkup(keyboard)

def pagination_keyboard(
    current_page: int, 
    total_pages: int, 
    base_callback: str
) -> InlineKeyboardMarkup:
    """Pagination keyboard"""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️", callback_data=f"{base_callback}_page_{current_page - 1}"
        ))
    
    nav_buttons.append(InlineKeyboardButton(
        f"{current_page}/{total_pages}", callback_data="no_action"
    ))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            "➡️", callback_data=f"{base_callback}_page_{current_page + 1}"
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def expenses_menu_keyboard() -> InlineKeyboardMarkup:
    """Expenses menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить расход", callback_data="add_expense"),
            InlineKeyboardButton("🗑 Удалить расходы", callback_data="delete_expenses")
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def currency_selection_keyboard() -> InlineKeyboardMarkup:
    """Currency selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🇸🇪 SEK", callback_data="currency_SEK"),
            InlineKeyboardButton("🇪🇺 EUR", callback_data="currency_EUR")
        ],
        [
            InlineKeyboardButton("🇷🇺 RUB", callback_data="currency_RUB")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)



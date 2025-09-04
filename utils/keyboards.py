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
            InlineKeyboardButton("📝 Список дел", callback_data="todo_list")
        ],
        [
            InlineKeyboardButton("💰 Расходы", callback_data="expenses_menu"),
            InlineKeyboardButton("📊 Отчет", callback_data="report")
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
    """Split choice keyboard for OTHER category expenses - shows participants directly"""
    keyboard = [
        [
            InlineKeyboardButton("⭕ Сеня", callback_data="participant_senya"),
            InlineKeyboardButton("⭕ Даша", callback_data="participant_dasha")
        ],
        [
            InlineKeyboardButton("⭕ Катя", callback_data="participant_katya"),
            InlineKeyboardButton("⭕ Дима", callback_data="participant_dima")
        ],
        [
            InlineKeyboardButton("⭕ Миша", callback_data="participant_misha")
        ],
        [
            InlineKeyboardButton("❌ Без разделения", callback_data="split_families")
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="add_expense")
        ]
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

def participants_selection_keyboard(selected_participants: set = None) -> InlineKeyboardMarkup:
    """Keyboard for selecting participants for OTHER category expenses"""
    if selected_participants is None:
        selected_participants = set()
    
    # Map participant names to telegram_ids
    participant_map = {
        "senya": 804085588,
        "dasha": 916228993,
        "dima": 350653235,
        "katya": 252901018,
        "misha": 6379711500
    }
    
    keyboard = []
    
    # Create participant buttons with visual indicators
    for name, telegram_id in participant_map.items():
        if telegram_id in selected_participants:
            # Selected - show green checkmark
            button_text = f"✅ {name.title()}"
        else:
            # Not selected - show red circle
            button_text = f"⭕ {name.title()}"
        
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"participant_{name}")
        ])
    
    # Add action buttons
    keyboard.append([
        InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_participants")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_split_choice")
    ])
    
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



"""
Expense handlers
"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import category_keyboard, back_keyboard, currency_selection_keyboard, expenses_menu_keyboard, split_choice_keyboard
from utils.texts import get_category_name, get_currency_name, format_amount
from services.expense_service import ExpenseService
from models import ExpenseCategory, Currency, Profile, User
from typing import Set
from telegram.error import BadRequest
import re

def get_participant_selection_display(selected_participants: Set[int], db, amount: float, currency, category_name: str) -> str:
    """Get display text for participant selection"""
    text = f"💰 Сумма: {format_amount(amount, currency)}\n"
    text += f"📂 Категория: {category_name}\n\n"
    text += "👥 Выберите людей, которые участвовали в этом расходе. Долг будет рассчитан только с участников противоположной группы\n\n"
    
    if not selected_participants:
        text += "Никто не выбран"
    else:
        participant_names = []
        for telegram_id in selected_participants:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                name = user.first_name or user.username or f"User {user.telegram_id}"
                participant_names.append(f"✅ {name}")
        
        text += "Выбранные участники:\n"
        text += "\n".join(participant_names)
        text += f"\n\nВсего участников: {len(selected_participants)}"
    
    return text

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

# User state storage moved to context.bot_data

async def expenses_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expenses menu button"""
    query = update.callback_query
    await query.answer()
    
    text = "💰 Меню расходов\n\nВыберите действие:"
    keyboard = expenses_menu_keyboard()
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def add_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add expense button"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        # Set user state to ask for currency first
        user_id = update.effective_user.id
        if 'user_states' not in context.bot_data:
            context.bot_data['user_states'] = {}
        
        context.bot_data['user_states'][user_id] = {
            'action': 'add_expense',
            'step': 'currency'
        }
        
        # Ask for currency first
        text = "💱 Выберите валюту:"
        keyboard = currency_selection_keyboard()
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        error_text, keyboard = handle_db_error(e, "добавлении расхода")
        await query.edit_message_text(error_text, reply_markup=keyboard)
    finally:
        db.close()

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse category from callback data
    callback_data = query.data
    if not callback_data.startswith("category_"):
        return
    
    category_value = callback_data.replace("category_", "")
    try:
        category = ExpenseCategory(category_value)
    except ValueError:
        await query.edit_message_text("❌ Неверная категория")
        return
    
    # Update user state with category
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    user_states[user_id]['category'] = category
    
    # Special handling for "OTHER" category - ask for custom name
    if category == ExpenseCategory.OTHER:
        user_states[user_id]['step'] = 'custom_category'
        
        text = f"💰 Сумма: {format_amount(user_states[user_id]['amount'], user_states[user_id]['currency'])}\n"
        text += f"📂 Категория: {get_category_name(category)}\n\n"
        text += "✏️ Введите описание покупки:\n"
        text += "Например: билеты, такси, ресторан, кино"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("add_expense")
        
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        # Create expense directly without profile selection
        # Get database session
        db = next(get_db())
        
        try:
            # Get default profile (Home) or create one if doesn't exist
            profile = db.query(Profile).filter(Profile.name == "Home").first()
            if not profile:
                # Create default profile if it doesn't exist
                profile = Profile(name="Home", is_default=True)
                db.add(profile)
                db.commit()
                db.refresh(profile)
            
            # Get user
            user = BaseHandler.get_or_create_user(db, update.effective_user)
            
            # Store values before clearing state
            amount = user_states[user_id]['amount']
            currency = user_states[user_id]['currency']
            custom_category_name = user_states[user_id].get('custom_category_name')
            
            # Create expense with special splitting logic
            from services.special_split import calculate_special_split
            
            # Calculate allocations based on category
            allocations = calculate_special_split(db, amount, category, profile.id)
            
            # Create expense
            expense = ExpenseService.create_expense(
                db=db,
                amount=amount,
                currency=currency,
                category=category,
                payer_id=user.id,
                profile_id=profile.id,
                allocations=allocations,
                custom_category_name=custom_category_name
            )
            
            # Clear user state
            del context.bot_data['user_states'][user_id]
            
            # Show success message
            text = f"✅ Расход добавлен!\n\n"
            if custom_category_name:
                text += f"📂 Категория: {get_category_name(category)}: {custom_category_name}\n"
            else:
                text += f"📂 Категория: {get_category_name(category)}\n"
            text += f"💱 Валюта: {get_currency_name(currency)}\n"
            text += f"💰 Сумма: {format_amount(amount, currency)}\n"
            text += f"💳 Оплатил: {BaseHandler.get_user_name(user)}"
            
            from utils.keyboards import back_keyboard
            keyboard = back_keyboard("main_menu")
            
            await query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            error_text, keyboard = handle_db_error(e, "создании расхода")
            await query.edit_message_text(error_text, reply_markup=keyboard)
        finally:
            db.close()



async def handle_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input"""
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        return
    
    amount_str = update.message.text
    amount = BaseHandler.validate_amount(amount_str)
    
    if amount is None:
        await update.message.reply_text(
            "❌ Неверный формат суммы. Введите положительное число (например: 100.50)"
        )
        return
    
    # Update user state with amount
    user_states[user_id]['amount'] = amount
    user_states[user_id]['step'] = 'category'
    
    # Show category selection
    currency = user_states[user_id]['currency']
    text = f"💱 Валюта: {get_currency_name(currency)}\n"
    text += f"💰 Сумма: {format_amount(amount, currency)}\n\n"
    text += "📂 Выберите категорию расхода:"
    
    from utils.keyboards import category_keyboard
    keyboard = category_keyboard()
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle currency selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse currency from callback data
    callback_data = query.data
    if not callback_data.startswith("currency_"):
        return
    
    currency_value = callback_data.replace("currency_", "")
    try:
        currency = Currency(currency_value)
    except ValueError:
        await query.edit_message_text("❌ Неверная валюта")
        return
    
    # Update user state with currency
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    user_states[user_id]['currency'] = currency
    user_states[user_id]['step'] = 'amount'
    
    # Ask for amount
    text = f"💱 Валюта: {get_currency_name(currency)}\n\n"
    text += "💰 Введите сумму:"
    
    keyboard = back_keyboard("add_expense")
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def split_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle split choice for OTHER category expenses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    # Initialize selected participants if not exists
    if 'selected_participants' not in user_states[user_id]:
        user_states[user_id]['selected_participants'] = []
    
    # Parse callback data
    callback_data = query.data
    
    if callback_data == "confirm_participants":
        # Confirm selection and create expense
        selected_participants = set(user_states[user_id].get('selected_participants', []))
        
        if len(selected_participants) < 2:
            await query.edit_message_text(
                "❌ Выберите минимум 2 участника для разделения расхода",
                reply_markup=back_keyboard("add_expense")
            )
            return
        
        # Проверяем, что выбраны участники из РАЗНЫХ групп
        from services.flexible_split import FlexibleSplitService
        
        # Проверяем, что есть участники из группы 1
        group_1_selected = any(telegram_id in FlexibleSplitService.GROUP_1_IDS for telegram_id in selected_participants)
        # Проверяем, что есть участники из группы 2  
        group_2_selected = any(telegram_id in FlexibleSplitService.GROUP_2_IDS for telegram_id in selected_participants)
        
        # Проверяем, что НЕ выбраны участники только из одной группы
        only_group_1 = group_1_selected and not group_2_selected
        only_group_2 = group_2_selected and not group_1_selected
        
        if only_group_1 or only_group_2:
            if only_group_1:
                group_name = "Даша + Сеня"
            else:
                group_name = "Дима + Катя + Миша"
            
            await query.edit_message_text(
                f"❌ Нельзя выбрать только участников из группы '{group_name}'. Выберите участников из РАЗНЫХ групп!",
                reply_markup=back_keyboard("add_expense")
            )
            return
        
        await create_expense_with_split(update, context, "participants", selected_participants)
        return
    
    elif callback_data == "no_split":
        # Create expense without splitting (like old "split_families")
        await create_expense_with_split(update, context, "split_families")
        return
    
    elif callback_data.startswith("participant_"):
        # Toggle participant selection
        participant_name = callback_data.replace("participant_", "")
        
        # Map participant names to user IDs
        participant_map = {
            "senya": 804085588,  # Арсентий
            "dasha": 916228993,  # Даша
            "dima": 350653235,   # Дима
            "katya": 252901018,  # Катя
            "misha": 6379711500  # Миша
        }
        
        if participant_name in participant_map:
            telegram_id = participant_map[participant_name]
            db = next(get_db())
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    # Convert list to set for manipulation
                    selected_participants = set(user_states[user_id].get('selected_participants', []))
                    
                    if telegram_id in selected_participants:
                        selected_participants.remove(telegram_id)
                        print(f"DEBUG: Removed {user.first_name} from selection")
                    else:
                        selected_participants.add(telegram_id)
                        print(f"DEBUG: Added {user.first_name} to selection")
                    
                    # Store back as list
                    user_states[user_id]['selected_participants'] = list(selected_participants)
                    print(f"DEBUG: Current selection: {selected_participants}")
                    
                    # Update display with current selection
                    amount = user_states[user_id]['amount']
                    currency = user_states[user_id]['currency']
                    category = user_states[user_id]['category']
                    base_name = get_category_name(category)
                    custom = user_states[user_id].get('custom_category_name')
                    category_name = f"{base_name}: {custom}" if custom else base_name
                    
                    text = get_participant_selection_display(selected_participants, db, amount, currency, category_name)
                    keyboard = split_choice_keyboard(selected_participants)
                    
                    try:
                        await query.edit_message_text(text, reply_markup=keyboard)
                    except BadRequest as e:
                        if "Message is not modified" in str(e):
                            await query.answer("Без изменений", show_alert=False)
                        else:
                            raise
                else:
                    print(f"DEBUG: User not found for telegram_id {telegram_id}")
            finally:
                db.close()
        else:
            print(f"DEBUG: Unknown participant name: {participant_name}")
        return
    
    else:
        await query.edit_message_text("❌ Неизвестный тип разделения")


async def create_expense_with_split(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  split_type: str, selected_participants: Set[int] = None):
    """Helper function to create expense with split logic"""
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    db = next(get_db())
    
    try:
        # Get default profile (Home)
        profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not profile:
            # Create default profile if it doesn't exist
            profile = Profile(name="Home", is_default=True)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        # Get user
        user = BaseHandler.get_or_create_user(db, update.effective_user)
        
        # Get values from state
        amount = user_states[user_id]['amount']
        currency = user_states[user_id]['currency']
        category = user_states[user_id]['category']
        custom_category_name = user_states[user_id]['custom_category_name']
        
        # Create expense with flexible splitting logic
        from services.flexible_split import FlexibleSplitService
        
        if split_type == "split_families":
            # Calculate family split allocations
            allocations = FlexibleSplitService.calculate_family_split(
                db, amount, user.telegram_id
            )
        elif split_type == "participants" and selected_participants:
            # Calculate participant split allocations
            allocations = FlexibleSplitService.calculate_participant_split(
                db, amount, selected_participants, user.telegram_id
            )
        else:
            allocations = {}
        
        # Create expense
        expense = ExpenseService.create_expense(
            db=db,
            amount=amount,
            currency=currency,
            category=category,
            payer_id=user.id,
            profile_id=profile.id,
            custom_category_name=custom_category_name,
            split_type=split_type,
            selected_participants=selected_participants
        )
        
        # Clear user state
        del context.bot_data['user_states'][user_id]
        
        # Show success message
        amount_text = format_amount(amount, currency)
        category_text = custom_category_name if custom_category_name else get_category_name(category)
        
        if split_type == "split_families":
            split_description = "За другую семью"
        elif split_type == "participants" and selected_participants:
            participant_names = []
            for participant_telegram_id in selected_participants:
                participant_user = db.query(User).filter(User.telegram_id == participant_telegram_id).first()
                if participant_user:
                    name = participant_user.first_name or participant_user.username or f"User {participant_user.telegram_id}"
                    participant_names.append(name)
            split_description = f"Участники: {', '.join(participant_names)}"
        else:
            split_description = "Стандартное разделение"
        
        text = f"✅ Расход создан!\n\n"
        text += f"💰 Сумма: {amount_text}\n"
        text += f"📁 Категория: {category_text}\n"
        text += f"👥 {split_description}"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("main_menu")
        
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Ошибка при создании расхода: {str(e)}")
    finally:
        db.close()



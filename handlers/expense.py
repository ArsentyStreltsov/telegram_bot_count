"""
Expense handlers
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from utils.keyboards import category_keyboard, back_keyboard, currency_selection_keyboard, expenses_menu_keyboard, participants_selection_keyboard
from utils.texts import get_category_name, get_currency_name, format_amount
from services.expense_service import ExpenseService
from models import ExpenseCategory, Currency, Profile, User
from typing import Set
import re

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
    
    print(f"🔍 DEBUG: split_choice_callback called with callback_data: {query.data}")
    
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    print(f"🔍 DEBUG: user_id: {user_id}")
    print(f"🔍 DEBUG: user_states: {user_states}")
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        print(f"❌ DEBUG: User state error - user_id: {user_id}, action: {user_states.get(user_id, {}).get('action', 'NOT_FOUND')}")
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    # Parse split type from callback data
    callback_data = query.data
    
    if callback_data.startswith("participant_"):
        print(f"🔍 DEBUG: Handling participant selection: {callback_data}")
        
        # Handle participant selection directly
        user_states[user_id]['step'] = 'select_participants'
        if 'selected_participants' not in user_states[user_id]:
            user_states[user_id]['selected_participants'] = set()
        
        # Toggle participant selection
        participant_name = callback_data.replace("participant_", "")
        print(f"🔍 DEBUG: Participant name: {participant_name}")
        
        # Map participant names to telegram_ids
        participant_map = {
            "senya": 804085588,
            "dasha": 916228993,
            "dima": 350653235,
            "katya": 252901018,
            "misha": 6379711500
        }
        
        if participant_name in participant_map:
            telegram_id = participant_map[participant_name]
            selected_participants = user_states[user_id]['selected_participants']
            
            print(f"🔍 DEBUG: Before toggle - selected_participants: {selected_participants}")
            
            if telegram_id in selected_participants:
                selected_participants.remove(telegram_id)
                print(f"🔍 DEBUG: Убрал {participant_name} (telegram_id: {telegram_id}) из выбора")
            else:
                selected_participants.add(telegram_id)
                print(f"🔍 DEBUG: Добавил {participant_name} (telegram_id: {telegram_id}) в выбор")
            
            print(f"🔍 DEBUG: After toggle - selected_participants: {selected_participants}")
            
            # Update keyboard to show current selection
            from utils.keyboards import split_choice_keyboard
            keyboard = split_choice_keyboard()
            
            # Update button texts based on selection
            for row in keyboard.inline_keyboard:
                for button in row:
                    if button.callback_data.startswith("participant_"):
                        name = button.callback_data.replace("participant_", "")
                        if name in participant_map:
                            telegram_id = participant_map[name]
                            if telegram_id in selected_participants:
                                button.text = f"✅ {name.title()}"
                            else:
                                button.text = f"⭕ {name.title()}"
            
            # Add confirm button if participants are selected
            if selected_participants:
                keyboard.inline_keyboard.insert(-2, [InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_participants")])
            
            print(f"🔍 DEBUG: Updating message with new keyboard")
            
            # Create text for the message
            text = "👥 Выберите между кем разделить расход:\n\n"
            text += "P.S. если ты заплатил за другого и расход делить не надо - выбирай 'Без разделения'"
            
            await query.edit_message_text(text, reply_markup=keyboard)
        else:
            print(f"❌ DEBUG: Unknown participant name: {participant_name}")
        return
    
    elif callback_data == "split_families":
        # Create expense with family split
        await create_expense_with_split(update, context, "split_families")
        return
    
    else:
        await query.edit_message_text("❌ Неизвестный тип разделения")

async def participant_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle participant selection for OTHER category expenses"""
    query = update.callback_query
    await query.answer()
    
    print(f"🔍 DEBUG: participant_selection_callback called with callback_data: {query.data}")
    
    user_id = update.effective_user.id
    user_states = context.bot_data.get('user_states', {})
    
    print(f"🔍 DEBUG: user_id: {user_id}")
    print(f"🔍 DEBUG: user_states: {user_states}")
    
    if user_id not in user_states or user_states[user_id]['action'] != 'add_expense':
        print(f"❌ DEBUG: User state error in participant_selection_callback")
        await query.edit_message_text("❌ Ошибка состояния")
        return
    
    callback_data = query.data
    
    if callback_data == "confirm_participants":
        # Confirm participant selection and create expense
        selected_participants = user_states[user_id].get('selected_participants', set())
        
        if len(selected_participants) < 2:
            await query.edit_message_text(
                "❌ Выберите минимум 2 участника для разделения расхода",
                reply_markup=back_keyboard("back_to_split_choice")
            )
            return
        
        await create_expense_with_split(update, context, "participants", selected_participants)
        return
    
    elif callback_data == "back_to_split_choice":
        # Go back to split choice
        user_states[user_id]['step'] = 'split_choice'
        user_states[user_id].pop('selected_participants', None)
        
        from utils.keyboards import split_choice_keyboard
        text = "👥 Выберите между кем разделить расход:\n\n"
        text += "P.S. если ты заплатил за другого и расход делить не надо - выбирай 'Без разделения'"
        
        keyboard = split_choice_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard)
        return
    
    elif callback_data.startswith("participant_"):
        # Toggle participant selection
        participant_name = callback_data.replace("participant_", "")
        
        # Map participant names to telegram_ids
        participant_map = {
            "senya": 804085588,
            "dasha": 916228993,
            "dima": 350653235,
            "katya": 252901018,
            "misha": 6379711500
        }
        
        if participant_name in participant_map:
            telegram_id = participant_map[participant_name]
            
            # Toggle selection in telegram_ids (not user IDs)
            selected_participants = user_states[user_id].get('selected_participants', set())
            
            if telegram_id in selected_participants:
                selected_participants.remove(telegram_id)
                print(f"🔍 DEBUG: Убрал {participant_name} (telegram_id: {telegram_id}) из выбора")
            else:
                selected_participants.add(telegram_id)
                print(f"🔍 DEBUG: Добавил {participant_name} (telegram_id: {telegram_id}) в выбор")
            
            user_states[user_id]['selected_participants'] = selected_participants
            
            # Update display with new keyboard
            from services.flexible_split import FlexibleSplitService
            text = FlexibleSplitService.get_participant_selection_text(
                selected_participants, db=None  # We don't need db for this
            )
            keyboard = participants_selection_keyboard(selected_participants)
            
            await query.edit_message_text(text, reply_markup=keyboard)
        return

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
            print(f"🔍 DEBUG: Creating expense with split_type='split_families'")
            print(f"🔍 DEBUG: amount={amount}, user.telegram_id={user.telegram_id}")
            
            allocations = FlexibleSplitService.calculate_family_split(
                db, amount, user.telegram_id
            )
            
            print(f"🔍 DEBUG: Allocations calculated: {allocations}")
        elif split_type == "participants" and selected_participants:
            # Calculate participant split allocations
            print(f"🔍 DEBUG: Creating expense with split_type='participants'")
            print(f"🔍 DEBUG: selected_participants (telegram_ids): {selected_participants}")
            print(f"🔍 DEBUG: user.telegram_id: {user.telegram_id}")
            
            # Convert telegram_ids to user_ids for the service
            user_ids = set()
            for telegram_id in selected_participants:
                participant_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if participant_user:
                    user_ids.add(participant_user.id)
                    print(f"🔍 DEBUG: telegram_id {telegram_id} -> user_id {participant_user.id}")
            
            allocations = FlexibleSplitService.calculate_participant_split(
                db, amount, user_ids, user.telegram_id
            )
            
            print(f"🔍 DEBUG: Participant allocations calculated: {allocations}")
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
            for participant_id in selected_participants:
                participant_user = db.query(User).filter(User.id == participant_id).first()
                if participant_user:
                    name = participant_user.first_name or participant_user.username or f"User {participant_user.telegram_id}"
                    participant_names.append(name)
            split_description = f"Участники: {', '.join(participant_names)}"
        else:
            split_description = "Стандартное разделение"
        
        text = f"✅ Расход создан!\n\n"
        text += f"💰 Сумма: {amount_text}\n"
        text += f"📁 Категория: {category_text}\n"
        text += f"👥 Разделение: {split_description}"
        
        from utils.keyboards import back_keyboard
        keyboard = back_keyboard("main_menu")
        
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Ошибка при создании расхода: {str(e)}")
    finally:
        db.close()



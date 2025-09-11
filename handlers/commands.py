"""
Command handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from models import ExchangeRate, Currency, ExpenseCategory, User, Profile
from services.expense_service import ExpenseService
from services.flexible_split import FlexibleSplitService
from utils.texts import get_category_name, get_currency_name, format_amount
from datetime import datetime
import re

async def set_rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_rate command"""
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n\n"
            "Используйте: /set_rate EUR 11.30"
        )
        return
    
    currency_str = context.args[0].upper()
    rate_str = context.args[1]
    
    # Validate currency
    try:
        currency = Currency(currency_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ Неподдерживаемая валюта: {currency_str}\n\n"
            f"Поддерживаемые валюты: {', '.join([c.value for c in Currency])}"
        )
        return
    
    # Validate rate
    rate = BaseHandler.validate_exchange_rate(rate_str)
    if rate is None:
        await update.message.reply_text(
            "❌ Неверный формат курса.\n\n"
            "Используйте положительное число, например: 11.30"
        )
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Invalidate previous rates
        db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == currency,
            ExchangeRate.to_currency == Currency.SEK,
            ExchangeRate.valid_until.is_(None)
        ).update({"valid_until": datetime.utcnow()})
        
        # Create new rate
        new_rate = ExchangeRate(
            from_currency=currency,
            to_currency=Currency.SEK,
            rate=rate,
            valid_from=datetime.utcnow()
        )
        
        db.add(new_rate)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Курс обновлен!\n\n"
            f"1 {currency.value} = {rate:.2f} SEK\n\n"
            f"Курс действителен с {new_rate.valid_from.strftime('%d.%m.%Y %H:%M')}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обновлении курса: {str(e)}")
    finally:
        db.close()

async def addexpence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addexpence command with parameters: currency,amount,category,custom_name,payer_name"""
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n\n"
            "Используйте: /addexpence валюта сумма категория имя_плательщика [описание]\n\n"
            "Примеры:\n"
            "• /addexpence EUR 110 продукты дима\n"
            "• /addexpence EUR 110 другое еда на заправке дима\n"
            "• /addexpence SEK 500 алкоголь катя\n\n"
            "Валюты: SEK, EUR, RUB\n"
            "Категории: продукты, алкоголь, другое\n"
            "Имена: дима, катя, сеня, даша, миша"
        )
        return
    
    # Parse arguments
    currency_str = context.args[0].upper()
    amount_str = context.args[1]
    category_str = context.args[2].lower()
    payer_name = context.args[3].lower()
    custom_name = context.args[4] if len(context.args) > 4 else None
    
    # Validate currency
    try:
        currency = Currency(currency_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ Неподдерживаемая валюта: {currency_str}\n\n"
            f"Поддерживаемые валюты: {', '.join([c.value for c in Currency])}"
        )
        return
    
    # Validate amount
    amount = BaseHandler.validate_amount(amount_str)
    if amount is None:
        await update.message.reply_text(
            "❌ Неверный формат суммы. Введите положительное число (например: 110.50)"
        )
        return
    
    # Validate category
    category_map = {
        "продукты": ExpenseCategory.FOOD,
        "алкоголь": ExpenseCategory.ALCOHOL,
        "другое": ExpenseCategory.OTHER
    }
    
    if category_str not in category_map:
        await update.message.reply_text(
            f"❌ Неверная категория: {category_str}\n\n"
            f"Поддерживаемые категории: {', '.join(category_map.keys())}"
        )
        return
    
    category = category_map[category_str]
    
    # Validate custom name for "другое" category
    if category == ExpenseCategory.OTHER and not custom_name:
        await update.message.reply_text(
            "❌ Для категории 'другое' необходимо указать описание.\n\n"
            "Пример: /addexpence EUR 110 другое еда на заправке дима"
        )
        return
    
    # Map payer names to telegram IDs
    payer_map = {
        "дима": 350653235,
        "катя": 252901018,
        "сеня": 804085588,
        "даша": 916228993,
        "миша": 6379711500
    }
    
    if payer_name not in payer_map:
        await update.message.reply_text(
            f"❌ Неверное имя плательщика: {payer_name}\n\n"
            f"Доступные имена: {', '.join(payer_map.keys())}"
        )
        return
    
    payer_telegram_id = payer_map[payer_name]
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create payer user
        payer_user = db.query(User).filter(User.telegram_id == payer_telegram_id).first()
        if not payer_user:
            await update.message.reply_text(
                f"❌ Пользователь {payer_name} не найден в системе.\n"
                "Попросите его присоединиться к боту с помощью /start"
            )
            return
        
        # Get default profile (Home)
        profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not profile:
            # Create default profile if it doesn't exist
            profile = Profile(name="Home", is_default=True)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
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
            payer_id=payer_user.id,
            profile_id=profile.id,
            allocations=allocations,
            custom_category_name=custom_name
        )
        
        # Show success message
        text = f"✅ Расход добавлен!\n\n"
        if custom_name:
            text += f"📂 Категория: {get_category_name(category)}: {custom_name}\n"
        else:
            text += f"📂 Категория: {get_category_name(category)}\n"
        text += f"💱 Валюта: {get_currency_name(currency)}\n"
        text += f"💰 Сумма: {format_amount(amount, currency)}\n"
        text += f"💳 Оплатил: {BaseHandler.get_user_name(payer_user)}"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при создании расхода: {str(e)}")
    finally:
        db.close()

async def addexpence_advanced_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addexpence_advanced command with participant selection"""
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n\n"
            "Используйте: /addexpence_advanced валюта сумма категория имя_плательщика участники [описание]\n\n"
            "Примеры:\n"
            "• /addexpence_advanced EUR 110 продукты дима дима,катя\n"
            "• /addexpence_advanced EUR 110 другое еда на заправке дима дима,сеня,даша\n"
            "• /addexpence_advanced SEK 500 алкоголь катя катя,миша\n\n"
            "Валюты: SEK, EUR, RUB\n"
            "Категории: продукты, алкоголь, другое\n"
            "Имена: дима, катя, сеня, даша, миша\n"
            "Участники: список имен через запятую (минимум 2 человека)"
        )
        return
    
    # Parse arguments
    currency_str = context.args[0].upper()
    amount_str = context.args[1]
    category_str = context.args[2].lower()
    payer_name = context.args[3].lower()
    participants_str = context.args[4].lower()
    custom_name = context.args[5] if len(context.args) > 5 else None
    
    # Validate currency
    try:
        currency = Currency(currency_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ Неподдерживаемая валюта: {currency_str}\n\n"
            f"Поддерживаемые валюты: {', '.join([c.value for c in Currency])}"
        )
        return
    
    # Validate amount
    amount = BaseHandler.validate_amount(amount_str)
    if amount is None:
        await update.message.reply_text(
            "❌ Неверный формат суммы. Введите положительное число (например: 110.50)"
        )
        return
    
    # Validate category
    category_map = {
        "продукты": ExpenseCategory.FOOD,
        "алкоголь": ExpenseCategory.ALCOHOL,
        "другое": ExpenseCategory.OTHER
    }
    
    if category_str not in category_map:
        await update.message.reply_text(
            f"❌ Неверная категория: {category_str}\n\n"
            f"Поддерживаемые категории: {', '.join(category_map.keys())}"
        )
        return
    
    category = category_map[category_str]
    
    # Validate custom name for "другое" category
    if category == ExpenseCategory.OTHER and not custom_name:
        await update.message.reply_text(
            "❌ Для категории 'другое' необходимо указать описание.\n\n"
            "Пример: /addexpence_advanced EUR 110 другое еда на заправке дима дима,катя"
        )
        return
    
    # Map names to telegram IDs
    name_map = {
        "дима": 350653235,
        "катя": 252901018,
        "сеня": 804085588,
        "даша": 916228993,
        "миша": 6379711500
    }
    
    # Validate payer
    if payer_name not in name_map:
        await update.message.reply_text(
            f"❌ Неверное имя плательщика: {payer_name}\n\n"
            f"Доступные имена: {', '.join(name_map.keys())}"
        )
        return
    
    payer_telegram_id = name_map[payer_name]
    
    # Parse and validate participants
    participant_names = [name.strip() for name in participants_str.split(',')]
    if len(participant_names) < 2:
        await update.message.reply_text(
            "❌ Необходимо указать минимум 2 участника для разделения расхода"
        )
        return
    
    # Validate all participant names
    invalid_names = [name for name in participant_names if name not in name_map]
    if invalid_names:
        await update.message.reply_text(
            f"❌ Неверные имена участников: {', '.join(invalid_names)}\n\n"
            f"Доступные имена: {', '.join(name_map.keys())}"
        )
        return
    
    # Convert to telegram IDs
    participant_telegram_ids = set(name_map[name] for name in participant_names)
    
    # Check that participants are from different groups (same logic as in expense.py)
    group_1_selected = any(telegram_id in FlexibleSplitService.GROUP_1_IDS for telegram_id in participant_telegram_ids)
    group_2_selected = any(telegram_id in FlexibleSplitService.GROUP_2_IDS for telegram_id in participant_telegram_ids)
    
    only_group_1 = group_1_selected and not group_2_selected
    only_group_2 = group_2_selected and not group_1_selected
    
    if only_group_1 or only_group_2:
        if only_group_1:
            group_name = "Даша + Сеня"
        else:
            group_name = "Дима + Катя + Миша"
        
        await update.message.reply_text(
            f"❌ Нельзя выбрать только участников из группы '{group_name}'. Выберите участников из РАЗНЫХ групп!"
        )
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create payer user
        payer_user = db.query(User).filter(User.telegram_id == payer_telegram_id).first()
        if not payer_user:
            await update.message.reply_text(
                f"❌ Пользователь {payer_name} не найден в системе.\n"
                "Попросите его присоединиться к боту с помощью /start"
            )
            return
        
        # Get default profile (Home)
        profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not profile:
            # Create default profile if it doesn't exist
            profile = Profile(name="Home", is_default=True)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        # Create expense with participant split logic
        allocations = FlexibleSplitService.calculate_participant_split(
            db, amount, participant_telegram_ids, payer_telegram_id
        )
        
        # Create expense
        expense = ExpenseService.create_expense(
            db=db,
            amount=amount,
            currency=currency,
            category=category,
            payer_id=payer_user.id,
            profile_id=profile.id,
            allocations=allocations,
            custom_category_name=custom_name,
            split_type="participants",
            selected_participants=participant_telegram_ids
        )
        
        # Show success message
        text = f"✅ Расход добавлен!\n\n"
        if custom_name:
            text += f"📂 Категория: {get_category_name(category)}: {custom_name}\n"
        else:
            text += f"📂 Категория: {get_category_name(category)}\n"
        text += f"💱 Валюта: {get_currency_name(currency)}\n"
        text += f"💰 Сумма: {format_amount(amount, currency)}\n"
        text += f"💳 Оплатил: {BaseHandler.get_user_name(payer_user)}\n"
        text += f"👥 Участники: {', '.join(participant_names)}"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при создании расхода: {str(e)}")
    finally:
        db.close()

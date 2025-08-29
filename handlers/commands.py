"""
Command handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from db import get_db
from handlers.base import BaseHandler
from models import ExchangeRate, Currency
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

"""
Text utilities for bot messages in Russian
"""
from models import ExpenseCategory, Currency
from typing import Dict, List
from datetime import datetime

def get_category_name(category: ExpenseCategory) -> str:
    """Get Russian name for expense category"""
    names = {
        ExpenseCategory.FOOD: "Продукты",
        ExpenseCategory.ALCOHOL: "Алкоголь",
        ExpenseCategory.OTHER: "Другое"
    }
    return names.get(category, category.value)

def get_currency_name(currency: Currency) -> str:
    """Get Russian name for currency"""
    names = {
        Currency.SEK: "SEK (шведские кроны)",
        Currency.EUR: "EUR (евро)",
        Currency.RUB: "RUB (рубли)"
    }
    return names.get(currency, currency.value)

def format_amount(amount: float, currency: Currency) -> str:
    """Format amount with currency symbol"""
    symbols = {
        Currency.SEK: "kr",
        Currency.EUR: "€",
        Currency.RUB: "₽"
    }
    symbol = symbols.get(currency, currency.value)
    return f"{amount:.2f} {symbol}"

def format_expense_report(expenses_by_category: Dict, current_month: datetime) -> str:
    """Format monthly expense report"""
    # Russian month names
    month_names = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    
    month_num = current_month.month
    month_name = month_names.get(month_num, current_month.strftime("%B"))
    year = current_month.year
    
    text = f"📊 Отчет по тратам за {month_name} {year}\n\n"
    
    total_sek = 0
    for category_value, data in expenses_by_category.items():
        category = ExpenseCategory(category_value)
        category_name = get_category_name(category)
        amount = data['total_sek']
        count = data['count']
        total_sek += amount
        
        # Handle custom category names for "OTHER"
        if category == ExpenseCategory.OTHER and data.get('individual_expenses'):
            individual_expenses = data['individual_expenses']
            # Show each individual expense with its own amount
            for expense in individual_expenses:
                text += f"• {expense['name']}: {format_amount(expense['amount_sek'], Currency.SEK)}\n"
            continue  # Skip the default line below
        
        text += f"• {category_name}: {format_amount(amount, Currency.SEK)}\n"
    
    text += f"\n💰 Общий итог: {format_amount(total_sek, Currency.SEK)}\n\n"
    return text

def format_balance_report(balances: Dict, users: Dict, settlements: List) -> str:
    """Format balance report"""
    text = "💳 Балансы участников:\n\n"
    
    for user_id, balance in balances.items():
        user = users.get(user_id)
        if user:
            name = user.first_name or user.username or f"User {user_id}"
            text += f"👤 {name}:\n"
            text += f"   💰 Оплатил: {format_amount(balance['paid'], Currency.SEK)}\n"
            text += f"   📋 Должен: {format_amount(balance['owed'], Currency.SEK)}\n"
            
            net = balance['net']
            if net > 0:
                text += f"   ✅ Кредит: +{format_amount(net, Currency.SEK)}\n"
            elif net < 0:
                text += f"   ❌ Долг: {format_amount(abs(net), Currency.SEK)}\n"
            else:
                text += f"   ⚖️ Баланс: 0\n"
            text += "\n"
    
    if settlements:
        text += "🔄 План погашения:\n\n"
        for settlement in settlements:
            from_user = users.get(settlement['from_user_id'])
            to_user = users.get(settlement['to_user_id'])
            
            if from_user and to_user:
                from_name = from_user.first_name or from_user.username or f"User {settlement['from_user_id']}"
                to_name = to_user.first_name or to_user.username or f"User {settlement['to_user_id']}"
                
                text += f"• {from_name} → {to_name}: {format_amount(settlement['amount_sek'], Currency.SEK)}\n"
    
    return text

def format_shopping_list(items: List, page: int = 1, total_pages: int = 1) -> str:
    """Format shopping list"""
    if not items:
        return "🛒 Список покупок пуст"
    
    text = "🛒 Список покупок:\n\n"
    
    for i, item in enumerate(items, 1):
        status = "✅" if item.is_checked else "⭕"
        text += f"{i}. {status} {item.title}\n"
    
    return text

def get_welcome_message(user_name: str) -> str:
    """Get welcome message"""
    return f"""👋 Привет, {user_name}!

Добро пожаловать в бот для отслеживания семейных расходов!

Возможности:
• 📝 Общий список покупок
• 💰 Отслеживание расходов по категориям
• 📊 Месячные отчеты и балансы

Выберите действие в главном меню:"""

def get_help_message() -> str:
    """Get help message"""
    return """📖 Справка по командам:

/start - Главное меню
/set_rate EUR 11.30 - Установить курс валюты

🛒 Список покупок:
• Добавляйте товары в общий список
• Отмечайте купленные товары
• Создавайте расходы из покупок

💰 Расходы:
• Выбирайте категорию и валюту
• Указывайте сумму и заметку
• Выбирайте профиль разделения

📊 Отчеты:
• Просматривайте расходы по категориям
• Проверяйте балансы участников
• Закрывайте месяцы

💱 Курсы валют:
• Устанавливайте актуальные курсы
• Все расчеты ведутся в SEK

👥 Профили:
• Настраивайте группы участников
• Устанавливайте веса для разделения"""

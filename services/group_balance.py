#!/usr/bin/env python3
"""
Group balance calculation service
Calculates balances between groups of users
"""

from sqlalchemy.orm import Session
from models import User, Expense, ExpenseAllocation, Profile, ProfileMember
from typing import Dict, List, Tuple
from decimal import Decimal

class GroupBalanceService:
    """Service for calculating balances between user groups"""
    
    # Определяем группы пользователей
    GROUP_1_IDS = [804085588, 916228993]  # Сеня + Даша
    GROUP_2_IDS = [252901018, 350653235, 6379711500]  # Катя + Дима + Миша
    
    @classmethod
    def get_user_group(cls, user_id: int) -> int:
        """Get group number for user (1 or 2)"""
        if user_id in cls.GROUP_1_IDS:
            return 1
        elif user_id in cls.GROUP_2_IDS:
            return 2
        else:
            return 0  # Неизвестный пользователь
    
    @classmethod
    def calculate_group_balances(cls, db: Session, profile_id: int = None) -> Dict:
        """Calculate balances between groups"""
        
        # Получаем профиль (по умолчанию Home)
        if profile_id is None:
            profile = db.query(Profile).filter(Profile.is_default == True).first()
            if not profile:
                return {"error": "Профиль по умолчанию не найден"}
            profile_id = profile.id
        
        # Получаем все расходы для профиля
        expenses = db.query(Expense).filter(Expense.profile_id == profile_id).all()
        
        # Инициализируем счетчики
        group_totals = {1: 0.0, 2: 0.0}  # Сколько каждая группа потратила
        group_shares = {1: 0.0, 2: 0.0}   # Сколько каждая группа должна
        
        # Проходим по всем расходам
        for expense in expenses:
            # Получаем аллокации для расхода
            allocations = db.query(ExpenseAllocation).filter(
                ExpenseAllocation.expense_id == expense.id
            ).all()
            
            if not allocations:
                continue
            
            # Кто внес расход (получаем пользователя по внутреннему ID)
            payer = db.query(User).filter(User.id == expense.payer_id).first()
            if not payer:
                continue
                
            payer_group = cls.get_user_group(payer.telegram_id)
            
            if payer_group == 0:
                continue
            
            # Добавляем к потраченному группой
            group_totals[payer_group] += expense.amount_sek
            
            # Считаем доли по категории
            category_shares = cls._calculate_category_shares(db, expense, allocations)
            
            # Распределяем доли по группам
            for user_id, share in category_shares.items():
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user_group = cls.get_user_group(user.telegram_id)
                    if user_group > 0:
                        group_shares[user_group] += share
        
        # Вычисляем чистые балансы
        group_balances = {}
        for group in [1, 2]:
            net_balance = group_totals[group] - group_shares[group]
            group_balances[group] = {
                "spent": group_totals[group],
                "owes": group_shares[group],
                "net_balance": net_balance
            }
        
        # Определяем, кто кому должен
        group1_balance = group_balances[1]["net_balance"]
        group2_balance = group_balances[2]["net_balance"]
        
        if group1_balance > 0 and group2_balance < 0:
            # Группа 1 должна группе 2 (группа 1 переплатила)
            debt_amount = min(group1_balance, abs(group2_balance))
            debt_direction = "Дима + Катя + Миша должны Даша + Сеня"
        elif group2_balance > 0 and group1_balance < 0:
            # Группа 2 должна группе 1 (группа 2 переплатила)
            debt_amount = min(group2_balance, abs(group1_balance))
            debt_direction = "Даша + Сеня должны Дима + Катя + Миша"
        else:
            debt_amount = 0
            debt_direction = "Баланс сведен"
        
        return {
            "group_balances": group_balances,
            "debt_amount": debt_amount,
            "debt_direction": debt_direction,
            "summary": {
                "group_1": {
                    "name": "Даша + Сеня",
                    "spent": group_totals[1],
                    "owes": group_shares[1],
                    "net": group_balances[1]["net_balance"]
                },
                "group_2": {
                    "name": "Дима + Катя + Миша", 
                    "spent": group_totals[2],
                    "owes": group_shares[2],
                    "net": group_balances[2]["net_balance"]
                }
            }
        }
    
    @classmethod
    def _calculate_category_shares(cls, db: Session, expense, allocations: List[ExpenseAllocation]) -> Dict[int, float]:
        """Calculate how much each user owes for this expense based on actual allocations"""
        
        print(f"🔍 DEBUG: _calculate_category_shares called for expense_id={expense.id}")
        print(f"🔍 DEBUG: expense.amount_sek={expense.amount_sek}")
        print(f"🔍 DEBUG: expense.category={expense.category}")
        print(f"🔍 DEBUG: allocations count={len(allocations) if allocations else 0}")
        
        # Если есть аллокации (например, из FlexibleSplitService), используем их
        if allocations:
            print(f"🔍 DEBUG: Using explicit allocations")
            shares = {}
            for allocation in allocations:
                print(f"🔍 DEBUG: Allocation: user_id={allocation.user_id}, amount_sek={allocation.amount_sek}")
                shares[allocation.user_id] = allocation.amount_sek
            print(f"🔍 DEBUG: Final shares: {shares}")
            return shares
        
        # Иначе используем старую логику по категориям (для обратной совместимости)
        from services.special_split import get_users_for_category
        
        # Получаем пользователей для данной категории
        category_users = get_users_for_category(db, expense.category)
        
        if not category_users:
            return {}
        
        # Равное разделение между участниками категории
        user_count = len(category_users)
        share_per_user = expense.amount_sek / user_count
        
        # Создаем словарь долей
        shares = {}
        for user in category_users:
            shares[user.id] = share_per_user
        
        return shares
    
    @classmethod
    def get_detailed_balance_report(cls, db: Session, profile_id: int = None) -> str:
        """Get detailed balance report as formatted text"""
        result = cls.calculate_group_balances(db, profile_id)
        
        if "error" in result:
            return f"❌ Ошибка: {result['error']}"
        
        summary = result["summary"]
        
        report = "📊 Отчет по балансам групп\n\n"
        
        # Группа 1
        report += f"{summary['group_1']['name']}\n"
        report += f"💰 Потратили: {summary['group_1']['spent']:.2f} SEK\n"
        # Показываем "Должны" только если другие платили за нас
        if summary['group_1']['owes'] > summary['group_1']['spent']:
            report += f"💸 Должны: {summary['group_1']['owes'] - summary['group_1']['spent']:.2f} SEK\n"
        else:
            report += f"💸 Должны: 0.00 SEK\n"
        report += "\n"
        
        # Группа 2
        report += f"{summary['group_2']['name']}\n"
        report += f"💰 Потратили: {summary['group_2']['spent']:.2f} SEK\n"
        # Показываем "Должны" только если другие платили за нас
        if summary['group_2']['owes'] > summary['group_2']['spent']:
            report += f"💸 Должны: {summary['group_2']['owes'] - summary['group_2']['spent']:.2f} SEK\n"
        else:
            report += f"💸 Должны: 0.00 SEK\n"
        report += "\n"
        
        # Итог
        if result["debt_amount"] > 0:
            report += f"💳 Итого:\n"
            report += f"{result['debt_direction']} - {result['debt_amount']:.2f} SEK"
        else:
            report += f"✅ {result['debt_direction']}"
        
        return report

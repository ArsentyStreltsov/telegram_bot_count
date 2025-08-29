"""
Expense splitting service
"""
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from models import Profile, ProfileMember, Expense, ExpenseAllocation, Currency
from datetime import datetime

class SplitService:
    """Service for calculating expense splits"""
    
    @staticmethod
    def calculate_expense_split(
        db: Session, 
        expense: Expense, 
        profile: Profile
    ) -> List[ExpenseAllocation]:
        """
        Calculate how expense should be split among profile members
        
        Args:
            db: Database session
            expense: Expense record
            profile: Split profile
            
        Returns:
            List of allocations for each user
        """
        # Get profile members with their groups and weights
        members = db.query(ProfileMember).filter(
            ProfileMember.profile_id == profile.id
        ).all()
        
        if not members:
            raise ValueError(f"Profile {profile.name} has no members")
        
        # Group members by group_name
        groups: Dict[str, List[ProfileMember]] = {}
        for member in members:
            if member.group_name not in groups:
                groups[member.group_name] = []
            groups[member.group_name].append(member)
        
        # Calculate total weight across all groups
        total_weight = sum(
            sum(member.weight for member in group_members)
            for group_members in groups.values()
        )
        
        allocations = []
        amount_sek = expense.amount_sek
        
        for group_name, group_members in groups.items():
            # Calculate group's share
            group_weight = sum(member.weight for member in group_members)
            group_share = amount_sek * group_weight / total_weight
            
            # Split group share equally among group members
            member_count = len(group_members)
            member_share = group_share / member_count
            
            for member in group_members:
                allocation = ExpenseAllocation(
                    expense_id=expense.id,
                    user_id=member.user_id,
                    amount_sek=member_share,
                    weight_used=member.weight
                )
                allocations.append(allocation)
        
        return allocations
    
    @staticmethod
    def calculate_user_balances(
        db: Session, 
        month: datetime = None
    ) -> Dict[int, Dict[str, float]]:
        """
        Calculate net balances for all users in a given month
        
        Args:
            db: Database session
            month: Month to calculate for (defaults to current month)
            
        Returns:
            Dict mapping user_id to balance info
        """
        if month is None:
            month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get all expenses for the month
        expenses = db.query(Expense).filter(
            Expense.month == month.date()
        ).all()
        
        balances = {}
        
        for expense in expenses:
            # Get allocations for this expense
            allocations = db.query(ExpenseAllocation).filter(
                ExpenseAllocation.expense_id == expense.id
            ).all()
            
            # Add to payer's paid amount
            if expense.payer_id not in balances:
                balances[expense.payer_id] = {
                    'paid': 0.0,
                    'owed': 0.0,
                    'net': 0.0
                }
            balances[expense.payer_id]['paid'] += expense.amount_sek
            
            # Add to each user's owed amount
            for allocation in allocations:
                if allocation.user_id not in balances:
                    balances[allocation.user_id] = {
                        'paid': 0.0,
                        'owed': 0.0,
                        'net': 0.0
                    }
                balances[allocation.user_id]['owed'] += allocation.amount_sek
        
        # Calculate net balances
        for user_id, balance in balances.items():
            balance['net'] = balance['owed'] - balance['paid']
        
        return balances
    
    @staticmethod
    def calculate_settlement_plan(
        db: Session, 
        balances: Dict[int, Dict[str, float]]
    ) -> List[Dict[str, any]]:
        """
        Calculate optimal settlement plan (who owes whom how much)
        
        Args:
            db: Database session
            balances: User balances from calculate_user_balances
            
        Returns:
            List of settlement transactions
        """
        # Separate debtors and creditors
        debtors = []
        creditors = []
        
        for user_id, balance in balances.items():
            if balance['net'] < 0:  # Owe money
                debtors.append((user_id, abs(balance['net'])))
            elif balance['net'] > 0:  # Are owed money
                creditors.append((user_id, balance['net']))
        
        # Sort by amount (largest first)
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)
        
        settlements = []
        
        # Greedy settlement algorithm
        debtor_idx = 0
        creditor_idx = 0
        
        while debtor_idx < len(debtors) and creditor_idx < len(creditors):
            debtor_id, debtor_amount = debtors[debtor_idx]
            creditor_id, creditor_amount = creditors[creditor_idx]
            
            # Calculate settlement amount
            settlement_amount = min(debtor_amount, creditor_amount)
            
            settlements.append({
                'from_user_id': debtor_id,
                'to_user_id': creditor_id,
                'amount_sek': settlement_amount
            })
            
            # Update remaining amounts
            debtor_amount -= settlement_amount
            creditor_amount -= settlement_amount
            
            if debtor_amount <= 0.01:  # Small threshold for floating point
                debtor_idx += 1
            else:
                debtors[debtor_idx] = (debtor_id, debtor_amount)
            
            if creditor_amount <= 0.01:
                creditor_idx += 1
            else:
                creditors[creditor_idx] = (creditor_id, creditor_amount)
        
        return settlements

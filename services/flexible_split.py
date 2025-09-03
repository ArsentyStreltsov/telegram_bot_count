#!/usr/bin/env python3
"""
Flexible expense splitting service for "OTHER" category
Allows users to choose how to split expenses
"""

from sqlalchemy.orm import Session
from models import User, Profile, ProfileMember
from typing import Dict, List
from decimal import Decimal

class FlexibleSplitService:
    """Service for flexible expense splitting"""

    # Определяем группы пользователей
    GROUP_1_IDS = [804085588, 916228993]  # Сеня + Даша
    GROUP_2_IDS = [252901018, 350653235, 6379711500]  # Катя + Дима + Миша

    @classmethod
    def get_users_for_split(cls, db: Session, split_type: str, profile_id: int) -> List[User]:
        """Get users for specific split type"""
        
        if split_type == "split_5":
            # На всех 5 поровну
            return db.query(User).filter(
                User.telegram_id.in_(cls.GROUP_1_IDS + cls.GROUP_2_IDS)
            ).all()
            
        elif split_type == "split_4":
            # На всех кроме Миши (4 человека)
            return db.query(User).filter(
                User.telegram_id.in_([804085588, 916228993, 252901018, 350653235])
            ).all()
            
        elif split_type == "split_families":
            # Только на противоположную группу
            # Определяем, кто платит
            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if not profile:
                return []
            
            # Получаем всех пользователей профиля
            profile_members = db.query(ProfileMember).filter(
                ProfileMember.profile_id == profile_id
            ).all()
            
            # Определяем, кто платит (по telegram_id из контекста)
            # Это будет определено в handler'е
            
            # Пока возвращаем пустой список, логика будет в handler'е
            return []
            
        else:
            return []

    @classmethod
    def calculate_flexible_split(cls, db: Session, amount: float, split_type: str, 
                               profile_id: int, payer_telegram_id: int) -> Dict[int, float]:
        """Calculate flexible split allocations"""
        
        if split_type == "split_5":
            # На всех 5 поровну
            users = cls.get_users_for_split(db, split_type, profile_id)
            if not users:
                return {}
            
            share_per_user = amount / len(users)
            allocations = {}
            for user in users:
                allocations[user.id] = share_per_user
            return allocations
            
        elif split_type == "split_4":
            # На всех кроме Миши (4 человека)
            users = cls.get_users_for_split(db, split_type, profile_id)
            if not users:
                return {}
            
            share_per_user = amount / len(users)
            allocations = {}
            for user in users:
                allocations[user.id] = share_per_user
            return allocations
            
        elif split_type == "split_families":
            # За другую семью (без плательщика)
            if payer_telegram_id in cls.GROUP_1_IDS:
                # Платит группа 1 (Сеня + Даша), значит платит группа 2 (Катя + Дима + Миша)
                target_users = db.query(User).filter(
                    User.telegram_id.in_(cls.GROUP_2_IDS)
                ).all()
            else:
                # Платит группа 2 (Катя + Дима + Миша), значит платит группа 1 (Сеня + Даша)
                target_users = db.query(User).filter(
                    User.telegram_id.in_(cls.GROUP_1_IDS)
                ).all()
            
            if not target_users:
                return {}
            
            # Делим сумму на количество людей в целевой группе
            share_per_user = amount / len(target_users)
            allocations = {}
            for user in target_users:
                allocations[user.id] = share_per_user
            return allocations
            
        else:
            return {}

    @classmethod
    def get_split_description(cls, split_type: str) -> str:
        """Get human-readable description of split type"""
        
        if split_type == "split_5":
            return "на всех 5 поровну"
        elif split_type == "split_4":
            return "на всех кроме Миши (4 человека)"
        elif split_type == "split_families":
            return "за другую семью (без моей группы)"
        else:
            return "неизвестно"

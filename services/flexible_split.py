#!/usr/bin/env python3
"""
Flexible expense splitting service for "OTHER" category
Allows users to select specific participants for expense splitting
"""

from sqlalchemy.orm import Session
from models import User, Profile, ProfileMember
from typing import Dict, List, Set
from decimal import Decimal

class FlexibleSplitService:
    """Service for flexible expense splitting with participant selection"""

    # Определяем группы пользователей
    GROUP_1_IDS = [804085588, 916228993]  # Сеня + Даша
    GROUP_2_IDS = [252901018, 350653235, 6379711500]  # Катя + Дима + Миша

    @classmethod
    def get_all_users(cls, db: Session) -> List[User]:
        """Get all available users"""
        return db.query(User).filter(
            User.telegram_id.in_(cls.GROUP_1_IDS + cls.GROUP_2_IDS)
        ).all()

    @classmethod
    def get_user_by_telegram_id(cls, db: Session, telegram_id: int) -> User:
        """Get user by telegram_id"""
        return db.query(User).filter(User.telegram_id == telegram_id).first()

    @classmethod
    def get_user_name(cls, user: User) -> str:
        """Get user display name"""
        if user.first_name:
            return user.first_name
        elif user.username:
            return user.username
        else:
            return f"User {user.telegram_id}"

    @classmethod
    def calculate_participant_split(cls, db: Session, amount: float, 
                                  selected_participant_telegram_ids: Set[int], 
                                  payer_telegram_id: int) -> Dict[int, float]:
        """Calculate split based on selected participants - only opposite group pays"""
        
        if not selected_participant_telegram_ids:
            return {}
        
        # Получаем пользователя-плательщика
        payer_user = cls.get_user_by_telegram_id(db, payer_telegram_id)
        if not payer_user:
            return {}
        
        # Определяем, к какой группе принадлежит плательщик
        if payer_user.telegram_id in cls.GROUP_1_IDS:
            # Плательщик из группы 1 (Сеня + Даша), долг на группу 2
            opposite_group_ids = cls.GROUP_2_IDS
        else:
            # Плательщик из группы 2 (Дима + Катя + Миша), долг на группу 1
            opposite_group_ids = cls.GROUP_1_IDS
        
        # Находим участников из противоположной группы
        opposite_group_participants = []
        for participant_telegram_id in selected_participant_telegram_ids:
            if participant_telegram_id in opposite_group_ids:
                participant_user = db.query(User).filter(User.telegram_id == participant_telegram_id).first()
                if participant_user:
                    opposite_group_participants.append(participant_user.id)
        
        if not opposite_group_participants:
            # Если нет участников из противоположной группы, никто ничего не должен
            return {}
        
        # Рассчитываем долю на каждого участника из противоположной группы
        # Делим сумму на общее количество участников, но долг только с противоположной группы
        total_participants = len(selected_participant_telegram_ids)
        share_per_participant = amount / total_participants
        
        allocations = {}
        for participant_id in opposite_group_participants:
            allocations[participant_id] = share_per_participant
        
        return allocations

    @classmethod
    def calculate_family_split(cls, db: Session, amount: float, 
                             payer_telegram_id: int) -> Dict[int, float]:
        """Calculate split for 'За другую семью' - entire amount goes to opposite group"""
        
        # Определяем, к какой группе принадлежит плательщик
        if payer_telegram_id in cls.GROUP_1_IDS:
            # Плательщик из группы 1 (Сеня + Даша), весь долг на группу 2
            target_group_ids = cls.GROUP_2_IDS
        else:
            # Плательщик из группы 2 (Дима + Катя + Миша), весь долг на группу 1
            target_group_ids = cls.GROUP_1_IDS
        
        # Получаем пользователей целевой группы
        target_users = db.query(User).filter(
            User.telegram_id.in_(target_group_ids)
        ).all()
        
        if not target_users:
            return {}
        
        # Делим сумму поровну между всеми в целевой группе
        share_per_user = amount / len(target_users)
        allocations = {}
        for user in target_users:
            allocations[user.id] = share_per_user
        
        return allocations

    @classmethod
    def get_split_description(cls, split_type: str, selected_participants: List[str] = None) -> str:
        """Get description for split type"""
        
        if split_type == "participants" and selected_participants:
            participant_names = ", ".join(selected_participants)
            return f"Участники: {participant_names}"
        elif split_type == "split_families":
            return "За другую семью (без моей группы)"
        else:
            return "Неизвестный тип разделения"

    @classmethod
    def get_participant_selection_text(cls, selected_participants: Set[int], db: Session) -> str:
        """Get text showing currently selected participants"""
        if not selected_participants:
            return "👥 Выберите участников расхода:\n\nНикто не выбран"
        
        participant_names = []
        for user_id in selected_participants:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                name = cls.get_user_name(user)
                participant_names.append(f"✅ {name}")
        
        text = "👥 Выбранные участники:\n\n"
        text += "\n".join(participant_names)
        text += f"\n\nВсего участников: {len(selected_participants)}"
        
        return text

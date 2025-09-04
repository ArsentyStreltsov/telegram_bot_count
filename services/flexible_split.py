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
                                  selected_participant_ids: Set[int], 
                                  payer_telegram_id: int) -> Dict[int, float]:
        """Calculate split based on selected participants"""
        
        print(f"🔍 DEBUG: calculate_participant_split called")
        print(f"🔍 DEBUG: amount={amount}, selected_participant_ids={selected_participant_ids}, payer_telegram_id={payer_telegram_id}")
        
        if not selected_participant_ids:
            print("🔍 DEBUG: No participants selected")
            return {}
        
        # Исключаем плательщика из расчета долга
        participants_without_payer = selected_participant_ids.copy()
        
        # Получаем пользователя-плательщика
        payer_user = cls.get_user_by_telegram_id(db, payer_telegram_id)
        if payer_user:
            print(f"🔍 DEBUG: Payer user: {payer_user.first_name} (ID: {payer_user.id})")
            if payer_user.id in participants_without_payer:
                participants_without_payer.remove(payer_user.id)
                print(f"🔍 DEBUG: Removed payer from participants")
        
        if not participants_without_payer:
            print("🔍 DEBUG: No participants left after removing payer")
            return {}
        
        print(f"🔍 DEBUG: Participants without payer: {participants_without_payer}")
        
        # Рассчитываем долю на каждого участника (кроме плательщика)
        share_per_participant = amount / len(participants_without_payer)
        print(f"🔍 DEBUG: Share per participant: {share_per_participant}")
        
        allocations = {}
        for participant_id in participants_without_payer:
            allocations[participant_id] = share_per_participant
            print(f"🔍 DEBUG: Allocation for user_id {participant_id}: {share_per_participant}")
        
        print(f"🔍 DEBUG: Final allocations: {allocations}")
        return allocations

    @classmethod
    def calculate_family_split(cls, db: Session, amount: float, 
                             payer_telegram_id: int) -> Dict[int, float]:
        """Calculate split for 'За другую семью' - entire amount goes to opposite group"""
        
        print(f"🔍 DEBUG: calculate_family_split called with amount={amount}, payer_telegram_id={payer_telegram_id}")
        print(f"🔍 DEBUG: GROUP_1_IDS = {cls.GROUP_1_IDS}")
        print(f"🔍 DEBUG: GROUP_2_IDS = {cls.GROUP_2_IDS}")
        
        # Определяем, к какой группе принадлежит плательщик
        if payer_telegram_id in cls.GROUP_1_IDS:
            # Плательщик из группы 1 (Сеня + Даша), весь долг на группу 2
            target_group_ids = cls.GROUP_2_IDS
            print(f"🔍 DEBUG: Плательщик из группы 1, целевая группа: {target_group_ids}")
        else:
            # Плательщик из группы 2 (Дима + Катя + Миша), весь долг на группу 1
            target_group_ids = cls.GROUP_1_IDS
            print(f"🔍 DEBUG: Плательщик из группы 2, целевая группа: {target_group_ids}")
        
        # Получаем пользователей целевой группы
        target_users = db.query(User).filter(
            User.telegram_id.in_(target_group_ids)
        ).all()
        
        print(f"🔍 DEBUG: Найдено пользователей в целевой группе: {len(target_users)}")
        for user in target_users:
            print(f"🔍 DEBUG: Пользователь: {user.first_name} (ID: {user.id}, telegram_id: {user.telegram_id})")
        
        if not target_users:
            print("❌ DEBUG: Нет пользователей в целевой группе!")
            return {}
        
        # Делим сумму поровну между всеми в целевой группе
        share_per_user = amount / len(target_users)
        allocations = {}
        for user in target_users:
            allocations[user.id] = share_per_user
            print(f"🔍 DEBUG: Аллокация для {user.first_name}: {share_per_user}")
        
        print(f"🔍 DEBUG: Итоговые аллокации: {allocations}")
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
    def get_participant_selection_text(cls, selected_participants: Set[int], db: Session = None) -> str:
        """Get text showing currently selected participants"""
        if not selected_participants:
            return "👥 Выберите участников расхода:\n\nНикто не выбран"
        
        # Map telegram_ids to names
        telegram_to_name = {
            804085588: "Сеня",
            916228993: "Даша", 
            350653235: "Дима",
            252901018: "Катя",
            6379711500: "Миша"
        }
        
        participant_names = []
        for telegram_id in selected_participants:
            name = telegram_to_name.get(telegram_id, f"User {telegram_id}")
            participant_names.append(f"✅ {name}")
        
        text = "👥 Выбранные участники:\n\n"
        text += "\n".join(participant_names)
        text += f"\n\nВсего участников: {len(selected_participants)}"
        
        return text

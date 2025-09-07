"""
Duty schedule management service - Improved architecture
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, deque
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from models import DutyTask, DutySchedule, User, Profile, ProfileMember, DutyTaskType
import calendar


class DutyService:
    """Service for managing duty schedules with improved architecture"""
    
    # Configuration constants
    SAME_TASK_COOLDOWN_DAYS = 2  # нельзя давать ту же задачу этому человеку в последние 2 дня
    ALLOW_OVER_ASSIGN_WEEKDAYS = False  # по будням строго не более 1 задачи на человека
    
    @staticmethod
    def initialize_default_tasks(db: Session) -> None:
        """Initialize default duty tasks with proper task types"""
        # Check if tasks already exist
        if db.query(DutyTask).count() > 0:
            return
            
        default_tasks = [
            # Будни
            {"name": "Приготовить ужин", "description": "Приготовить ужин для всей семьи",
             "is_weekday_only": True, "frequency_days": 1, "task_type": DutyTaskType.COOKING},
            {"name": "Убрать со стола", "description": "Помыть посуду после ужина, убрать со стола",
             "is_weekday_only": True, "frequency_days": 1, "task_type": DutyTaskType.CLEANING},
            {"name": "Вынос мусора", "description": "Вынести мусор и зарядить новые пакеты",
             "is_weekday_only": True, "frequency_days": 2, "task_type": DutyTaskType.OTHER},
            
            # Выходные
            {"name": "Приготовить завтрак", "description": "Приготовить завтрак для всей семьи",
             "is_weekend_only": True, "frequency_days": 1, "task_type": DutyTaskType.COOKING},
            {"name": "Убрать посуду после завтрака", "description": "Помыть посуду после завтрака",
             "is_weekend_only": True, "frequency_days": 1, "task_type": DutyTaskType.CLEANING},
            {"name": "Приготовить обед", "description": "Приготовить обед для всей семьи",
             "is_weekend_only": True, "frequency_days": 1, "task_type": DutyTaskType.COOKING},
            {"name": "Убрать посуду после обеда", "description": "Помыть посуду после обеда",
             "is_weekend_only": True, "frequency_days": 1, "task_type": DutyTaskType.CLEANING},
            {"name": "Уборка пылесосом", "description": "Пропылесосить все комнаты",
             "is_weekend_only": True, "frequency_days": 7, "task_type": DutyTaskType.CLEANING},
            {"name": "Протереть окна/зеркала", "description": "Протереть все окна и зеркала",
             "is_weekend_only": True, "frequency_days": 7, "task_type": DutyTaskType.CLEANING},
            {"name": "Убрать туалеты", "description": "Помыть туалеты, раковины, зеркала",
             "is_weekend_only": True, "frequency_days": 7, "task_type": DutyTaskType.CLEANING},
        ]
        
        for task_data in default_tasks:
            task = DutyTask(**task_data)
            db.add(task)
        
        db.commit()
    
    @staticmethod
    def get_all_tasks(db: Session) -> List[DutyTask]:
        """Get all duty tasks"""
        return db.query(DutyTask).order_by(DutyTask.name).all()
    
    @staticmethod
    def get_available_users(db: Session) -> List[User]:
        """Get all users from the default profile"""
        default_profile = db.query(Profile).filter(Profile.is_default == True).first()
        if not default_profile:
            return []
        
        members = db.query(ProfileMember).filter(ProfileMember.profile_id == default_profile.id).all()
        user_ids = [member.user_id for member in members]
        return db.query(User).filter(User.id.in_(user_ids)).all()
    
    @staticmethod
    def generate_schedule_for_month(db: Session, year: int, month: int) -> Dict[str, List[DutySchedule]]:
        """Generate duty schedule for a specific month with improved algorithm"""
        DutyService.initialize_default_tasks(db)
        tasks: List[DutyTask] = DutyService.get_all_tasks(db)
        users: List[User] = DutyService.get_available_users(db)
        
        if not users:
            return {}
        
        start_date = date(year, month, 1)
        end_date = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1))
        
        # Предзагрузим уже существующие назначения за месяц + 7 дней до начала (для cooldown)
        preload_start = start_date - timedelta(days=7)
        existing: List[DutySchedule] = (
            db.query(DutySchedule)
              .options(joinedload(DutySchedule.task), joinedload(DutySchedule.assigned_user))
              .filter(DutySchedule.date >= preload_start, DutySchedule.date <= end_date)
              .all()
        )
        
        # Быстрые индексы в памяти
        assignments_by_date: Dict[date, List[DutySchedule]] = defaultdict(list)
        last_assigned_task_date: Dict[Tuple[int, int], date] = {}  # (user_id, task_id) -> last date
        total_counts_month: Dict[int, int] = defaultdict(int)  # user_id -> total in target month
        type_counts_month: Dict[Tuple[int, DutyTaskType], int] = defaultdict(int)  # (user_id, type) -> count
        
        for s in existing:
            assignments_by_date[s.date].append(s)
            if s.date <= end_date:
                last_assigned_task_date[(s.assigned_user_id, s.task_id)] = max(
                    last_assigned_task_date.get((s.assigned_user_id, s.task_id), s.date), s.date
                )
            if start_date <= s.date <= end_date:
                total_counts_month[s.assigned_user_id] += 1
                type_counts_month[(s.assigned_user_id, s.task.task_type)] += 1
        
        # Round-robin очередь пользователей, чтобы было честное стат. чередование
        user_queue = deque(sorted(users, key=lambda u: u.id))
        
        current = start_date
        created = 0
        
        while current <= end_date:
            is_weekend = current.weekday() >= 5
            # Уже назначенные на день (если перегенерация частичная/идемпотентность)
            taken_today: Dict[int, int] = defaultdict(int)  # user_id -> count today
            for s in assignments_by_date.get(current, []):
                taken_today[s.assigned_user_id] += 1
            
            # Отобрать задачи на день
            day_tasks = [t for t in tasks if DutyService._should_schedule_task(t, current, is_weekend)]
            
            # Сортировка по типу для более предсказуемого распределения
            day_tasks.sort(key=lambda t: (t.task_type.value, t.id))
            
            for task in day_tasks:
                # Пропустить, если уже есть запись для этой (task_id, date)
                if any(s.task_id == task.id for s in assignments_by_date.get(current, [])):
                    continue
                
                # Кандидаты
                candidates = []
                for _ in range(len(user_queue)):
                    user = user_queue[0]
                    
                    # Будни: не более 1 задания на человека
                    if not is_weekend and not DutyService.ALLOW_OVER_ASSIGN_WEEKDAYS and taken_today[user.id] >= 1:
                        user_queue.rotate(-1)
                        continue
                    
                    # Cooldown по одинаковой задаче
                    last_date = last_assigned_task_date.get((user.id, task.id))
                    if last_date and (current - last_date).days < DutyService.SAME_TASK_COOLDOWN_DAYS:
                        user_queue.rotate(-1)
                        continue
                    
                    # Кандидат годится
                    candidates.append(user)
                    user_queue.rotate(-1)
                
                if not candidates:
                    # Если никого не нашли: на буднях — оставляем незаполненным (или включай ALLOW_OVER_ASSIGN_WEEKDAYS)
                    if is_weekend or DutyService.ALLOW_OVER_ASSIGN_WEEKDAYS:
                        # Ослабим правило по будням при включенном флаге: разрешим 2 задачи,
                        # либо на выходных всегда можно больше 1.
                        candidates = list(users)
                    else:
                        continue  # пропускаем задачу
                
                # Выбор лучшего кандидата: минимизируем перекосы
                def score(u: User) -> tuple:
                    return (
                        total_counts_month.get(u.id, 0),                             # меньше всего всего задач
                        type_counts_month.get((u.id, task.task_type), 0),            # меньше всего задач этого типа
                        taken_today.get(u.id, 0),                                     # меньше уже взято сегодня
                        u.id                                                          # стабильный tie-breaker
                    )
                
                best = min(candidates, key=score)
                
                new_s = DutySchedule(
                    task_id=task.id,
                    assigned_user_id=best.id,
                    date=current,
                    is_completed=False
                )
                db.add(new_s)
                
                # Обновим индексы
                assignments_by_date[current].append(new_s)
                last_assigned_task_date[(best.id, task.id)] = current
                if start_date <= current <= end_date:
                    total_counts_month[best.id] += 1
                    type_counts_month[(best.id, task.task_type)] += 1
                taken_today[best.id] += 1
                created += 1
            
            current += timedelta(days=1)
        
        db.commit()
        return DutyService._group_schedules_by_date(db, start_date, end_date)
    
    @staticmethod
    def _should_schedule_task(task: DutyTask, current_date: date, is_weekend: bool) -> bool:
        """Check if task should be scheduled for given date"""
        if task.is_weekday_only and is_weekend:
            return False
        if task.is_weekend_only and not is_weekend:
            return False
        
        # Check frequency
        if task.frequency_days > 1:
            # Привязка к началу месяца (можно заменить на anchor_date при необходимости)
            days_since_start = (current_date - date(current_date.year, current_date.month, 1)).days
            if days_since_start % task.frequency_days != 0:
                return False
        
        return True
    
    @staticmethod
    def _group_schedules_by_date(db: Session, start_date: date, end_date: date) -> Dict[str, List[DutySchedule]]:
        """Group schedules by date for display"""
        schedules = db.query(DutySchedule).filter(
            and_(
                DutySchedule.date >= start_date,
                DutySchedule.date <= end_date
            )
        ).order_by(DutySchedule.date, DutySchedule.task_id).all()
        
        grouped = {}
        for schedule in schedules:
            date_str = schedule.date.strftime("%Y-%m-%d")
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(schedule)
        
        return grouped
    
    @staticmethod
    def get_schedule_for_date_range(db: Session, start_date: date, end_date: date) -> Dict[str, List[DutySchedule]]:
        """Get existing schedule for date range"""
        return DutyService._group_schedules_by_date(db, start_date, end_date)
    
    @staticmethod
    def mark_task_completed(db: Session, schedule_id: int, user_id: int) -> bool:
        """Mark a duty task as completed"""
        schedule = db.query(DutySchedule).filter(DutySchedule.id == schedule_id).first()
        if not schedule:
            return False
        
        schedule.is_completed = True
        schedule.completed_at = datetime.utcnow()
        db.commit()
        return True
    
    @staticmethod
    def get_user_duties_for_date(db: Session, user_id: int, target_date: date) -> List[DutySchedule]:
        """Get all duties for a specific user on a specific date"""
        return db.query(DutySchedule).filter(
            and_(
                DutySchedule.assigned_user_id == user_id,
                DutySchedule.date == target_date
            )
        ).all()
    
    @staticmethod
    def get_user_duties_for_week(db: Session, user_id: int, start_date: date) -> Dict[str, List[DutySchedule]]:
        """Get all duties for a specific user for a week starting from start_date"""
        end_date = start_date + timedelta(days=6)
        
        schedules = db.query(DutySchedule).filter(
            and_(
                DutySchedule.assigned_user_id == user_id,
                DutySchedule.date >= start_date,
                DutySchedule.date <= end_date
            )
        ).order_by(DutySchedule.date).all()
        
        grouped = {}
        for schedule in schedules:
            date_str = schedule.date.strftime("%Y-%m-%d")
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(schedule)
        
        return grouped
    
    @staticmethod
    def wipe_month(db: Session, year: int, month: int) -> int:
        """Remove all uncompleted assignments for a month (for regeneration)"""
        start_date = date(year, month, 1)
        end_date = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1))
        
        deleted = (db.query(DutySchedule)
                     .filter(DutySchedule.date >= start_date,
                             DutySchedule.date <= end_date,
                             DutySchedule.is_completed == False)
                     ).delete(synchronize_session=False)
        db.commit()
        return deleted
#!/usr/bin/env python3
"""
Детальный тест ограничений на задания
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from services.duty_service import DutyService
from models import DutyTask, DutySchedule, DutyTaskType, User
from db import init_db, get_db

def test_detailed_restrictions():
    """Детальный тест ограничений"""
    print("🧪 Детальный тест ограничений на задания")
    
    # Инициализируем БД
    init_db()
    db = next(get_db())
    
    # Получаем всех пользователей
    users = db.query(User).all()
    print(f"\n👥 Пользователи в системе:")
    for user in users:
        name = user.first_name or user.username or "Неизвестно"
        print(f"  - {name} (first_name: '{user.first_name}', username: '{user.username}')")
    
    # Получаем задачу "Вынос мусора"
    garbage_task = db.query(DutyTask).filter(DutyTask.name.like("%мусор%")).first()
    if not garbage_task:
        print("❌ Задача 'Вынос мусора' не найдена")
        return
    
    print(f"\n🗑️ Тестируем задачу: {garbage_task.name}")
    
    # Тестируем каждого пользователя
    for user in users:
        name = user.first_name or user.username or "Неизвестно"
        can_do = DutyService._can_user_do_task(user, garbage_task)
        status = "✅" if can_do else "❌"
        
        # Детальная информация
        user_name_for_check = user.first_name or user.username or ""
        print(f"  {status} {name}:")
        print(f"    - first_name: '{user.first_name}'")
        print(f"    - username: '{user.username}'")
        print(f"    - user_name_for_check: '{user_name_for_check}'")
        print(f"    - user_name_for_check.lower(): '{user_name_for_check.lower()}'")
        print(f"    - can_do: {can_do}")
        print()
    
    db.close()

if __name__ == "__main__":
    test_detailed_restrictions()


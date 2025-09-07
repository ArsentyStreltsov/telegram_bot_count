#!/usr/bin/env python3
"""
Тест ограничений на задания
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from services.duty_service import DutyService
from models import DutyTask, DutySchedule, DutyTaskType, User
from db import init_db, get_db

def test_task_restrictions():
    """Тестируем ограничения на задания"""
    print("🧪 Тестируем ограничения на задания")
    
    # Инициализируем БД
    init_db()
    db = next(get_db())
    
    # Получаем всех пользователей
    users = db.query(User).all()
    print(f"\n👥 Пользователи в системе:")
    for user in users:
        name = user.first_name or user.username or "Неизвестно"
        print(f"  - {name} (ID: {user.id})")
    
    # Получаем задачи
    tasks = db.query(DutyTask).all()
    print(f"\n📋 Задачи в системе:")
    for task in tasks:
        print(f"  - {task.name}")
    
    # Тестируем ограничения
    print(f"\n🔍 Проверяем ограничения:")
    
    # Найдем задачи
    garbage_task = db.query(DutyTask).filter(DutyTask.name.like("%мусор%")).first()
    floor_tasks = db.query(DutyTask).filter(
        DutyTask.name.like("%полы%") | DutyTask.name.like("%пылесос%")
    ).all()
    
    if garbage_task:
        print(f"\n🗑️ Задача: {garbage_task.name}")
        for user in users:
            name = user.first_name or user.username or "Неизвестно"
            can_do = DutyService._can_user_do_task(user, garbage_task)
            status = "✅" if can_do else "❌"
            print(f"  {status} {name}: {'может' if can_do else 'не может'}")
    
    for task in floor_tasks:
        print(f"\n🏠 Задача: {task.name}")
        for user in users:
            name = user.first_name or user.username or "Неизвестно"
            can_do = DutyService._can_user_do_task(user, task)
            status = "✅" if can_do else "❌"
            print(f"  {status} {name}: {'может' if can_do else 'не может'}")
    
    # Тестируем полное расписание
    print(f"\n📅 Генерируем тестовое расписание для проверки ограничений...")
    schedules = DutyService.generate_schedule_for_month(db, 2024, 9)
    
    # Проверяем нарушения ограничений
    violations = []
    for date_str, duties in schedules.items():
        for duty in duties:
            if not DutyService._can_user_do_task(duty.assigned_user, duty.task):
                user_name = duty.assigned_user.first_name or duty.assigned_user.username or "Неизвестно"
                violations.append(f"{date_str}: {user_name} назначен на {duty.task.name}")
    
    if violations:
        print(f"\n❌ Найдены нарушения ограничений:")
        for violation in violations:
            print(f"  - {violation}")
    else:
        print(f"\n✅ Ограничения соблюдены! Нарушений не найдено.")
    
    # Показываем статистику по заданиям
    print(f"\n📊 Статистика назначений:")
    task_stats = {}
    for date_str, duties in schedules.items():
        for duty in duties:
            task_name = duty.task.name
            user_name = duty.assigned_user.first_name or duty.assigned_user.username or "Неизвестно"
            if task_name not in task_stats:
                task_stats[task_name] = []
            task_stats[task_name].append(user_name)
    
    for task_name, assignees in task_stats.items():
        print(f"\n📋 {task_name}:")
        for assignee in assignees:
            print(f"  - {assignee}")
    
    db.close()
    print(f"\n✅ Тест завершен!")

if __name__ == "__main__":
    test_task_restrictions()

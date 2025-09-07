#!/usr/bin/env python3
"""
Тест исправления выходных дней - проверяем, что домашние дела назначаются только на субботу
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from services.duty_service import DutyService
from models import DutyTask, DutyTaskType
from db import init_db, get_db

def test_weekend_scheduling():
    """Тестируем новую логику выходных дней"""
    print("🧪 Тестируем исправленную логику выходных дней")
    
    # Инициализируем БД
    init_db()
    db = next(get_db())
    
    # Получаем все задачи
    tasks = db.query(DutyTask).all()
    print(f"\n📋 Всего задач: {len(tasks)}")
    
    # Тестируем выходные дни (суббота и воскресенье)
    test_dates = [
        date(2024, 9, 7),  # Суббота
        date(2024, 9, 8),  # Воскресенье
    ]
    
    for test_date in test_dates:
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][test_date.weekday()]
        is_weekend = test_date.weekday() >= 5
        
        print(f"\n📅 {day_name} {test_date.strftime('%d.%m.%Y')} (выходной: {is_weekend}):")
        
        # Проверяем каждую задачу
        for task in tasks:
            if task.is_weekend_only:
                should_schedule = DutyService._should_schedule_task(task, test_date, is_weekend)
                status = "✅" if should_schedule else "❌"
                print(f"  {status} {task.name} (частота: {task.frequency_days} дней)")
    
    # Проверяем конкретно домашние дела
    print(f"\n🏠 Проверяем домашние дела:")
    household_tasks = ["Пропылесосить полы", "Помыть полы", "Убрать туалеты", "Протереть поверхности"]
    
    for task_name in household_tasks:
        task = db.query(DutyTask).filter(DutyTask.name == task_name).first()
        if task:
            print(f"\n📋 {task_name}:")
            for test_date in test_dates:
                day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][test_date.weekday()]
                should_schedule = DutyService._should_schedule_task(task, test_date, True)
                status = "✅" if should_schedule else "❌"
                print(f"  {day_name} {test_date.strftime('%d.%m')}: {status}")
    
    db.close()
    print(f"\n✅ Тест завершен!")

if __name__ == "__main__":
    test_weekend_scheduling()

#!/usr/bin/env python3
"""
Debug script to check why weekend cleaning tasks are not appearing
"""
import os
import sys
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_db
from services.duty_service import DutyService
from models import DutyTask, DutyTaskType

def debug_weekend_tasks():
    """Debug why weekend cleaning tasks are not appearing"""
    print("🔍 Отладка задач выходных дней")
    
    # Initialize database
    init_db()
    db = next(get_db())
    
    try:
        # Get all tasks
        tasks = DutyService.get_all_tasks(db)
        
        print(f"\n📋 Всего задач в БД: {len(tasks)}")
        
        # Show all tasks
        for task in tasks:
            print(f"  - {task.name} (тип: {task.task_type.value}, выходные: {task.is_weekend_only}, частота: {task.frequency_days} дней)")
        
        # Check specific weekend dates
        test_dates = [
            date(2025, 9, 6),  # Saturday
            date(2025, 9, 7),  # Sunday
            date(2025, 9, 13), # Saturday
            date(2025, 9, 14), # Sunday
        ]
        
        print(f"\n📅 Проверка задач для выходных дней:")
        
        for test_date in test_dates:
            is_weekend = test_date.weekday() >= 5
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][test_date.weekday()]
            
            print(f"\n{day_name} {test_date.strftime('%d.%m.%Y')} (выходной: {is_weekend}):")
            
            for task in tasks:
                should_schedule = DutyService._should_schedule_task(task, test_date, is_weekend)
                if should_schedule:
                    print(f"  ✅ {task.name}")
                else:
                    print(f"  ❌ {task.name}")
        
        # Check floor cleaning logic specifically
        print(f"\n🧹 Проверка логики пылесос/мытье полов:")
        
        vacuum_task = next((t for t in tasks if t.name == "Пропылесосить полы"), None)
        mop_task = next((t for t in tasks if t.name == "Помыть полы"), None)
        
        if vacuum_task and mop_task:
            for test_date in test_dates:
                vacuum_should = DutyService._should_schedule_floor_cleaning(vacuum_task, test_date)
                mop_should = DutyService._should_schedule_floor_cleaning(mop_task, test_date)
                
                day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][test_date.weekday()]
                print(f"  {day_name} {test_date.strftime('%d.%m')}: пылесос={vacuum_should}, мытье={mop_should}")
        else:
            print("  ❌ Задачи пылесос/мытье полов не найдены!")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_weekend_tasks()

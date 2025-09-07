#!/usr/bin/env python3
"""
Test script for duty rotation algorithm
"""
import os
import sys
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_db
from services.duty_service import DutyService
from models import User, Profile, ProfileMember

def test_duty_rotation():
    """Test the duty rotation algorithm"""
    print("🧪 Тестирование алгоритма чередования дежурств")
    
    # Initialize database
    init_db()
    db = next(get_db())
    
    try:
        # Get current month
        today = date.today()
        year = today.year
        month = today.month
        
        print(f"📅 Генерируем график для {today.strftime('%B %Y')}")
        
        # Clear existing schedules for this month
        from models import DutySchedule
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Delete existing schedules
        db.query(DutySchedule).filter(
            DutySchedule.date >= start_date,
            DutySchedule.date <= end_date
        ).delete()
        db.commit()
        
        # Generate new schedule
        schedules = DutyService.generate_schedule_for_month(db, year, month)
        
        if not schedules:
            print("❌ Не удалось сгенерировать график")
            return
        
        print(f"✅ График сгенерирован! Создано {sum(len(day_duties) for day_duties in schedules.values())} назначений")
        
        # Analyze the schedule for rotation quality
        print("\n📊 Анализ чередования:")
        
        # Get users
        users = DutyService.get_available_users(db)
        user_names = {user.id: user.first_name or user.username or f"User{user.id}" for user in users}
        
        # Analyze first week
        first_week_dates = sorted(schedules.keys())[:7]
        
        for date_str in first_week_dates:
            duty_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][duty_date.weekday()]
            
            print(f"\n{day_name} {duty_date.strftime('%d.%m')}:")
            
            # Group by user
            user_duties = {}
            for duty in schedules[date_str]:
                user_name = user_names[duty.assigned_user_id]
                if user_name not in user_duties:
                    user_duties[user_name] = []
                user_duties[user_name].append(duty.task.name)
            
            for user_name, tasks in user_duties.items():
                print(f"  {user_name}: {', '.join(tasks)}")
        
        # Check for conflicts (cooking + cleaning same day)
        print("\n🔍 Проверка конфликтов:")
        conflicts_found = 0
        
        for date_str, day_duties in schedules.items():
            user_tasks = {}
            for duty in day_duties:
                if duty.assigned_user_id not in user_tasks:
                    user_tasks[duty.assigned_user_id] = []
                user_tasks[duty.assigned_user_id].append(duty.task.name)
            
            for user_id, tasks in user_tasks.items():
                has_cooking = any("приготовить" in task.lower() for task in tasks)
                has_cleaning = any("убрать" in task.lower() for task in tasks)
                
                if has_cooking and has_cleaning:
                    user_name = user_names[user_id]
                    duty_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    print(f"  ⚠️  {user_name} на {duty_date.strftime('%d.%m')}: готовка + уборка")
                    conflicts_found += 1
        
        if conflicts_found == 0:
            print("  ✅ Конфликтов не найдено!")
        else:
            print(f"  ⚠️  Найдено {conflicts_found} конфликтов")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_duty_rotation()

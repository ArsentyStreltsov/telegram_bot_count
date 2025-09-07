#!/usr/bin/env python3
"""
Reset duty tables to apply new schema
"""
import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_db
from models import DutyTask, DutySchedule
from sqlalchemy import text

def reset_duty_tables():
    """Reset duty tables to apply new schema"""
    print("🔄 Сброс таблиц дежурств для применения новой схемы")
    
    db = next(get_db())
    try:
        # Drop existing tables
        print("🗑️  Удаляем старые таблицы...")
        db.execute(text("DROP TABLE IF EXISTS duty_schedules CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS duty_tasks CASCADE"))
        db.commit()
        print("✅ Старые таблицы удалены")
        
        # Recreate tables
        print("🔨 Создаем новые таблицы...")
        DutyTask.__table__.create(db.bind, checkfirst=True)
        DutySchedule.__table__.create(db.bind, checkfirst=True)
        db.commit()
        print("✅ Новые таблицы созданы")
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_duty_tables()

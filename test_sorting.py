#!/usr/bin/env python3
"""
Тест сортировки заданий в правильном порядке
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from services.duty_service import DutyService
from models import DutyTask, DutySchedule, DutyTaskType, User
from db import init_db, get_db

def test_task_sorting():
    """Тестируем сортировку заданий"""
    print("🧪 Тестируем сортировку заданий в правильном порядке")
    
    # Инициализируем БД
    init_db()
    db = next(get_db())
    
    # Получаем пользователя для тестирования
    user = db.query(User).first()
    if not user:
        print("❌ Нет пользователей в БД")
        return
    
    # Создаем тестовые задания в неправильном порядке
    test_tasks = [
        "Убрать посуду после ужина",
        "Приготовить завтрак", 
        "Убрать посуду после обеда",
        "Приготовить обед",
        "Убрать посуду после завтрака",
        "Приготовить ужин",
        "Протереть поверхности",
        "Убрать туалеты",
        "Помыть полы"
    ]
    
    # Создаем тестовые DutySchedule объекты
    test_duties = []
    for i, task_name in enumerate(test_tasks):
        task = db.query(DutyTask).filter(DutyTask.name == task_name).first()
        if task:
            duty = DutySchedule()
            duty.task = task
            duty.assigned_user = user
            duty.date = date.today()
            duty.is_completed = False
            test_duties.append(duty)
    
    print(f"\n📋 Исходный порядок заданий:")
    for i, duty in enumerate(test_duties, 1):
        print(f"  {i}. {duty.task.name}")
    
    # Импортируем функцию сортировки
    from handlers.duty import sort_duties_by_meal_order
    
    # Сортируем
    sorted_duties = sort_duties_by_meal_order(test_duties)
    
    print(f"\n📋 Отсортированный порядок заданий:")
    for i, duty in enumerate(sorted_duties, 1):
        print(f"  {i}. {duty.task.name}")
    
    # Проверяем правильность сортировки
    expected_order = [
        "Приготовить завтрак",
        "Убрать посуду после завтрака", 
        "Приготовить обед",
        "Убрать посуду после обеда",
        "Приготовить ужин",
        "Убрать посуду после ужина",
        "Помыть полы",
        "Убрать туалеты", 
        "Протереть поверхности"
    ]
    
    print(f"\n✅ Ожидаемый порядок:")
    for i, task_name in enumerate(expected_order, 1):
        print(f"  {i}. {task_name}")
    
    # Проверяем соответствие
    is_correct = True
    for i, duty in enumerate(sorted_duties):
        if i < len(expected_order) and duty.task.name != expected_order[i]:
            is_correct = False
            print(f"❌ Ошибка на позиции {i+1}: ожидалось '{expected_order[i]}', получено '{duty.task.name}'")
    
    if is_correct:
        print(f"\n🎉 Сортировка работает правильно!")
    else:
        print(f"\n❌ Сортировка работает неправильно!")
    
    db.close()

if __name__ == "__main__":
    test_task_sorting()

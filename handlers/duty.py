"""
Duty schedule handlers
"""
from datetime import datetime, date, timedelta
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from services.duty_service import DutyService
from utils.keyboards import back_keyboard
from db import get_db
from models import DutySchedule


def sort_duties_by_meal_order(duties: List[DutySchedule]) -> List[DutySchedule]:
    """Sort duties in logical meal order: breakfast -> lunch -> dinner, with cleaning after each"""
    def get_meal_order(duty):
        task_name = duty.task.name.lower()
        
        # Breakfast tasks
        if "завтрак" in task_name:
            if "приготовить" in task_name:
                return 1  # Cook breakfast
            elif "убрать" in task_name or "посуду" in task_name:
                return 2  # Clean after breakfast
        
        # Lunch tasks  
        elif "обед" in task_name:
            if "приготовить" in task_name:
                return 3  # Cook lunch
            elif "убрать" in task_name or "посуду" in task_name:
                return 4  # Clean after lunch
        
        # Dinner tasks
        elif "ужин" in task_name:
            if "приготовить" in task_name:
                return 5  # Cook dinner
            elif "убрать" in task_name or "посуду" in task_name:
                return 6  # Clean after dinner
        
        # Household tasks (last) - specific order
        elif "полы" in task_name and ("пылесос" in task_name or "помыть" in task_name):
            return 7  # Floor cleaning first
        elif "туалет" in task_name:
            return 8  # Toilets second
        elif "поверхност" in task_name:
            return 9  # Surfaces last
        
        # Other tasks
        else:
            return 10
    
    return sorted(duties, key=get_meal_order)


async def duty_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle duty schedule button - пока в разработке"""
    query = update.callback_query
    await query.answer()
    
    text = "🚧 **График дежурств**\n\n"
    text += "Раздел пока в разработке, но пока анекдот:\n\n"
    text += "Жарятся как-то 2 сосиски на сковородке и одна другой говорит:\n"
    text += "— Да, что-то тут становится жарковато\n\n"
    text += "Вторая отвечает:\n"
    text += "— Емае, говорящая сосиска! 😄"
    
    keyboard = back_keyboard("main_menu")
    
    await query.edit_message_text(
        text, 
        reply_markup=keyboard
    )


async def my_duties_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's duties for current week"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        user_id = query.from_user.id
        
        # Get user from database
        from models import User
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Get current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        
        # Get duties for the week
        duties = DutyService.get_user_duties_for_week(db, user.id, start_of_week)
        
        text = f"📋 **Мои дежурства на неделю**\n"
        text += f"📅 {start_of_week.strftime('%d.%m')} - {(start_of_week + timedelta(days=6)).strftime('%d.%m.%Y')}\n\n"
        
        if not duties:
            text += "🎉 На этой неделе у вас нет дежурств!"
        else:
            for date_str, day_duties in duties.items():
                duty_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][duty_date.weekday()]
                
                text += f"**{day_name} {duty_date.strftime('%d.%m')}:**\n"
                for duty in day_duties:
                    status = "✅" if duty.is_completed else "⏳"
                    text += f"  {status} {duty.task.name}\n"
                text += "\n"
        
        keyboard = back_keyboard("duty_schedule")
        await query.edit_message_text(
            text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def monthly_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly duty schedule"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        # Get current month
        today = date.today()
        year = today.year
        month = today.month
        
        # Check if schedule exists for this month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        schedules = DutyService.get_schedule_for_date_range(db, start_date, end_date)
        
        if not schedules:
            text = f"📅 **График на {today.strftime('%B %Y')}**\n\n"
            text += "❌ График не сгенерирован для этого месяца.\n"
            text += "Нажмите 'Сгенерировать график' для создания."
        else:
            text = f"📅 **График на {today.strftime('%B %Y')}**\n\n"
            
            # Show only current and future weeks to avoid message being too long
            current_date = start_date
            week_num = 1
            
            while current_date <= end_date:
                week_end = min(current_date + timedelta(days=6), end_date)
                
                # Skip past weeks (only show current week and future weeks)
                if week_end < today:
                    current_date += timedelta(days=7)
                    week_num += 1
                    continue
                
                text += f"**Неделя {week_num}** ({current_date.strftime('%d.%m')} - {week_end.strftime('%d.%m')}):\n"
                
                for i in range(7):
                    check_date = current_date + timedelta(days=i)
                    if check_date > end_date:
                        break
                    
                    date_str = check_date.strftime("%Y-%m-%d")
                    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][check_date.weekday()]
                    
                    if date_str in schedules:
                        text += f"  {day_name} {check_date.strftime('%d.%m')}:\n"
                        # Sort duties in logical meal order
                        sorted_duties = sort_duties_by_meal_order(schedules[date_str])
                        for duty in sorted_duties:
                            status = "✅" if duty.is_completed else "⏳"
                            user_name = duty.assigned_user.first_name or duty.assigned_user.username or "Неизвестно"
                            text += f"    {status} {duty.task.name} - {user_name}\n"
                
                text += "\n"
                current_date += timedelta(days=7)
                week_num += 1
        
        keyboard = back_keyboard("duty_schedule")
        
        # Check if message is too long (Telegram limit is 4096 characters)
        if len(text) > 4000:
            # Truncate and add note
            text = text[:3900] + "\n\n... (сообщение обрезано, показаны только ближайшие недели)"
        
        await query.edit_message_text(
            text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def current_week_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current week duty schedule only"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        # Get current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Get schedules for current week
        schedules = DutyService.get_schedule_for_date_range(db, start_of_week, end_of_week)
        
        text = f"📅 **График на текущую неделю**\n"
        text += f"📅 {start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m.%Y')}\n\n"
        
        if not schedules:
            text += "🎉 На этой неделе нет дежурств!"
        else:
            current_date = start_of_week
            while current_date <= end_of_week:
                date_str = current_date.strftime("%Y-%m-%d")
                day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][current_date.weekday()]
                
                if date_str in schedules:
                    text += f"**{day_name} {current_date.strftime('%d.%m')}:**\n"
                    # Sort duties in logical meal order
                    sorted_duties = sort_duties_by_meal_order(schedules[date_str])
                    for duty in sorted_duties:
                        status = "✅" if duty.is_completed else "⏳"
                        user_name = duty.assigned_user.first_name or duty.assigned_user.username or "Неизвестно"
                        text += f"  {status} {duty.task.name} - {user_name}\n"
                    text += "\n"
                
                current_date += timedelta(days=1)
        
        keyboard = back_keyboard("duty_schedule")
        await query.edit_message_text(
            text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def mark_completed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interface to mark duties as completed"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        user_id = query.from_user.id
        
        # Get user from database
        from models import User
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Get today's duties for this user
        today = date.today()
        today_duties = DutyService.get_user_duties_for_date(db, user.id, today)
        
        if not today_duties:
            text = f"📅 **Отметить выполнение**\n\n"
            text += f"🎉 У вас нет дежурств на сегодня ({today.strftime('%d.%m.%Y')})!"
        else:
            text = f"📅 **Отметить выполнение**\n"
            text += f"📅 {today.strftime('%d.%m.%Y')}\n\n"
            text += "Выберите выполненное дежурство:"
            
            keyboard = []
            for duty in today_duties:
                if not duty.is_completed:
                    button_text = f"✅ {duty.task.name}"
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"complete_duty_{duty.id}"
                    )])
            
            if not keyboard:
                text = f"📅 **Отметить выполнение**\n\n"
                text += f"🎉 Все дежурства на сегодня ({today.strftime('%d.%m.%Y')}) уже выполнены!"
                keyboard = [back_keyboard("duty_schedule").inline_keyboard[0]]
            else:
                keyboard.append(back_keyboard("duty_schedule").inline_keyboard[0])
            
            await query.edit_message_text(
                text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        keyboard = back_keyboard("duty_schedule")
        await query.edit_message_text(
            text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def complete_duty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a specific duty as completed"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        # Extract duty ID from callback data
        duty_id = int(query.data.split("_")[-1])
        
        # Mark as completed
        success = DutyService.mark_task_completed(db, duty_id, query.from_user.id)
        
        if success:
            await query.edit_message_text(
                "✅ Дежурство отмечено как выполненное!",
                reply_markup=back_keyboard("duty_schedule")
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при отметке выполнения",
                reply_markup=back_keyboard("duty_schedule")
            )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def generate_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate duty schedule for current month"""
    query = update.callback_query
    await query.answer()
    
    db = next(get_db())
    try:
        # Get current month
        today = date.today()
        year = today.year
        month = today.month
        
        # Generate schedule
        schedules = DutyService.generate_schedule_for_month(db, year, month)
        
        if schedules:
            await query.edit_message_text(
                f"✅ График дежурств сгенерирован для {today.strftime('%B %Y')}!\n\n"
                f"📊 Создано {sum(len(day_duties) for day_duties in schedules.values())} назначений.",
                reply_markup=back_keyboard("duty_schedule")
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при генерации графика",
                reply_markup=back_keyboard("duty_schedule")
            )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

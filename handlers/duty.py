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


async def duty_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle duty schedule button"""
    query = update.callback_query
    await query.answer()
    
    text = "📅 **График дежурств**\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("📋 Мой график", callback_data="my_duties")],
        [InlineKeyboardButton("📅 График на месяц", callback_data="monthly_schedule")],
        [InlineKeyboardButton("✅ Отметить выполнение", callback_data="mark_completed")],
        [InlineKeyboardButton("🔄 Сгенерировать график", callback_data="generate_schedule")],
    ]
    keyboard.append(back_keyboard("main_menu").inline_keyboard[0])
    
    await query.edit_message_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
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
            
            # Group by week for better display
            current_date = start_date
            week_num = 1
            
            while current_date <= end_date:
                week_end = min(current_date + timedelta(days=6), end_date)
                text += f"**Неделя {week_num}** ({current_date.strftime('%d.%m')} - {week_end.strftime('%d.%m')}):\n"
                
                for i in range(7):
                    check_date = current_date + timedelta(days=i)
                    if check_date > end_date:
                        break
                    
                    date_str = check_date.strftime("%Y-%m-%d")
                    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][check_date.weekday()]
                    
                    if date_str in schedules:
                        text += f"  {day_name} {check_date.strftime('%d.%m')}:\n"
                        for duty in schedules[date_str]:
                            status = "✅" if duty.is_completed else "⏳"
                            user_name = duty.assigned_user.first_name or duty.assigned_user.username or "Неизвестно"
                            text += f"    {status} {duty.task.name} - {user_name}\n"
                
                text += "\n"
                current_date += timedelta(days=7)
                week_num += 1
        
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

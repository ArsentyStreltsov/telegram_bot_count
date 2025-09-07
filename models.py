"""
Database models for household expenses tracking
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, Enum, Date, BigInteger, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from db import Base
import enum

class Currency(enum.Enum):
    """Supported currencies"""
    SEK = "SEK"
    EUR = "EUR"
    RUB = "RUB"

class ExpenseCategory(enum.Enum):
    """Expense categories"""
    FOOD = "Продукты"
    ALCOHOL = "Алкоголь"
    OTHER = "Другое"

class DutyTaskType(str, enum.Enum):
    """Duty task types"""
    COOKING = "cooking"
    CLEANING = "cleaning"
    OTHER = "other"

class User(Base):
    """Telegram user"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    profile_memberships = relationship("ProfileMember", back_populates="user")
    expenses = relationship("Expense", back_populates="payer")
    allocations = relationship("ExpenseAllocation", back_populates="user")

class Profile(Base):
    """Split profile for expense sharing"""
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("ProfileMember", back_populates="profile")
    expenses = relationship("Expense", back_populates="profile")

class ProfileMember(Base):
    """Profile member with group and weight"""
    __tablename__ = "profile_members"
    
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_name = Column(String(50), nullable=False, default="default")
    weight = Column(Float, nullable=False, default=1.0)
    
    # Relationships
    profile = relationship("Profile", back_populates="members")
    user = relationship("User", back_populates="profile_memberships")

class ShoppingItem(Base):
    """Shopping list item"""
    __tablename__ = "shopping_items"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    note = Column(Text, nullable=True)
    is_checked = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    checked_at = Column(DateTime, nullable=True)
    checked_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class TodoItem(Base):
    """Todo list item"""
    __tablename__ = "todo_items"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    note = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class ExchangeRate(Base):
    """Exchange rate history"""
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True)
    from_currency = Column(Enum(Currency), nullable=False)
    to_currency = Column(Enum(Currency), nullable=False)
    rate = Column(Float, nullable=False)
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)

class Expense(Base):
    """Expense record"""
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    exchange_rate = Column(Float, nullable=False)  # Rate used for this expense
    amount_sek = Column(Float, nullable=False)  # Amount in SEK
    category = Column(Enum(ExpenseCategory), nullable=False)
    custom_category_name = Column(String(200), nullable=True)  # For "OTHER" category
    note = Column(Text, nullable=True)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    month = Column(Date, nullable=False)  # YYYY-MM-01 for grouping
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payer = relationship("User", back_populates="expenses")
    profile = relationship("Profile", back_populates="expenses")
    allocations = relationship("ExpenseAllocation", back_populates="expense")

class ExpenseAllocation(Base):
    """How expense is split among users"""
    __tablename__ = "expense_allocations"
    
    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_sek = Column(Float, nullable=False)  # User's share in SEK
    weight_used = Column(Float, nullable=False)  # Weight used for calculation
    
    # Relationships
    expense = relationship("Expense", back_populates="allocations")
    user = relationship("User", back_populates="allocations")

class MonthSnapshot(Base):
    """Monthly balance snapshot"""
    __tablename__ = "month_snapshots"
    
    id = Column(Integer, primary_key=True)
    month = Column(Date, nullable=False)  # YYYY-MM-01
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_paid_sek = Column(Float, nullable=False, default=0.0)
    total_owed_sek = Column(Float, nullable=False, default=0.0)
    net_balance_sek = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")

class DutyTask(Base):
    """Duty task definition"""
    __tablename__ = "duty_tasks"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_weekday_only = Column(Boolean, default=False)  # True if only for weekdays
    is_weekend_only = Column(Boolean, default=False)  # True if only for weekends
    frequency_days = Column(Integer, default=1)  # How often (1=daily, 2=every other day, etc.)
    task_type = Column(Enum(DutyTaskType), default=DutyTaskType.OTHER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    schedules = relationship("DutySchedule", back_populates="task")
    
    __table_args__ = (
        Index("ix_duty_tasks_type", "task_type"),
    )

class DutySchedule(Base):
    """Duty schedule for specific date and task"""
    __tablename__ = "duty_schedules"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("duty_tasks.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("DutyTask", back_populates="schedules")
    assigned_user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint("task_id", "date", name="uq_task_per_date"),
        Index("ix_user_date", "assigned_user_id", "date"),
        Index("ix_date", "date"),
    )

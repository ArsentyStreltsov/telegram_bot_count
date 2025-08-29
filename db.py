"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Create database directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Database URL
DATABASE_URL = "sqlite:///data/household_expenses.db"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with all tables"""
    from models import (
        User, Profile, ProfileMember, ShoppingItem, Expense, 
        ExpenseAllocation, ExchangeRate, MonthSnapshot
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully")

def reset_db():
    """Reset database (drop all tables and recreate)"""
    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Database reset successfully")

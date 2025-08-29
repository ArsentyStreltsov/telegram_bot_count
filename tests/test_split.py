"""
Tests for split service
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base
from models import User, Profile, ProfileMember, Expense, Currency, ExpenseCategory
from services.split import SplitService

# Test database
TEST_DATABASE_URL = "sqlite:///test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_users(db_session):
    """Create sample users"""
    users = []
    for i in range(4):
        user = User(
            telegram_id=1000 + i,
            username=f"user{i}",
            first_name=f"User{i}"
        )
        db_session.add(user)
        users.append(user)
    
    db_session.commit()
    return users

@pytest.fixture
def sample_profile(db_session, sample_users):
    """Create sample profile with members"""
    profile = Profile(name="Test Profile", is_default=True)
    db_session.add(profile)
    db_session.flush()
    
    # Add members with different groups and weights
    members = [
        ProfileMember(profile_id=profile.id, user_id=sample_users[0].id, group_name="Group A", weight=1.0),
        ProfileMember(profile_id=profile.id, user_id=sample_users[1].id, group_name="Group A", weight=1.0),
        ProfileMember(profile_id=profile.id, user_id=sample_users[2].id, group_name="Group B", weight=2.0),
        ProfileMember(profile_id=profile.id, user_id=sample_users[3].id, group_name="Group B", weight=2.0),
    ]
    
    for member in members:
        db_session.add(member)
    
    db_session.commit()
    return profile

def test_calculate_expense_split(db_session, sample_profile, sample_users):
    """Test expense split calculation"""
    # Create expense
    expense = Expense(
        amount=100.0,
        currency=Currency.SEK,
        exchange_rate=1.0,
        amount_sek=100.0,
        category=ExpenseCategory.OTHER,
        payer_id=sample_users[0].id,
        profile_id=sample_profile.id,
        month=datetime.now().replace(day=1).date()
    )
    db_session.add(expense)
    db_session.flush()
    
    # Calculate splits
    allocations = SplitService.calculate_expense_split(db_session, expense, sample_profile)
    
    # Verify allocations
    assert len(allocations) == 4
    
    # Group A should get 16.67 SEK each (2/6 of 100, split equally between 2 members)
    group_a_allocations = [a for a in allocations if a.user_id in [sample_users[0].id, sample_users[1].id]]
    for allocation in group_a_allocations:
        assert abs(allocation.amount_sek - 16.67) < 0.01
        assert allocation.weight_used == 1.0
    
    # Group B should get 33.33 SEK each (4/6 of 100, split equally between 2 members)
    group_b_allocations = [a for a in allocations if a.user_id in [sample_users[2].id, sample_users[3].id]]
    for allocation in group_b_allocations:
        assert abs(allocation.amount_sek - 33.33) < 0.01
        assert allocation.weight_used == 2.0

def test_calculate_user_balances(db_session, sample_profile, sample_users):
    """Test user balance calculation"""
    # Create expenses
    expenses = [
        Expense(
            amount=100.0,
            currency=Currency.SEK,
            exchange_rate=1.0,
            amount_sek=100.0,
            category=ExpenseCategory.OTHER,
            payer_id=sample_users[0].id,
            profile_id=sample_profile.id,
            month=datetime.now().replace(day=1).date()
        ),
        Expense(
            amount=50.0,
            currency=Currency.SEK,
            exchange_rate=1.0,
            amount_sek=50.0,
            category=ExpenseCategory.OTHER,
            payer_id=sample_users[1].id,
            profile_id=sample_profile.id,
            month=datetime.now().replace(day=1).date()
        )
    ]
    
    for expense in expenses:
        db_session.add(expense)
        db_session.flush()
        
        # Create allocations for each expense
        allocations = SplitService.calculate_expense_split(db_session, expense, sample_profile)
        for allocation in allocations:
            db_session.add(allocation)
    
    db_session.commit()
    
    # Calculate balances
    balances = SplitService.calculate_user_balances(db_session)
    
    # Verify balances
    assert len(balances) == 4
    
    # User 0 paid 100, owes 25.0 (16.67 from first expense + 8.33 from second)
    user0_balance = balances[sample_users[0].id]
    assert user0_balance['paid'] == 100.0
    assert abs(user0_balance['owed'] - 25.0) < 0.01
    assert abs(user0_balance['net'] - (-75.0)) < 0.01  # Owe money
    
    # User 1 paid 50, owes 25.0
    user1_balance = balances[sample_users[1].id]
    assert user1_balance['paid'] == 50.0
    assert abs(user1_balance['owed'] - 25.0) < 0.01
    assert abs(user1_balance['net'] - (-25.0)) < 0.01  # Owe money

def test_calculate_settlement_plan(db_session, sample_profile, sample_users):
    """Test settlement plan calculation"""
    # Create mock balances
    balances = {
        sample_users[0].id: {'paid': 100.0, 'owed': 25.0, 'net': -75.0},  # Owe 75
        sample_users[1].id: {'paid': 50.0, 'owed': 25.0, 'net': -25.0},   # Owe 25
        sample_users[2].id: {'paid': 0.0, 'owed': 50.0, 'net': 50.0},     # Are owed 50
        sample_users[3].id: {'paid': 0.0, 'owed': 50.0, 'net': 50.0},     # Are owed 50
    }
    
    # Calculate settlements
    settlements = SplitService.calculate_settlement_plan(db_session, balances)
    
    # Verify settlements (greedy algorithm may create more transactions)
    assert len(settlements) >= 2
    
    # Should have settlements from debtors to creditors
    debtor_ids = [s['from_user_id'] for s in settlements]
    creditor_ids = [s['to_user_id'] for s in settlements]
    
    assert sample_users[0].id in debtor_ids  # Owe 75
    assert sample_users[1].id in debtor_ids  # Owe 25
    assert sample_users[2].id in creditor_ids  # Are owed 50
    assert sample_users[3].id in creditor_ids  # Are owed 50

def test_empty_profile_split(db_session, sample_users):
    """Test split calculation with empty profile"""
    profile = Profile(name="Empty Profile")
    db_session.add(profile)
    db_session.flush()
    
    expense = Expense(
        amount=100.0,
        currency=Currency.SEK,
        exchange_rate=1.0,
        amount_sek=100.0,
        category=ExpenseCategory.OTHER,
        payer_id=sample_users[0].id,
        profile_id=profile.id,
        month=datetime.now().replace(day=1).date()
    )
    db_session.add(expense)
    db_session.flush()
    
    # Should raise error for empty profile
    with pytest.raises(ValueError, match="has no members"):
        SplitService.calculate_expense_split(db_session, expense, profile)

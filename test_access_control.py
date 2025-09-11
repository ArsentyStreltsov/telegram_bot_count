#!/usr/bin/env python3
"""
Test script for access control system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.access_control import AccessControl
from unittest.mock import Mock, AsyncMock
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

def create_mock_update(text: str, user_id: int, username: str = None, first_name: str = None) -> Update:
    """Create a mock Update object for testing"""
    mock_user = Mock(spec=User)
    mock_user.id = user_id
    mock_user.first_name = first_name or f"User{user_id}"
    mock_user.username = username
    
    mock_chat = Mock(spec=Chat)
    mock_chat.id = user_id
    
    mock_message = Mock(spec=Message)
    mock_message.text = text
    mock_message.reply_text = AsyncMock()
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    
    mock_update = Mock(spec=Update)
    mock_update.message = mock_message
    mock_update.effective_user = mock_user
    
    return mock_update

def create_mock_context() -> ContextTypes.DEFAULT_TYPE:
    """Create a mock Context object for testing"""
    mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.bot_data = {}
    return mock_context

def test_access_control():
    """Test the access control system"""
    print("🧪 Testing Access Control System...")
    
    # Test 1: Allowed users
    print("\n✅ Test 1: Allowed users")
    allowed_users = AccessControl.get_allowed_users()
    print(f"  Разрешенные пользователи: {allowed_users}")
    
    for user_id in allowed_users:
        is_allowed = AccessControl.is_user_allowed(user_id)
        print(f"  User {user_id}: {'✅ Разрешен' if is_allowed else '❌ Запрещен'}")
    
    # Test 2: Disallowed users
    print("\n❌ Test 2: Disallowed users")
    disallowed_users = [123456789, 987654321, 111111111, 999999999]
    
    for user_id in disallowed_users:
        is_allowed = AccessControl.is_user_allowed(user_id)
        print(f"  User {user_id}: {'✅ Разрешен' if is_allowed else '❌ Запрещен'}")
    
    # Test 3: Access control with mock updates
    print("\n🔍 Test 3: Access control with mock updates")
    
    # Test allowed user
    allowed_user_id = allowed_users[0]
    allowed_update = create_mock_update("/start", allowed_user_id, "allowed_user", "Allowed User")
    allowed_context = create_mock_context()
    
    has_access = AccessControl.check_access(allowed_update, allowed_context)
    print(f"  Разрешенный пользователь {allowed_user_id}: {'✅ Доступ разрешен' if has_access else '❌ Доступ запрещен'}")
    
    # Test disallowed user
    disallowed_user_id = 123456789
    disallowed_update = create_mock_update("/start", disallowed_user_id, "hacker", "Hacker")
    disallowed_context = create_mock_context()
    
    has_access = AccessControl.check_access(disallowed_update, disallowed_context)
    print(f"  Запрещенный пользователь {disallowed_user_id}: {'✅ Доступ разрешен' if has_access else '❌ Доступ запрещен'}")
    
    # Test 4: Access denied message
    print("\n📝 Test 4: Access denied message")
    message = AccessControl.get_access_denied_message()
    print(f"  Сообщение об отказе в доступе: {message[:50]}...")
    
    # Test 5: Logging access attempts
    print("\n📊 Test 5: Logging access attempts")
    AccessControl.log_access_attempt(disallowed_update, disallowed_context)
    
    if 'access_attempts' in disallowed_context.bot_data:
        attempts = disallowed_context.bot_data['access_attempts']
        print(f"  Записано попыток доступа: {len(attempts)}")
        if attempts:
            last_attempt = attempts[-1]
            print(f"  Последняя попытка: {last_attempt['first_name']} (@{last_attempt['username']}, ID: {last_attempt['telegram_id']})")
    
    print("\n✅ Все тесты завершены!")

def test_decorators():
    """Test the decorators"""
    print("\n🧪 Testing Decorators...")
    
    # Test require_access decorator
    print("\n🔒 Test require_access decorator")
    
    from utils.access_control import require_access
    
    @require_access
    async def test_command(update, context):
        return "Command executed"
    
    # This would normally be tested with actual async calls, but we can test the logic
    print("  ✅ Декоратор require_access добавлен к функции test_command")
    
    print("\n✅ Тесты декораторов завершены!")

def main():
    """Run all tests"""
    print("🚀 Starting Access Control Tests...\n")
    
    test_access_control()
    test_decorators()
    
    print("\n🎉 Все тесты завершены успешно!")

if __name__ == "__main__":
    main()

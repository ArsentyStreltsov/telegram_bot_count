"""
Setup profiles and family members after all users have joined the bot
"""
from db import get_db, init_db
from models import User, Profile, ProfileMember
from sqlalchemy.orm import Session

def list_users():
    """List all registered users"""
    db = next(get_db())
    
    try:
        users = db.query(User).order_by(User.created_at).all()
        
        if not users:
            print("❌ Нет зарегистрированных пользователей")
            print("Попросите всех участников семьи присоединиться к боту с помощью /start")
            return []
        
        print("👥 Зарегистрированные пользователи:")
        print("-" * 50)
        
        for i, user in enumerate(users, 1):
            name = user.first_name or user.username or f"User {user.telegram_id}"
            print(f"{i}. {name} (@{user.username or 'no username'}) - ID: {user.id}")
        
        print("-" * 50)
        return users
        
    except Exception as e:
        print(f"❌ Ошибка при получении пользователей: {e}")
        return []
    finally:
        db.close()

def setup_home_profile():
    """Setup Home profile with family members"""
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        if not users:
            print("❌ Нет пользователей для настройки профиля")
            return
        
        # Get Home profile
        home_profile = db.query(Profile).filter(Profile.name == "Home").first()
        if not home_profile:
            print("❌ Профиль 'Home' не найден")
            return
        
        print("\n🏠 Настройка профиля 'Home' (Домашние расходы)")
        print("Введите номера пользователей для каждой группы:")
        
        # Clear existing members
        db.query(ProfileMember).filter(ProfileMember.profile_id == home_profile.id).delete()
        
        # Group A (Arsenty, Dasha)
        print("\n👥 Группа A (равные доли):")
        group_a_input = input("Введите номера пользователей через запятую (например: 1,2): ").strip()
        group_a_users = []
        if group_a_input:
            try:
                indices = [int(x.strip()) - 1 for x in group_a_input.split(',')]
                group_a_users = [users[i] for i in indices if 0 <= i < len(users)]
            except (ValueError, IndexError):
                print("❌ Неверный формат ввода")
                return
        
        # Group B (Mom, Dad)
        print("\n👥 Группа B (равные доли):")
        group_b_input = input("Введите номера пользователей через запятую (например: 3,4): ").strip()
        group_b_users = []
        if group_b_input:
            try:
                indices = [int(x.strip()) - 1 for x in group_b_input.split(',')]
                group_b_users = [users[i] for i in indices if 0 <= i < len(users)]
            except (ValueError, IndexError):
                print("❌ Неверный формат ввода")
                return
        
        # Add members to profile
        for user in group_a_users:
            member = ProfileMember(
                profile_id=home_profile.id,
                user_id=user.id,
                group_name="Group A",
                weight=1.0
            )
            db.add(member)
            print(f"✅ Добавлен в Group A: {user.first_name or user.username}")
        
        for user in group_b_users:
            member = ProfileMember(
                profile_id=home_profile.id,
                user_id=user.id,
                group_name="Group B",
                weight=1.0
            )
            db.add(member)
            print(f"✅ Добавлен в Group B: {user.first_name or user.username}")
        
        db.commit()
        print(f"\n✅ Профиль 'Home' настроен успешно!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при настройке профиля: {e}")
    finally:
        db.close()

def setup_trip_profile():
    """Setup Trip profile with all family members"""
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        if not users:
            print("❌ Нет пользователей для настройки профиля")
            return
        
        # Get Trip profile
        trip_profile = db.query(Profile).filter(Profile.name == "Trip").first()
        if not trip_profile:
            print("❌ Профиль 'Trip' не найден")
            return
        
        print("\n✈️ Настройка профиля 'Trip' (Расходы на поездки)")
        
        # Clear existing members
        db.query(ProfileMember).filter(ProfileMember.profile_id == trip_profile.id).delete()
        
        # Add all users with equal weights
        for user in users:
            member = ProfileMember(
                profile_id=trip_profile.id,
                user_id=user.id,
                group_name="default",
                weight=1.0
            )
            db.add(member)
            print(f"✅ Добавлен: {user.first_name or user.username}")
        
        db.commit()
        print(f"\n✅ Профиль 'Trip' настроен успешно!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при настройке профиля: {e}")
    finally:
        db.close()

def main():
    """Main setup function"""
    print("🔧 Настройка профилей для семейных расходов")
    print("=" * 50)
    
    # List users
    users = list_users()
    if not users:
        return
    
    # Setup profiles
    setup_home_profile()
    setup_trip_profile()
    
    print("\n🎉 Настройка завершена!")
    print("Теперь можно использовать бота для отслеживания расходов.")

if __name__ == "__main__":
    main()

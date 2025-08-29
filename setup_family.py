"""
Quick setup script for family members with known IDs
"""
from db import get_db, init_db
from models import Profile, ProfileMember, User

def setup_family():
    """Setup family profiles with known user IDs"""
    db = next(get_db())
    
    try:
        # Get all users
        users = db.query(User).all()
        print("👥 Найденные пользователи:")
        for i, user in enumerate(users, 1):
            name = user.first_name or user.username or f"User {user.telegram_id}"
            print(f"{i}. {name} (@{user.username or 'no username'}) - ID: {user.id}, Telegram ID: {user.telegram_id}")
        
        # Map users by their names/telegram IDs
        user_map = {}
        for user in users:
            if user.username == "the_lodka":
                user_map["arsenty"] = user
            elif user.username == "katrine_streltsova":
                user_map["mom"] = user
            elif user.first_name == "Dmitry" and user.last_name == "Streltsov":
                user_map["dad"] = user
            elif user.username == "dashok_she":
                user_map["dasha"] = user
            elif user.username == "l_tyti":
                user_map["misha"] = user
        
        print(f"\n🗺️ Сопоставление пользователей:")
        for key, user in user_map.items():
            print(f"  {key}: {user.first_name} (@{user.username})")
        
        # Get profiles
        home_profile = db.query(Profile).filter(Profile.name == "Home").first()
        trip_profile = db.query(Profile).filter(Profile.name == "Trip").first()
        
        if not home_profile or not trip_profile:
            print("❌ Профили не найдены")
            return
        
        # Clear existing members
        db.query(ProfileMember).filter(ProfileMember.profile_id == home_profile.id).delete()
        db.query(ProfileMember).filter(ProfileMember.profile_id == trip_profile.id).delete()
        
        # Setup Home profile: Group A (Arsenty, Dasha), Group B (Mom, Dad)
        print(f"\n🏠 Настройка профиля 'Home':")
        print("   Примечание: Теперь разделение зависит от категории расхода")
        
        # Group A: Arsenty, Dasha
        if "arsenty" in user_map and "dasha" in user_map:
            for user in [user_map["arsenty"], user_map["dasha"]]:
                member = ProfileMember(
                    profile_id=home_profile.id,
                    user_id=user.id,
                    group_name="Group A",
                    weight=1.0
                )
                db.add(member)
                print(f"  ✅ Добавлен в Group A: {user.first_name} (@{user.username})")
        
        # Group B: Mom, Dad
        if "mom" in user_map and "dad" in user_map:
            for user in [user_map["mom"], user_map["dad"]]:
                member = ProfileMember(
                    profile_id=home_profile.id,
                    user_id=user.id,
                    group_name="Group B",
                    weight=1.0
                )
                db.add(member)
                print(f"  ✅ Добавлен в Group B: {user.first_name} (@{user.username})")
        
        # Setup Trip profile: all family members
        print(f"\n✈️ Настройка профиля 'Trip':")
        
        for key, user in user_map.items():
            member = ProfileMember(
                profile_id=trip_profile.id,
                user_id=user.id,
                group_name="default",
                weight=1.0
            )
            db.add(member)
            print(f"  ✅ Добавлен: {user.first_name} (@{user.username})")
        
        db.commit()
        print(f"\n🎉 Настройка завершена успешно!")
        print(f"Теперь можно использовать бота для отслеживания расходов.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при настройке: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    setup_family()

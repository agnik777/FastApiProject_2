# app/scripts.py
import asyncio
from sqlalchemy import select
from models import User, Role, Right
from auth import hash_password
from database import AsyncSessionLocal
from services import add_item
from config import Config


async def create_initial_roles(session):
    """Создает базовые роли и права"""

    # --- Права ---
    # Право на чтение своих объявлений
    right_read_own_advertisement = Right(
        read=True, write=False, only_own=True, model="Catalog"
    )
    # Право на чтение и запись своих объявлений
    right_read_write_own_advertisement = Right(
        read=True, write=True, only_own=True, model="Catalog"
    )
    # Право на чтение любых объявлений
    right_read_any_advertisement = Right(
        read=True, write=False, only_own=False, model="Catalog"
    )
    # Право на любые действия с объявлений (админское)
    right_full_advertisement = Right(
        read=True, write=True, only_own=False, model="Catalog"
    )
    # Право на чтение и запись своих данных
    right_read_write_own_user = Right(
        read=True, write=True, only_own=True, model="User"
    )
    # Право на чтение данных любых пользователей
    right_read_any_user = Right(
        read=True, write=False, only_own=False, model="User"
    )
    # Право на любые действия с данными пользователей (админское)
    right_full_user = Right(
        read=True, write=True, only_own=False, model="User"
    )

    session.add_all([right_read_own_advertisement,
                     right_read_write_own_advertisement,
                     right_read_any_advertisement,
                     right_full_advertisement,
                     right_read_write_own_user,
                     right_read_any_user,
                     right_full_user])
    await session.flush()  # Чтобы получить id созданных прав

    # --- Роли ---
    role_user = Role(name="user")
    role_user.rights = [right_read_any_advertisement,
                        right_read_write_own_advertisement,
                        right_read_any_user,
                        right_read_write_own_user]

    role_admin = Role(name="admin")
    role_admin.rights = [right_full_advertisement,
                         right_full_user]

    session.add_all([role_user, role_admin])
    await session.flush()
    return role_user, role_admin


async def create_admin(session, role_admin):
    """Создает администратора и назначает ему роль admin"""
    hashed_pw = hash_password(Config.ADMIN_PASSWORD)
    admin_user = User(name=Config.CATALOG_ADMIN, password=hashed_pw, roles=[role_admin])
    admin_user = await add_item(session, admin_user)
    print(f"Admin user created with id: {admin_user.id}")

async def create_test_user(session, role_user):
    """Создает тестового пользователя и назначает ему роль user"""
    hashed_pw = hash_password("1234")
    test_user = User(name="test_user", password=hashed_pw, roles=[role_user])
    test_user = await add_item(session, test_user)
    print(f"Test user created with id: {test_user.id}")


async def main():
    async with AsyncSessionLocal() as session:
        # Проверим, есть ли уже роли, чтобы не создавать дубликаты
        result = await session.execute(select(Role))
        existing_roles = result.scalars().all()
        if not existing_roles:
            print("Creating initial roles...")
            role_user, role_admin = await create_initial_roles(session)
            await create_admin(session, role_admin)
            await create_test_user(session, role_user)
            await session.commit()
            print("Initial data created.")
        else:
            print("Roles already exist.")

if __name__ == "__main__":
    asyncio.run(main())

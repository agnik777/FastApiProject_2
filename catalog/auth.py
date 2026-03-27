# app/auth.py
import bcrypt
import uuid
import datetime
from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import (Token, User, Role, Right,
                    user_role_relation, role_right_relation)
from dependencies import get_db_session
from config import config
from sqlalchemy.sql import func


def hash_password(password: str) -> str:
    # Генерируем соль и хэшируем пароль
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def check_password(password: str, hashed_password: str) -> bool:
    # Сравниваем введенный пароль с хэшем
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

async def check_token(
    token: uuid.UUID = Header(..., alias="x-token"),
    db_session: AsyncSession = Depends(get_db_session)
) -> Token:
    # Вычисляем дату, раньше которой токен считается просроченным
    expire_threshold = func.now() - datetime.timedelta(seconds=config.TOKEN_TTL)

    query = select(Token).where(
        Token.token == token,
        Token.creation_time >= expire_threshold
    )
    token_obj = await db_session.scalar(query)

    if token_obj is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token_obj


async def check_object_access(
    user: User,
    orm_object,
    db_session: AsyncSession,
    need_read: bool = False,
    need_write: bool = False,
) -> bool:
    """
    Проверяет, есть ли у пользователя права на объект.
    """
    # 1. Определяем имя класса модели, к которой мы обращаемся
    model_class = orm_object if isinstance(orm_object, type) \
        else orm_object.__class__
    model_name = model_class.__name__

    # 2. Формируем базовые условия для WHERE
    where_args = [
        User.id == user.id,
        Right.model == model_name
    ]
    if need_read:
        where_args.append(Right.read == True)
    if need_write:
        where_args.append(Right.write == True)

    # 3. Особая логика для проверки "только свое" или "чужое".
    # Если объект - это экземпляр (не класс) и у него есть поле user_id
    if not isinstance(orm_object, type) and hasattr(orm_object, 'user_id'):
        # Если объект не принадлежит текущему пользователю
        if orm_object.user_id != user.id:
            # То нам нужны права, у которых only_own == False
            where_args.append(Right.only_own == False)
        # Если объект свой, то нас устраивают права как с only_own=True,
        # так и с only_own=False. Поэтому дополнительное условие не добавляем.

    # 4. Формируем запрос на подсчет
    query = (
        select(func.count())
        .select_from(User)
        .join(user_role_relation, User.id == user_role_relation.c.user_id)
        .join(Role, user_role_relation.c.role_id == Role.id)
        .join(role_right_relation, Role.id == role_right_relation.c.role_id)
        .join(Right, role_right_relation.c.right_id == Right.id)
        .where(*where_args)
    )

    # 5. Выполняем запрос
    result = await db_session.execute(query)
    count = result.scalar()

    # 6. Если нашли хотя бы одно право - доступ разрешен
    return count > 0

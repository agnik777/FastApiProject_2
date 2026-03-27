# catalog/database.py
from sqlalchemy.ext.asyncio import (create_async_engine, async_sessionmaker,
                                    AsyncSession)
from config import config
from sqlalchemy.orm import declarative_base


# Создаём асинхронный движок
engine = create_async_engine(config.DATABASE_URL, echo=True)

# Создаём фабрику сессий. expire_on_commit=False -
# чтобы можно было работать с объектами после коммита.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для наших моделей
Base = declarative_base()

# catalog/dependencies.py
from database import AsyncSessionLocal


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

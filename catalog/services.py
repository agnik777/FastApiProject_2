# catalog/services.py
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime


async def add_item(
    session: AsyncSession,
    new_item
) -> models.User:
    session.add(new_item)
    try:
        await session.commit()
        await session.refresh(new_item)
        return new_item
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item with such data already exists."
        )

async def get_item(
    session: AsyncSession,
    orm_model: type[models.Catalog, models.User],
    item_id: int
) -> (models.Catalog, models.User):
    """
    Получает запись по ID или выбрасывает 404.
    """
    stmt = select(orm_model).where(orm_model.id == item_id)
    item = await session.scalar(stmt)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data with id {item_id} not found"
        )
    return item

async def update_item(
    session: AsyncSession,
    orm_model: type[models.Catalog],
    item_id: int,
    update_data: schemas.UpdateAdvertisementRequest
) -> models.Catalog:
    item = await get_item(session, orm_model, item_id)
    # Преобразуем update_data в словарь, исключая поля со значением None
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item

async def delete_item(
    session: AsyncSession,
    orm_model: type[models.Catalog, models.User],
    item_id: int
) -> None:
    """
    Удаляет запись.
    """
    item = await get_item(session, orm_model, item_id)
    await session.delete(item)
    await session.commit()

def get_date_obj(date_name: str, search_dict: dict) -> datetime:
    # Ожидается, что date_name — строка в ISO формате
    try:
        date_obj = datetime.fromisoformat(search_dict[date_name])
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="Некорректный формат date_creation. "
                                   "Ожидается ISO формат.")
    return date_obj

def get_advertisements_query(orm_model, search_data):
    search_dict = search_data.model_dump(exclude_none=True)
    # Преобразуем update_data в словарь, исключая поля со значением None
    if len(search_dict) < 2:
        raise HTTPException(status_code=400,
                            detail="Должен быть указан хотя бы один параметр.")
    # Создаем список условий для фильтрации
    filters = []
    # Обработка строковых полей с вхождением
    if 'title' in search_dict:
        filters.append(orm_model.title.ilike(f"%{search_dict['title']}%"))
    if 'description' in search_dict:
        filters.append(orm_model.description.ilike(
            f"%{search_dict['description']}%"))
    if 'max_price' in search_dict:
        filters.append(orm_model.price <= search_dict['max_price'])
    if 'min_price' in search_dict:
        filters.append(orm_model.price >= search_dict['min_price'])
    # Обработка даты
    if 'after_date_creation' in search_dict:
        date_obj = get_date_obj('after_date_creation', search_dict)
        filters.append(orm_model.date_creation >= date_obj)
    if 'before_date_creation' in search_dict:
        date_obj = get_date_obj('before_date_creation', search_dict)
        filters.append(orm_model.date_creation <= date_obj)
    query = (
        select(orm_model)
        .distinct(orm_model.id)
        .options(selectinload(orm_model.user))
        .where(and_(*filters))
        .limit(search_data.limit)
    )
    return query

async def search_item(
    session: AsyncSession,
    orm_model: type[models.Catalog],
    search_data: schemas.SearchAdvertisementRequest
):
    stmt = get_advertisements_query(orm_model, search_data)
    result = await session.execute(stmt)
    items = result.scalars().all()
    # Если товаров не найдено, возвращаем 404
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No listings found with these settings"
        )
    return items

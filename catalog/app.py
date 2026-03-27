# catalog/app.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from lifespan import lifespan
import models
from models import User, Token, Catalog, Role
from auth import check_password, hash_password, check_token, check_object_access
import schemas
from dependencies import get_db_session
from services import add_item, get_item, update_item, delete_item, search_item


app = FastAPI(
    title="Catalog App",
    description="This is a product catalog application API",
    version="0.0.1",
    lifespan=lifespan
)


@app.post("/login", response_model=schemas.LoginResponse)
async def login(
    login_data: schemas.LoginRequest,
    db_session: AsyncSession = Depends(get_db_session)
):
    # 1. Ищем пользователя по имени
    query = select(User).where(User.name == login_data.username)
    user = await db_session.scalar(query)
    # 2. Если пользователь не найден
    if user is None:
        raise HTTPException(status_code=401,
                            detail="Incorrect username or password")
    # 3. Проверяем пароль
    if not check_password(login_data.password, user.password):
        raise HTTPException(status_code=401,
                            detail="Incorrect username or password")
    # 4. Если всё ок, создаем токен
    new_token = Token(user=user)
    db_session.add(new_token)
    await db_session.commit()
    await db_session.refresh(new_token)
    return new_token  # FastAPI автоматически преобразует в схему LoginResponse


@app.post("/user", response_model=schemas.IdResponse)
async def create_user(
    user_data: schemas.CreateUserRequest,
    db_session: AsyncSession = Depends(get_db_session)
):
    # Хэшируем пароль
    hashed_password = hash_password(user_data.password)
    # Создаем объект пользователя
    new_user = User(name=user_data.username, password=hashed_password)
    # --- Назначение роли 'user' по умолчанию ---
    role_user = await db_session.scalar(select(Role).where(Role.name == "user"))
    if role_user is None:
        raise HTTPException(status_code=500,
                            detail="Default role 'user' not found in database")
    new_user.roles = [role_user]
    new_user = await add_item(db_session, new_user)
    return {"id": new_user.id}


@app.get("/user/{user_id}",
        response_model=schemas.UserResponse,
        summary="Получить польэователя по ID")
async def get_user(
        user_id: int,
        db_session: AsyncSession = Depends(get_db_session)
):
    user = await get_item(db_session, models.User, user_id)
    return user


@app.patch("/user/{user_id}",
           response_model=schemas.UserResponse,
           summary="Обновить данные пользователя")
async def update_user(
    user_id: int,
    update_data: schemas.UpdateUserRequest,
    db_session: AsyncSession = Depends(get_db_session),
    token_obj: Token = Depends(check_token)
):
    user = await get_item(db_session, models.User, user_id)
    # --- Проверка прав доступа ---
    has_access = await check_object_access(
        user=token_obj.user,
        orm_object=user,
        db_session=db_session,
        need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    if update_data.username != None:
        user.name = update_data.username
    if update_data.password != None:
        hashed_password = hash_password(update_data.password)
        user.password = hashed_password
    user = await add_item(db_session, user)
    return user


@app.delete("/user/{user_id}",
            response_model=schemas.OKResponse,
            summary="Удалить польэователя")
async def delete_user(
    item_id: int,
    db_session: AsyncSession = Depends(get_db_session),
    token_obj: Token = Depends(check_token)
):
    user_to_delete = await get_item(db_session, models.User, item_id)
    # --- Проверка прав доступа ---
    has_access = await check_object_access(
        user=token_obj.user,
        orm_object=user_to_delete,
        db_session=db_session,
        need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    await delete_item(db_session, models.User, item_id)
    return schemas.OKResponse()


@app.post("/advertisement")
async def create_advertisement(
    advertisement_data: schemas.CreateAdvertisementRequest,
    token_obj: Token = Depends(check_token),  # Вот она, наша защита!
    db_session: AsyncSession = Depends(get_db_session)
):
    # Создаем задачу, привязывая её к пользователю из токена
    new_advertisement = Catalog(
        title=advertisement_data.title,
        description=advertisement_data.description,
        price=advertisement_data.price,
        user_id=token_obj.user_id
    )
    db_session.add(new_advertisement)
    await db_session.commit()
    await db_session.refresh(new_advertisement)
    # Для простоты вернем ID созданной задачи
    return {"id": new_advertisement.id}


@app.get("/advertisement/{advertisement_id}",
        response_model=schemas.AdvertisementResponse,
        summary="Получить описание товара по ID")
async def get_advertisement(
        advertisement_id: int,
        db_session: AsyncSession = Depends(get_db_session)
):
    advertisement = await get_item(db_session, models.Catalog, advertisement_id)
    # Преобразуем ORM-модель в словарь и затем в Pydantic-схему
    return schemas.AdvertisementResponse(**advertisement.to_dict())


@app.patch("/advertisement/{advertisement_id}",
           response_model=schemas.AdvertisementResponse,
           summary="Обновить описание товара")
async def update_advertisement(
    advertisement_id: int,
    update_data: schemas.UpdateAdvertisementRequest,
    db_session: AsyncSession = Depends(get_db_session),
    token_obj: Token = Depends(check_token)
):
    advertisement = await get_item(db_session, models.Catalog, advertisement_id)
    # --- Проверка прав доступа ---
    has_access = await check_object_access(
        user=token_obj.user,
        orm_object=advertisement,
        db_session=db_session,
        need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    advertisement = await update_item(db_session, models.Catalog,
                                              advertisement_id, update_data)
    return schemas.AdvertisementResponse(**advertisement.to_dict())


@app.delete("/advertisement/{advertisement_id}",
            response_model=schemas.OKResponse,
            summary="Удалить запись о товаре")
async def delete_advertisement(
    item_id: int,
    db_session: AsyncSession = Depends(get_db_session),
    token_obj: Token = Depends(check_token)
):
    advertisement = await get_item(db_session, models.Catalog, item_id)
    # --- Проверка прав доступа ---
    has_access = await check_object_access(
        user=token_obj.user,
        orm_object=advertisement,
        db_session=db_session,
        need_write=True
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    await delete_item(db_session, models.Catalog, item_id)
    return schemas.OKResponse()


@app.get("/advertisement",
         response_model=schemas.SearchAdvertisementResponse,
         summary="Получить описание товара по параметрам")
async def search_advertisement(
        db_session: AsyncSession = Depends(get_db_session),
        search_data: schemas.SearchAdvertisementRequest = Depends()
):
    items = await search_item(db_session, models.Catalog, search_data)
    advertisements = [item.to_dict() for item in items]
    return schemas.SearchAdvertisementResponse(items=advertisements)

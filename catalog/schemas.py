# catalog/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    token: UUID

    class Config:
        # Это позволяет работать с ORM объектами
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str
    password: str


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class IdResponse(BaseModel):
    id: int


class UserResponse(BaseModel):
    id: int
    name: str


class CreateAdvertisementRequest(BaseModel):
    title: str
    description: str
    price: int


class CreateAdvertisementResponse(BaseModel):
    id: int


class AdvertisementResponse(BaseModel):
    id: int
    title: str
    description: str
    price: int
    user_id: int
    date_creation: str


class UpdateAdvertisementRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None


class OKResponse(BaseModel):
    status: str = "ok"


class SearchAdvertisementRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    after_date_creation: Optional[str] = None
    before_date_creation: Optional[str] = None
    limit: int = 1


class SearchAdvertisementResponse(BaseModel):
    items: List[AdvertisementResponse]

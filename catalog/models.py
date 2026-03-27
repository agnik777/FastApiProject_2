# catalog/models.py
import uuid
import datetime
from sqlalchemy import (Table, Column, Integer, String, DateTime, Boolean,
                        ForeignKey, Uuid)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base
from typing import Literal, List


# Создаем тип, который может принимать только строки из списка
ModelName = Literal["User", "Catalog", "Role", "Right"]


# Связь пользователя и роли (многие-ко-многим)
user_role_relation = Table(
    "user_role_relation",
    Base.metadata,
    Column("user_id", ForeignKey("advertisement_user.id"), primary_key=True),  # Используем primary_key для составного ключа
    Column("role_id", ForeignKey("role.id"), primary_key=True)
)


# Связь роли и права (многие-ко-многим)
role_right_relation = Table(
    "role_right_relation",
    Base.metadata,
    Column("role_id", ForeignKey("role.id"), primary_key=True),
    Column("right_id", ForeignKey("right.id"), primary_key=True)
)


class Right(Base):
    __tablename__ = "right"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Может ли писать (создавать/изменять/удалять)
    write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Может ли читать
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Только свои записи или любые
    only_own: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Имя модели. Будет храниться строго одно из значений ModelName
    model: Mapped[ModelName] = mapped_column(String(50), nullable=False)


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Связь с правами через промежуточную таблицу
    rights: Mapped[List[Right]] = relationship(
        secondary=role_right_relation,  # Указываем таблицу связи
        lazy="joined"
    )


class User(Base):
    __tablename__ = "advertisement_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True,
                                      nullable=False)
    password: Mapped[str] = mapped_column(String(70), nullable=False)

    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="user",  # Обратная связь в модели Token
        cascade="all, delete-orphan",  # Если удалим юзера, его токены удалятся
        lazy="joined"  # Как подгружать данные (сразу при загрузке юзера)
    )

    roles: Mapped[List[Role]] = relationship(
        secondary=user_role_relation,  # Связь через нашу таблицу
        lazy="joined"
    )

    @property
    def to_dict(self):
        return {"id": self.id, "name": str(self.name)}


class Token(Base):
    __tablename__ = "token"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Сам токен. Используем тип UUID и генерируем случайное значение
    # по умолчанию прямо в БД
    token: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        server_default=func.gen_random_uuid(),
        unique=True,
        nullable=False
    )
    # Время создания
    creation_time: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # Ставим текущее время на стороне БД
        nullable=False
    )
    # Внешний ключ на пользователя
    user_id: Mapped[int] = mapped_column(ForeignKey("advertisement_user.id"))

    user: Mapped[User] = relationship(User,
                                      back_populates="tokens",
                                      lazy="joined")

    @property
    def to_dict(self):
        return {"id": self.id, "token": str(self.token),
                "creation_time": self.creation_time.isoformat()}


class Catalog(Base):
    __tablename__ = "catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("advertisement_user.id"))
    date_creation: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # Ставим текущее время на стороне БД
        nullable=False
    )

    user: Mapped[User] = relationship(User, lazy="joined")

    def to_dict(self):
        """Вспомогательный метод для преобразования ORM-объекта в словарь."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "user_id": self.user_id,
            "date_creation": self.date_creation.isoformat(),
        }

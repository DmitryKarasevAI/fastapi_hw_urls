from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __table_args__ = {'extend_existing': True}
    pass


class Url(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(UUID(as_uuid=True), nullable=True)
    full_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, nullable=False)
    creation_time = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url_id = Column(Integer, ForeignKey('urls.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    full_url = Column(String, nullable=False)
    short_url = Column(String, ForeignKey('urls.short_url', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    access_time = Column(DateTime, nullable=False)

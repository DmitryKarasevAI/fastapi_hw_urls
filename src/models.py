from datetime import datetime

from sqlalchemy import Column, String, TIMESTAMP, Boolean, Table, Integer, DateTime, MetaData, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(UUID, primary_key=True, index=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    registered_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)


metadata = MetaData()

urls = Table(
    "urls",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("creator_id", UUID(as_uuid=True), nullable=True),
    Column("full_url", String, nullable=False),
    Column("short_url", String, unique=True, nullable=False),
    Column("creation_time", DateTime, nullable=False),
    Column("expires_at", DateTime, nullable=True),
)

queries = Table(
    "queries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("url_id", Integer, ForeignKey('urls.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    Column("full_url", String, nullable=False),
    Column("short_url", String, ForeignKey('urls.short_url', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    Column("access_time", DateTime, nullable=False),
)

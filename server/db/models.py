"""
SQLAlchemy models for cpip server.

Defines User, Device, Package, Build, and Execution tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=True)
    api_key = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    tier = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    architecture = Column(String(50))
    platform_tag = Column(String(100))
    python_version = Column(String(20))
    last_seen = Column(DateTime, default=utc_now)
    metadata_ = Column("metadata", JSON, default=dict)

    user = relationship("User", back_populates="devices")


class Package(Base):
    __tablename__ = "packages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), index=True, nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, default="")
    strategy = Column(String(50), default="local_install")
    wheel_url = Column(String(1024), nullable=True)
    wheel_hash = Column(String(64), nullable=True)
    wheel_size = Column(Integer, default=0)
    requires_gpu = Column(Boolean, default=False)
    cloud_only = Column(Boolean, default=False)
    supported_architectures = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    layers = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Build(Base):
    __tablename__ = "builds"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    package_name = Column(String(255), nullable=False)
    package_version = Column(String(50), default="latest")
    target_architecture = Column(String(50), default="aarch64")
    python_version = Column(String(20), default="3.11")
    status = Column(String(50), default="queued")  # queued, building, succeeded, failed
    wheel_url = Column(String(1024), nullable=True)
    wheel_hash = Column(String(64), nullable=True)
    build_log = Column(Text, default="")
    error = Column(Text, nullable=True)
    priority = Column(Integer, default=5)
    duration_seconds = Column(Float, default=0)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    device_id = Column(String(36), nullable=True)
    session_id = Column(String(36), nullable=True)
    method = Column(String(500))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    mode = Column(String(50), default="cloud")
    result_type = Column(String(50), default="python")
    duration_ms = Column(Float, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

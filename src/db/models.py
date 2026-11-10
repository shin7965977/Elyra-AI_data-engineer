"""SQLAlchemy 2.0 ORM models for normalized requirements and audit trails."""

import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255), default="PreFab Project")
    building_type: Mapped[str] = mapped_column(String(64), default="single_family_house")
    target_stories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_area_target_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Audit trail & lineage
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON representation
    validation_status: Mapped[str] = mapped_column(String(32), default="PASSED")
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED, REJECTED
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    spaces: Mapped[List["SpaceRecord"]] = relationship("SpaceRecord", back_populates="project", cascade="all, delete-orphan")
    constraints: Mapped[List["ConstraintRecord"]] = relationship("ConstraintRecord", back_populates="project", cascade="all, delete-orphan")
    validation_logs: Mapped[List["ValidationLogRecord"]] = relationship("ValidationLogRecord", back_populates="project", cascade="all, delete-orphan")


class SpaceRecord(Base):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    space_key: Mapped[str] = mapped_column(String(128), nullable=False)
    space_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    relationships_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Provenance
    quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_hallucinated: Mapped[bool] = mapped_column(default=False)

    project: Mapped["ProjectRecord"] = relationship("ProjectRecord", back_populates="spaces")


class ConstraintRecord(Base):
    __tablename__ = "constraints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    constraint_key: Mapped[str] = mapped_column(String(128), nullable=False)
    target_space: Mapped[str] = mapped_column(String(128), nullable=False)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)

    # Provenance
    quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_hallucinated: Mapped[bool] = mapped_column(default=False)

    project: Mapped["ProjectRecord"] = relationship("ProjectRecord", back_populates="constraints")


class ValidationLogRecord(Base):
    __tablename__ = "validation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped["ProjectRecord"] = relationship("ProjectRecord", back_populates="validation_logs")


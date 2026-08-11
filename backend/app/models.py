from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped[Optional["ProfileAvatar"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    public_profile: Mapped[Optional["PublicProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

class ProfileAvatar(Base):
    __tablename__ = "profile_avatars"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    file_storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    user: Mapped[User] = relationship(back_populates="avatar")

class PublicProfile(Base):
    __tablename__ = "public_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    show_email_public: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="public_profile")

class Presentation(Base):
    __tablename__ = "presentations"
    __table_args__ = (UniqueConstraint("title", "version", name="uq_presentation_title_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(40))
    presentation_date: Mapped[date] = mapped_column(Date)
    authors: Mapped[str] = mapped_column(Text)
    change_summary: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    file_storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[User] = relationship()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assets: Mapped[list["PresentationAsset"]] = relationship(back_populates="presentation", cascade="all, delete-orphan")

class PresentationAsset(Base):
    __tablename__ = "presentation_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"), index=True)
    relative_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    file_storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    presentation: Mapped[Presentation] = relationship(back_populates="assets")

class SiteContent(Base):
    __tablename__ = "site_content"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(100), default="ARCHER")
    tagline: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    problem: Mapped[str] = mapped_column(Text)
    objectives: Mapped[str] = mapped_column(Text)
    intended_users: Mapped[str] = mapped_column(Text)
    core_features: Mapped[str] = mapped_column(Text)
    roles_json: Mapped[str] = mapped_column(Text)

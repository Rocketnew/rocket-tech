"""Database models for Rupeewa Admin Panel."""

import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import SingletonThreadPool

DATABASE_URL = "sqlite:///rupeewa_admin.db"
engine = create_engine(DATABASE_URL, poolclass=SingletonThreadPool, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ArticleOverride(Base):
    """Custom overrides for articles on the site."""
    __tablename__ = "article_overrides"
    id = Column(Integer, primary_key=True)
    article_url = Column(String(512), unique=True, nullable=False)
    title = Column(String(500))
    is_featured = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    custom_description = Column(Text)
    custom_image = Column(String(500))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class Source(Base):
    """RSS feed sources managed independently."""
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    rss_url = Column(String(500), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    article_limit = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SiteSetting(Base):
    """Site-wide SEO and configuration settings."""
    __tablename__ = "site_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    subscribed_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BuildLog(Base):
    __tablename__ = "build_logs"
    id = Column(Integer, primary_key=True)
    status = Column(String(50), default="pending")  # pending, running, success, failed
    articles_count = Column(Integer, default=0)
    sources_count = Column(Integer, default=0)
    output_size = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime)


class PageVisit(Base):
    """Simple page visit tracking (anonymized)."""
    __tablename__ = "page_visits"
    id = Column(Integer, primary_key=True)
    path = Column(String(500))
    referrer = Column(String(500))
    user_agent = Column(String(500))
    ip_hash = Column(String(64))
    visited_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    return engine


def get_db():
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _database_url() -> str:
    """Use a migration-provided URL before loading complete app settings.

    Alembic imports model metadata but does not run the FastAPI application, so
    it must not require unrelated settings such as JWT_SECRET. Normal runtime
    configuration continues to be validated by Settings when DATABASE_URL is
    not explicitly supplied by the migration process.
    """
    if database_url := os.environ.get("DATABASE_URL"):
        return database_url
    from .config import get_settings

    return get_settings().database_url


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
class Base(DeclarativeBase): pass
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

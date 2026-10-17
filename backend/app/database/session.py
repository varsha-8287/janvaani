
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Check the .env file in the project root."
    )

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """Provide a database session to a FastAPI endpoint."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify that PostgreSQL accepts a connection."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

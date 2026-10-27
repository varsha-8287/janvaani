
import os
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

class Settings:
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "janvaani_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    JANVAANI_DEV_AUTH: str = os.getenv("JANVAANI_DEV_AUTH", "false")
    JANVAANI_DEV_REVIEWER_AUTH: str = os.getenv(
        "JANVAANI_DEV_REVIEWER_AUTH", "false"
    )

    # Development-only reviewer authentication.
    # This is not a replacement for verified production authentication.
    JANVAANI_DEV_REVIEWER_AUTH: str = os.getenv(
        "JANVAANI_DEV_REVIEWER_AUTH", "false"
    )


settings = Settings()

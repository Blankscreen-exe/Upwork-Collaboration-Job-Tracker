import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./upwork_tracker.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

settings = Settings()

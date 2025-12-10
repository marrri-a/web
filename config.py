import os
from typing import List

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://blog_user:blog_password@localhost:5432/blog_db")
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key-change-this-later")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()

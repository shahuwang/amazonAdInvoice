import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "shahuwang"
    DB_PASSWORD: str = "5201314"
    DB_NAME: str = "amazon_ad_invoice"
    DB_POOL_SIZE: int = 10
    
    UPLOAD_DIR: str = "backend/uploads"
    
    class Config:
        env_file = ".env"

settings = Settings()

DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
DB_CONFIG = {
    "host": settings.DB_HOST,
    "port": settings.DB_PORT,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD,
    "database": settings.DB_NAME,
    "charset": "utf8mb4",
    "cursorclass": "pymysql.cursors.DictCursor"
}

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

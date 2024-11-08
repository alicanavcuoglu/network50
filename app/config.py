import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SECURITY_PASSWORD_SALT = os.getenv(
        "SECURITY_PASSWORD_SALT", default="very-important"
    )
    UPLOAD_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]
    UPLOAD_PATH = "image_uploads"
    UPLOAD_AVATAR_PATH = "static/avatars"
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

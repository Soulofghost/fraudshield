import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "FraudShield"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fraudshield.db")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()

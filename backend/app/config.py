from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    FIREBASE_CREDENTIALS: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()

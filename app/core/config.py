from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "bacopilot_db"
    db_user: str = "postgres"
    db_password: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    environment: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8010

    class Config:
        env_file = ".env"


settings = Settings()
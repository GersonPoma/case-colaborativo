from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    DEBUG: bool = True
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 86400
    CORS_ALLOWED_ORIGINS: str = "http://localhost:4200"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
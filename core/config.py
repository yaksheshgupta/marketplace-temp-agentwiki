from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()

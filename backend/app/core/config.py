from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://zenail:zenail@localhost:5432/zenail"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


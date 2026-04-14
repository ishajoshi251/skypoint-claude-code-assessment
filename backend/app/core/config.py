from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    BCRYPT_ROUNDS: int = 12
    CORS_ORIGINS: str = "http://localhost:3000"

    # Email
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_ADDRESS: str = "noreply@talentbridge.local"
    EMAILS_FROM_NAME: str = "TalentBridge"

    # File uploads
    UPLOAD_DIR: str = "/app/uploads/resumes"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Rate limiting
    RATE_LIMIT_AUTH: str = "5/5minutes"

    # Seed
    SEED_HR_EMAIL: str = "hr@test.com"
    SEED_HR_PASSWORD: str = "Hr@12345"
    SEED_CANDIDATE_EMAIL: str = "candidate@test.com"
    SEED_CANDIDATE_PASSWORD: str = "Candidate@12345"

    # Feature flags
    ENABLE_LLM_JD_WRITER: bool = False
    OPENAI_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

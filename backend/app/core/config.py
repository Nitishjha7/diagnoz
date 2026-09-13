from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://diagnoz:diagnoz@db:5432/diagnoz"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DISPATCH_RADIUS_METERS: int = 5000
    DISPATCH_LOCK_TTL_SECONDS: int = 300
    PLATFORM_COMMISSION_RATE: float = 0.15
    TDS_RATE: float = 0.01

    WHISPER_MODEL: str = "base"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    TTS_API_KEY: str = ""
    TTS_VOICE: str = ""

    REFERENCE_VIDEO_PATH: str = "/var/storage/diagnoz/reference_videos"
    HLS_OUTPUT_PATH: str = "/var/storage/diagnoz/hls"

    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "diagnoz-media"


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/coding_machine"
    API_URL: str = "http://api:8000"
    CONTROLLER_PORT: int = 8003
    POLL_INTERVAL_SECONDS: int = 10
    HEARTBEAT_TIMEOUT_SECONDS: int = 60
    LEASE_TTL_SECONDS: int = 300
    SANDBOX_HEARTBEAT_TIMEOUT_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

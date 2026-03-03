from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    DATABASE_URL: str = "postgresql+asyncpg://localhost/madm"
    AGENT_WORK_PARENT: str = "/agent-work"
    TOOLS_GATEWAY_URL: str = "http://localhost:8002"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

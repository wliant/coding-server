from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/coding_machine"
    CONTROLLER_URL: str = "http://controller:8003"
    AGENT_TYPE: str = "simple_langchain_deepagent"
    WORK_DIR: str = "/agent-work"
    WORKER_PORT: int = 8004
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    TOOLS_GATEWAY_URL: str = "http://tools:8002"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

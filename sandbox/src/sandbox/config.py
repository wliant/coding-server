from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CONTROLLER_URL: str = "http://controller:8003"
    SANDBOX_PORT: int = 8006
    LABELS: str = "python,git"
    WORKSPACE_DIR: str = "/workspace"
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    SANDBOX_ID: str = ""  # Empty = use hostname as default
    COMMAND_TIMEOUT_SECONDS: int = 300

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def labels_list(self) -> list[str]:
        return [label.strip() for label in self.LABELS.split(",") if label.strip()]


settings = Settings()

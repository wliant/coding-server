from pydantic import BaseModel


class SettingsResponse(BaseModel):
    settings: dict[str, str]


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseModel):
    SLACK_BOT_TOKEN: str | None = os.getenv("SLACK_BOT_TOKEN") or None
    SLACK_USER_TOKEN: str | None = os.getenv("SLACK_USER_TOKEN") or None
    SLACK_ADMIN_TOKEN: str | None = os.getenv("SLACK_ADMIN_TOKEN") or None
    APP_NAME: str = "Slack License Inventory API"


def get_settings() -> Settings:
    return Settings()

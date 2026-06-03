from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096

    # Twilio / WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Events
    eventbrite_api_key: str = ""

    # Transport for NSW
    tfnsw_api_key: str = ""
    tfnsw_base_url: str = "https://api.transport.nsw.gov.au/v1/tp"

    # Database
    database_url: str = "sqlite+aiosqlite:///./sydney_planner.db"

    # App — Render sets PORT automatically; WEB_PORT is the local override
    web_host: str = "0.0.0.0"
    web_port: int = 8000          # overridden by PORT env var on Render
    port: int = 0                 # Render's PORT — 0 means "not set"
    debug: bool = False
    sydney_timezone: str = "Australia/Sydney"

    @property
    def effective_port(self) -> int:
        """Use Render's PORT if set, otherwise WEB_PORT."""
        return self.port if self.port else self.web_port


@lru_cache
def get_settings() -> Settings:
    return Settings()

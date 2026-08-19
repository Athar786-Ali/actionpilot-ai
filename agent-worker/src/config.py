"""
ActionPilot AI — Agent Worker Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads and validates all environment variables using Pydantic Settings.
Supports up to 5 Gemini API keys for multi-key failover rotation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# ── Load .env from project root ──────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings(BaseSettings):
    """Validated configuration for the Agent Worker."""

    # ── Redis ────────────────────────────────────────────────────
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")

    # ── Gemini API Keys (up to 5 for multi-key rotation) ────────
    gemini_api_key_1: str = Field(default="", alias="GEMINI_API_KEY_1")
    gemini_api_key_2: str = Field(default="", alias="GEMINI_API_KEY_2")
    gemini_api_key_3: str = Field(default="", alias="GEMINI_API_KEY_3")
    gemini_api_key_4: str = Field(default="", alias="GEMINI_API_KEY_4")
    gemini_api_key_5: str = Field(default="", alias="GEMINI_API_KEY_5")

    # ── Webhook (Node.js API Backend) ────────────────────────────
    webhook_url: str = Field(
        default="http://localhost:3001/api/webhooks/logs",
        alias="WEBHOOK_URL",
    )
    webhook_secret: str = Field(
        default="your-webhook-secret-key",
        alias="WEBHOOK_SECRET",
    )

    # ── BullMQ ───────────────────────────────────────────────────
    bullmq_queue_name: str = Field(
        default="actionpilot:jobs",
        alias="BULLMQ_QUEUE_NAME",
    )

    # ── HITL ─────────────────────────────────────────────────────
    redis_hitl_channel_prefix: str = Field(
        default="actionpilot:hitl:",
        alias="REDIS_HITL_CHANNEL_PREFIX",
    )
    hitl_timeout_seconds: int = Field(default=300, alias="HITL_TIMEOUT_SECONDS")

    # ── Browser ──────────────────────────────────────────────────
    browser_headless: bool = Field(default=True, alias="BROWSER_HEADLESS")

    @property
    def gemini_api_keys(self) -> list[str]:
        """Return a list of all non-empty Gemini API keys."""
        all_keys = [
            self.gemini_api_key_1,
            self.gemini_api_key_2,
            self.gemini_api_key_3,
            self.gemini_api_key_4,
            self.gemini_api_key_5,
        ]
        return [k for k in all_keys if k and not k.startswith("your-")]

    @field_validator(
        "gemini_api_key_1",
        "gemini_api_key_2",
        "gemini_api_key_3",
        "gemini_api_key_4",
        "gemini_api_key_5",
        mode="before",
    )
    @classmethod
    def _normalize_empty_keys(cls, v: str | None) -> str:
        """Allow empty keys (only key_1 needs to be set)."""
        return v or ""

    @property
    def redis_url(self) -> str:
        """Construct a full Redis URL for clients that accept it."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    model_config = {
        "env_file": ".env",
        "populate_by_name": True,
        "extra": "ignore",
    }


# ── Singleton ────────────────────────────────────────────────────
settings = Settings()  # type: ignore[call-arg]

# ── Validate at least one key is present ─────────────────────────
if not settings.gemini_api_keys:
    raise ValueError(
        "At least GEMINI_API_KEY_1 must be set to a valid API key. "
        "Get one at https://aistudio.google.com/apikey"
    )

# ── Logging Setup ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-24s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("actionpilot.worker")
logger.info("✅ Configuration loaded successfully")
logger.info("   Redis: %s:%d", settings.redis_host, settings.redis_port)
logger.info("   Webhook: %s", settings.webhook_url)
logger.info("   Queue: %s", settings.bullmq_queue_name)
logger.info("   Headless: %s", settings.browser_headless)
logger.info("   Gemini API keys loaded: %d", len(settings.gemini_api_keys))

"""
ActionPilot AI — Agent Worker Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads and validates all environment variables using Pydantic Settings.
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

    # ── Groq (Free Llama 3.3 70B with tool-calling support) ─────
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")

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

    @field_validator("groq_api_key")
    @classmethod
    def _validate_groq_key(cls, v: str) -> str:
        if not v or v.startswith("your-"):
            raise ValueError(
                "GROQ_API_KEY must be set to a valid API key. "
                "Get a free one at https://console.groq.com/keys"
            )
        return v

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

"""
ActionPilot AI — Human-in-the-Loop Handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Subscribes to a Redis Pub/Sub channel for a specific job and blocks
until a human operator submits an OTP/verification code via the
Node.js API, which then publishes it to Redis.

Flow:
  1. Agent detects OTP/CAPTCHA field → calls `wait_for_human_input()`
  2. This function subscribes to `actionpilot:hitl:{job_id}`
  3. The human submits OTP via POST /api/jobs/:id/submit-otp
  4. Node.js publishes OTP to the same Redis channel
  5. This function receives the message, unsubscribes, and returns the OTP
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Optional

import redis

from .config import settings

logger = logging.getLogger("actionpilot.hitl")


class HITLTimeoutError(Exception):
    """Raised when the human does not respond within the timeout period."""

    pass


def wait_for_human_input(
    job_id: str,
    timeout: Optional[int] = None,
) -> str:
    """
    Block until a human submits OTP/verification input for the given job.

    This uses Redis Pub/Sub with a dedicated subscriber connection so it
    does not interfere with the main Redis connection used by BullMQ.

    Parameters:
        job_id:  The UUID of the job requiring human input.
        timeout: Seconds to wait before raising HITLTimeoutError.
                 Defaults to settings.hitl_timeout_seconds (300s).

    Returns:
        The OTP string submitted by the human operator.

    Raises:
        HITLTimeoutError: If no response is received within the timeout.
    """
    effective_timeout = timeout or settings.hitl_timeout_seconds
    channel = f"{settings.redis_hitl_channel_prefix}{job_id}"

    logger.info(
        "⏳ HITL: Waiting for human input on channel '%s' (timeout=%ds)",
        channel,
        effective_timeout,
    )

    # ── Create a dedicated Redis connection for Pub/Sub ──────────
    subscriber = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )

    pubsub = subscriber.pubsub()
    received_otp: Optional[str] = None
    error: Optional[Exception] = None

    def _listen() -> None:
        """Background thread that listens for the Pub/Sub message."""
        nonlocal received_otp, error
        try:
            pubsub.subscribe(channel)
            logger.info("📡 HITL: Subscribed to channel '%s'", channel)

            # pubsub.listen() yields messages; we filter for 'message' type
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        received_otp = payload.get("otp", "")
                        logger.info(
                            "✅ HITL: Received OTP for job %s (length=%d)",
                            job_id,
                            len(received_otp),
                        )
                    except (json.JSONDecodeError, KeyError) as parse_err:
                        # Fallback: treat raw data as OTP string
                        received_otp = str(message["data"])
                        logger.warning(
                            "⚠️ HITL: Could not parse JSON, using raw data: %s",
                            parse_err,
                        )
                    break  # We only need one message
        except Exception as exc:
            error = exc
            logger.error("❌ HITL: Listener error: %s", exc)

    # ── Run listener in a background thread with timeout ─────────
    listener_thread = threading.Thread(target=_listen, daemon=True)
    listener_thread.start()
    listener_thread.join(timeout=effective_timeout)

    # ── Cleanup ──────────────────────────────────────────────────
    try:
        pubsub.unsubscribe(channel)
        pubsub.close()
        subscriber.close()
    except Exception as cleanup_err:
        logger.warning("⚠️ HITL: Cleanup error: %s", cleanup_err)

    # ── Evaluate result ──────────────────────────────────────────
    if error is not None:
        raise error

    if received_otp is None:
        raise HITLTimeoutError(
            f"No human response received for job {job_id} within "
            f"{effective_timeout} seconds on channel '{channel}'"
        )

    return received_otp

"""
ActionPilot AI — Webhook Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sends real-time audit logs from the Python Agent Worker back to the
Node.js API Gateway via authenticated HTTP POST requests.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import settings

logger = logging.getLogger("actionpilot.webhook")


class WebhookClient:
    """
    HTTP client for posting agent action logs to the Node.js API backend.

    Features:
    - Automatic retry with exponential backoff on transient failures.
    - x-webhook-secret header authentication.
    - Structured log payloads matching the Zod schema in webhookController.ts.
    """

    def __init__(self) -> None:
        self._url = settings.webhook_url
        self._secret = settings.webhook_secret
        self._session = self._build_session()
        logger.info("🔗 WebhookClient initialized → %s", self._url)

    # ── Private ──────────────────────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        """Create a requests Session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _post(self, payload: dict[str, Any]) -> bool:
        """
        Send a POST request to the webhook endpoint.
        Returns True on success, False on failure (after retries).
        """
        headers = {
            "Content-Type": "application/json",
            "x-webhook-secret": self._secret,
        }
        try:
            response = self._session.post(
                self._url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            if response.ok:
                data = response.json()
                log_id = data.get("data", {}).get("logId", "unknown")
                logger.info(
                    "📤 Webhook sent [%s] → logId=%s",
                    payload.get("actionType", "?"),
                    log_id,
                )
                return True
            else:
                logger.error(
                    "❌ Webhook failed (HTTP %d): %s",
                    response.status_code,
                    response.text[:200],
                )
                return False
        except requests.RequestException as exc:
            logger.error("❌ Webhook request error: %s", exc)
            return False

    # ── Public API ───────────────────────────────────────────────

    def send_log(
        self,
        job_id: str,
        action_type: str,
        description: str,
        *,
        screenshot_url: Optional[str] = None,
        status: Optional[str] = None,
        result_data: Optional[Any] = None,
    ) -> bool:
        """
        Send an audit log entry to the Node.js API backend.

        Parameters:
            job_id:         UUID of the job this log belongs to.
            action_type:    Category of the action (e.g., "NAVIGATE", "CLICK", "TYPE").
            description:    Human-readable description of what happened.
            screenshot_url: Optional URL to a screenshot taken during the action.
            status:         Optional job status update (e.g., "RUNNING", "COMPLETED").
            result_data:    Optional result data to attach when the job completes.
        """
        payload: dict[str, Any] = {
            "jobId": job_id,
            "actionType": action_type,
            "description": description,
        }
        if screenshot_url is not None:
            payload["screenshotUrl"] = screenshot_url
        if status is not None:
            payload["status"] = status
        if result_data is not None:
            payload["resultData"] = result_data

        return self._post(payload)

    def send_status_running(self, job_id: str) -> bool:
        """Mark a job as RUNNING when the agent begins execution."""
        return self.send_log(
            job_id=job_id,
            action_type="JOB_STARTED",
            description="Agent worker has picked up the job and started execution",
            status="RUNNING",
        )

    def send_status_completed(
        self, job_id: str, result_data: Optional[Any] = None
    ) -> bool:
        """Mark a job as COMPLETED with optional result data."""
        return self.send_log(
            job_id=job_id,
            action_type="JOB_COMPLETED",
            description="Agent has successfully completed the task",
            status="COMPLETED",
            result_data=result_data,
        )

    def send_status_failed(self, job_id: str, error_message: str) -> bool:
        """Mark a job as FAILED with the error details."""
        return self.send_log(
            job_id=job_id,
            action_type="JOB_FAILED",
            description=f"Agent execution failed: {error_message}",
            status="FAILED",
            result_data={"error": error_message},
        )

    def send_status_paused_for_hitl(self, job_id: str, reason: str) -> bool:
        """Mark a job as PAUSED_FOR_HITL when human input is required."""
        return self.send_log(
            job_id=job_id,
            action_type="HITL_REQUESTED",
            description=f"Agent paused for human input: {reason}",
            status="PAUSED_FOR_HITL",
        )

    def send_agent_action(
        self,
        job_id: str,
        action_type: str,
        description: str,
        *,
        screenshot_url: Optional[str] = None,
    ) -> bool:
        """Log a generic browser action (navigate, click, type, etc.)."""
        return self.send_log(
            job_id=job_id,
            action_type=action_type,
            description=description,
            screenshot_url=screenshot_url,
        )

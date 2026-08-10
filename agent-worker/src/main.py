"""
ActionPilot AI — Agent Worker Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Initializes a BullMQ Worker that listens to the `actionpilot:jobs` Redis
queue. When a job arrives, it extracts jobId and prompt, runs the
browser-use agent, and reports status back to the Node.js API via webhooks.

Usage:
    python -m src.main
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import traceback
from typing import Any

from bullmq import Worker

from .agent_runner import run_agent
from .config import settings
from .webhook_client import WebhookClient

logger = logging.getLogger("actionpilot.main")

# ── Global shutdown flag ─────────────────────────────────────────
_shutdown_event = asyncio.Event()


async def process_job(job: Any, token: str | None = None) -> Any:
    """
    BullMQ job processor. Called for each job consumed from the queue.

    The job.data payload matches the BullMQJobData interface from the
    Node.js API:
        { "jobId": "uuid", "prompt": "natural language task" }
    """
    webhook = WebhookClient()

    # ── Extract job data ─────────────────────────────────────────
    job_data: dict[str, Any] = job.data if isinstance(job.data, dict) else {}
    job_id: str = job_data.get("jobId", "")
    prompt: str = job_data.get("prompt", "")

    if not job_id or not prompt:
        logger.error(
            "❌ Invalid job data received: %s. Expected {jobId, prompt}.",
            job_data,
        )
        raise ValueError(f"Invalid job payload: missing jobId or prompt in {job_data}")

    logger.info(
        "━" * 60 + "\n"
        "📥 Job received: %s\n"
        "   Prompt: %s\n"
        "━" * 60,
        job_id,
        prompt[:120],
    )

    # ── Mark job as RUNNING ──────────────────────────────────────
    webhook.send_status_running(job_id)

    try:
        # ── Run the browser-use agent ────────────────────────────
        result_data = await run_agent(job_id=job_id, prompt=prompt)

        # ── Mark job as COMPLETED ────────────────────────────────
        webhook.send_status_completed(job_id, result_data=result_data)

        logger.info("✅ Job %s completed successfully", job_id)
        return result_data

    except Exception as err:
        # ── Mark job as FAILED ───────────────────────────────────
        error_message = f"{type(err).__name__}: {err}"
        logger.error(
            "❌ Job %s failed: %s\n%s",
            job_id,
            error_message,
            traceback.format_exc(),
        )
        webhook.send_status_failed(job_id, error_message)

        # Re-raise so BullMQ marks the job as failed and can retry
        raise


async def start_worker() -> None:
    """
    Initialize and start the BullMQ Worker.

    The worker connects to Redis and continuously polls the
    `actionpilot:jobs` queue for new jobs to process.
    """
    logger.info(
        "\n"
        "  ╔══════════════════════════════════════════════╗\n"
        "  ║   🤖 ActionPilot AI — Agent Worker           ║\n"
        "  ║   📡 Queue: %-30s  ║\n"
        "  ║   🔗 Redis: %s:%-23d  ║\n"
        "  ╚══════════════════════════════════════════════╝\n",
        settings.bullmq_queue_name,
        settings.redis_host,
        settings.redis_port,
    )

    # ── Build Redis connection options ───────────────────────────
    redis_opts: dict[str, Any] = {
        "host": settings.redis_host,
        "port": settings.redis_port,
    }
    if settings.redis_password:
        redis_opts["password"] = settings.redis_password

    # ── Create the BullMQ Worker ─────────────────────────────────
    worker = Worker(
        name=settings.bullmq_queue_name,
        processor=process_job,
        opts={
            "connection": redis_opts,
            "concurrency": 1,  # Process one browser session at a time
            "autorun": True,
        },
    )

    logger.info("🟢 Worker started, waiting for jobs...")

    # ── Wait for shutdown signal ─────────────────────────────────
    await _shutdown_event.wait()

    # ── Graceful shutdown ────────────────────────────────────────
    logger.info("📴 Shutting down worker...")
    await worker.close()
    logger.info("✅ Worker shut down cleanly")


def _handle_signal(sig: signal.Signals) -> None:
    """Handle OS signals for graceful shutdown."""
    logger.info("📴 Received signal %s, initiating shutdown...", sig.name)
    _shutdown_event.set()


def main() -> None:
    """Entry point for the agent worker process."""
    # ── Register signal handlers ─────────────────────────────────
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    try:
        loop.run_until_complete(start_worker())
    except KeyboardInterrupt:
        logger.info("📴 Worker interrupted by keyboard")
    finally:
        loop.close()
        logger.info("👋 Agent worker process exited")
        sys.exit(0)


if __name__ == "__main__":
    main()

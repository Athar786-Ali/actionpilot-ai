"""
ActionPilot AI — Agent Runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Initializes and executes the browser-use Agent with Google Gemini Flash,
custom action logging callbacks, and a Human-in-the-Loop (HITL) tool
for OTP/CAPTCHA scenarios.

Architecture:
  1. A custom `Controller` is created with an `ask_human_for_otp` tool.
  2. The agent is initialized with the user's prompt and Gemini 2.0 Flash.
  3. A `register_action_callback` hook sends every browser action back
     to the Node.js API via webhook.
  4. When the LLM encounters OTP/CAPTCHA, it invokes `ask_human_for_otp`,
     which pauses the agent, notifies the API, and waits for Redis Pub/Sub.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any, Optional

from browser_use import Agent, Browser, BrowserConfig, Controller
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from .config import settings
from .hitl_handler import HITLTimeoutError, wait_for_human_input
from .webhook_client import WebhookClient

logger = logging.getLogger("actionpilot.agent")


# ── Pydantic model for the HITL tool input ───────────────────────
class AskHumanInput(BaseModel):
    """Input schema for the ask_human_for_otp tool."""

    reason: str = "OTP or verification code required"


# ── Agent Runner ─────────────────────────────────────────────────
async def run_agent(job_id: str, prompt: str) -> dict[str, Any]:
    """
    Execute a browser-use agent session for the given job.

    Parameters:
        job_id: UUID of the job being processed.
        prompt: Natural language task description from the user.

    Returns:
        A dict with the agent's result data including extracted content
        and action history.

    Raises:
        Exception: Any unhandled error during agent execution.
    """
    webhook = WebhookClient()
    controller = Controller()

    # ── Register the HITL tool on the controller ─────────────────
    @controller.action(
        description=(
            "Use this tool when you encounter an OTP input field, CAPTCHA, "
            "two-factor authentication prompt, or any verification screen "
            "that requires a code from the human user. This will pause "
            "execution and wait for the human to provide the code. "
            "Returns the OTP/code as a string that you should type into "
            "the appropriate field."
        ),
    )
    async def ask_human_for_otp(reason: str = "OTP or verification code required") -> str:
        """Pause the agent and wait for human-provided OTP via Redis Pub/Sub."""
        logger.info("🛑 HITL tool invoked for job %s: %s", job_id, reason)

        # 1. Notify the API that we need human input
        webhook.send_status_paused_for_hitl(job_id, reason)

        # 2. Wait for the OTP on Redis Pub/Sub (blocking call in a thread)
        try:
            otp = await asyncio.get_event_loop().run_in_executor(
                None,  # default executor (ThreadPoolExecutor)
                wait_for_human_input,
                job_id,
            )
            logger.info("✅ HITL: Received OTP for job %s, resuming agent", job_id)

            # 3. Notify the API that we're resuming
            webhook.send_agent_action(
                job_id=job_id,
                action_type="HITL_RESUMED",
                description=f"Agent resumed after receiving human input for: {reason}",
            )

            return otp

        except HITLTimeoutError:
            logger.error("⏰ HITL: Timeout waiting for human input on job %s", job_id)
            webhook.send_status_failed(
                job_id,
                f"Human input timeout: No response within {settings.hitl_timeout_seconds}s",
            )
            raise

    # ── Initialize the LLM ───────────────────────────────────────
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
        max_tokens=8192,
    )

    # ── Configure the Browser ────────────────────────────────────
    browser_config = BrowserConfig(
        headless=settings.browser_headless,
    )
    browser = Browser(config=browser_config)

    # ── Build the Agent ──────────────────────────────────────────
    agent = Agent(
        task=prompt,
        llm=llm,
        browser=browser,
        controller=controller,
        max_actions_per_step=5,
        use_vision=True,
    )

    # ── Register action callback for real-time logging ───────────
    # browser-use calls this after every action step with action details
    original_step = agent.step

    async def _instrumented_step(*args: Any, **kwargs: Any) -> Any:
        """Wraps Agent.step() to log each action via webhook."""
        result = await original_step(*args, **kwargs)

        # Extract action details from the step result if available
        try:
            if result and hasattr(result, "model_output") and result.model_output:
                for action in result.model_output:
                    action_dict = (
                        action.model_dump()
                        if hasattr(action, "model_dump")
                        else str(action)
                    )
                    # Determine action type from the action object
                    action_type = "AGENT_ACTION"
                    description = str(action_dict)

                    if isinstance(action_dict, dict):
                        # Extract a cleaner action type from the action keys
                        action_keys = [
                            k for k in action_dict.keys() if action_dict[k] is not None
                        ]
                        if action_keys:
                            action_type = action_keys[0].upper()
                            action_value = action_dict[action_keys[0]]
                            if isinstance(action_value, dict):
                                description = str(action_value)
                            else:
                                description = str(action_value)

                    webhook.send_agent_action(
                        job_id=job_id,
                        action_type=action_type,
                        description=description[:500],  # Truncate long descriptions
                    )
        except Exception as log_err:
            # Never let logging failures crash the agent
            logger.warning("⚠️ Failed to log action via webhook: %s", log_err)

        return result

    agent.step = _instrumented_step  # type: ignore[assignment]

    # ── Execute the Agent ────────────────────────────────────────
    logger.info("▶️  Starting agent for job %s with prompt: %s", job_id, prompt[:100])
    webhook.send_agent_action(
        job_id=job_id,
        action_type="AGENT_INITIALIZED",
        description=f"Agent initialized with prompt: {prompt[:200]}",
    )

    try:
        result = await agent.run()

        # ── Extract result data ──────────────────────────────────
        result_data: dict[str, Any] = {
            "final_result": result.final_result() if hasattr(result, "final_result") else str(result),
            "is_done": result.is_done() if hasattr(result, "is_done") else True,
        }

        # Collect action history if available
        if hasattr(result, "action_results"):
            result_data["total_actions"] = len(result.action_results())
        if hasattr(result, "errors") and result.errors():
            result_data["errors"] = [str(e) for e in result.errors()]

        logger.info(
            "✅ Agent completed job %s successfully. Result: %s",
            job_id,
            str(result_data)[:200],
        )

        return result_data

    except Exception as agent_err:
        logger.error(
            "❌ Agent execution failed for job %s: %s\n%s",
            job_id,
            agent_err,
            traceback.format_exc(),
        )
        raise

    finally:
        # Always close the browser to free resources
        try:
            await browser.close()
            logger.info("🧹 Browser closed for job %s", job_id)
        except Exception as close_err:
            logger.warning("⚠️ Error closing browser: %s", close_err)

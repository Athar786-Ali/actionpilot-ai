"""
ActionPilot AI — Agent Runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Initializes and executes the browser-use Agent with Google Gemini Flash,
custom action logging callbacks, and a Human-in-the-Loop (HITL) tool
for OTP/CAPTCHA scenarios.

Architecture:
  1. A custom `Tools` (controller) is created with an `ask_human_for_otp` action.
  2. The agent is initialized with the user's prompt and Gemini 2.0 Flash
     via browser-use's built-in ChatGoogle LLM wrapper.
  3. A `register_new_step_callback` hook sends every browser action back
     to the Node.js API via webhook after each agent step.
  4. When the LLM encounters OTP/CAPTCHA, it invokes `ask_human_for_otp`,
     which pauses the agent, notifies the API, and waits for Redis Pub/Sub.

Compatible with browser-use >= 0.13.x
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from browser_use.agent.service import Agent
from browser_use.agent.views import AgentOutput
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.browser.views import BrowserStateSummary
from browser_use.tools.service import Tools
from langchain_openai import ChatOpenAI

from .config import settings
from .hitl_handler import HITLTimeoutError, wait_for_human_input
from .webhook_client import WebhookClient

logger = logging.getLogger("actionpilot.agent")


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
    controller = Tools()

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
    async def ask_human_for_otp(
        reason: str = "OTP or verification code required",
    ) -> str:
        """Pause the agent and wait for human-provided OTP via Redis Pub/Sub."""
        logger.info("🛑 HITL tool invoked for job %s: %s", job_id, reason)

        # 1. Notify the API that we need human input
        webhook.send_status_paused_for_hitl(job_id, reason)

        # 2. Wait for the OTP on Redis Pub/Sub (blocking call offloaded to thread)
        try:
            loop = asyncio.get_running_loop()
            otp = await loop.run_in_executor(
                None,  # default ThreadPoolExecutor
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

    # ── Step callback for real-time webhook logging ──────────────
    def _on_step(
        browser_state: BrowserStateSummary,
        agent_output: AgentOutput,
        step_number: int,
    ) -> None:
        """Called by browser-use after every agent step with action details."""
        try:
            # Log each action from the agent's output
            if agent_output.action:
                for action_model in agent_output.action:
                    action_dict = action_model.model_dump(exclude_none=True)

                    # Determine action type from the action dict keys
                    action_type = "AGENT_ACTION"
                    description = str(action_dict)

                    if isinstance(action_dict, dict):
                        action_keys = [
                            k
                            for k in action_dict.keys()
                            if k not in ("interacted_element",)
                            and action_dict[k] is not None
                        ]
                        if action_keys:
                            action_type = action_keys[0].upper()
                            action_value = action_dict[action_keys[0]]
                            description = str(action_value)

                    webhook.send_agent_action(
                        job_id=job_id,
                        action_type=action_type,
                        description=(
                            f"[Step {step_number}] {description[:500]}"
                        ),
                    )

            # Also log the agent's thinking/goal if present
            if agent_output.next_goal:
                webhook.send_agent_action(
                    job_id=job_id,
                    action_type="AGENT_GOAL",
                    description=(
                        f"[Step {step_number}] Goal: {agent_output.next_goal[:300]}"
                    ),
                )

        except Exception as log_err:
            # Never let logging failures crash the agent
            logger.warning("⚠️ Failed to log step via webhook: %s", log_err)

    # ── Custom LLM class (browser-use expects a .provider attribute) ─
    class CustomChatOpenAI(ChatOpenAI):
        @property
        def provider(self) -> str:
            return "openai"

    # ── Initialize the LLM (Nvidia NIM — Llama 3.2 Vision) ────────
    llm = CustomChatOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.2-90b-vision-instruct",
        api_key=settings.nvidia_api_key,
        temperature=0.1,
        max_tokens=8192,
    )

    # ── Configure browser profile ────────────────────────────────
    browser_profile = BrowserProfile(
        headless=settings.browser_headless,
    )

    # ── Create browser session ───────────────────────────────────
    browser_session = BrowserSession(
        browser_profile=browser_profile,
    )

    # ── Build the Agent ──────────────────────────────────────────
    agent = Agent(
        task=prompt,
        llm=llm,
        browser_session=browser_session,
        controller=controller,
        register_new_step_callback=_on_step,
        max_actions_per_step=5,
        use_vision=True,
    )
    
    # ── Execute the Agent ────────────────────────────────────────
    logger.info("▶️  Starting agent for job %s with prompt: %s", job_id, prompt[:100])
    webhook.send_agent_action(
        job_id=job_id,
        action_type="AGENT_INITIALIZED",
        description=f"Agent initialized with prompt: {prompt[:200]}",
    )

    try:
        result = await agent.run()

        # ── Extract result data from AgentHistoryList ────────────
        result_data: dict[str, Any] = {
            "final_result": result.final_result(),
            "is_done": result.is_done(),
            "total_actions": result.number_of_steps(),
        }

        if result.errors():
            result_data["errors"] = [str(e) for e in result.errors()]

        if result.is_successful() is not None:
            result_data["is_successful"] = result.is_successful()

        if result.extracted_content():
            result_data["extracted_content"] = result.extracted_content()

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
        # Always close the browser session to free resources
        try:
            await browser_session.close()
            logger.info("🧹 Browser session closed for job %s", job_id)
        except Exception as close_err:
            logger.warning("⚠️ Error closing browser session: %s", close_err)

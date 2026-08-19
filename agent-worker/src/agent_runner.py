"""
ActionPilot AI — Agent Runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Initializes and executes the browser-use Agent with Google Gemini 2.0 Flash
and a **multi-key failover rotation** system to handle rate limits seamlessly.

Architecture:
  1. GeminiKeyPool loads up to 5 Gemini API keys and creates a ChatGoogle
     instance for each.  When a 429 / rate-limit error is raised (after
     ChatGoogle's own internal retries are exhausted), the pool catches it,
     logs a warning, rotates to the next key, and transparently retries.
  2. A custom `Tools` controller exposes an `ask_human_for_otp` HITL tool.
  3. A `register_new_step_callback` hook streams every action to the
     Node.js API via webhook.

Compatible with browser-use >= 0.13.x
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any, TypeVar, overload

from browser_use.agent.service import Agent
from browser_use.agent.views import AgentOutput
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.browser.views import BrowserStateSummary
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.google.chat import ChatGoogle
from browser_use.llm.messages import BaseMessage
from browser_use.tools.service import Tools
from browser_use.llm.views import ChatInvokeCompletion

from .config import settings
from .hitl_handler import HITLTimeoutError, wait_for_human_input
from .webhook_client import WebhookClient

logger = logging.getLogger("actionpilot.agent")

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════
# GEMINI MULTI-KEY FAILOVER POOL
# ═══════════════════════════════════════════════════════════════════

class GeminiKeyPool:
    """
    A pool of Gemini API keys that automatically rotates on rate-limit
    errors.  Implements the browser-use ``BaseChatModel`` protocol so it
    can be passed directly to ``Agent(llm=...)``.

    Flow on each ``ainvoke`` call:
      1. Try the current ChatGoogle client.
      2. ChatGoogle internally retries 429s up to ``max_retries`` times.
      3. If it *still* fails with a rate-limit status, we catch the error,
         rotate to the next key, and retry — up to ``len(keys)`` times.
      4. If ALL keys are exhausted, re-raise the last error.
    """

    def __init__(
        self,
        api_keys: list[str],
        model: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        max_output_tokens: int = 8192,
    ) -> None:
        if not api_keys:
            raise ValueError("GeminiKeyPool requires at least one API key")

        self.model: str = model
        self._keys = api_keys
        self._current_idx = 0
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

        # Pre-build a ChatGoogle instance per key
        self._clients: list[ChatGoogle] = [
            ChatGoogle(
                model=model,
                api_key=key,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                # ChatGoogle's own internal retry (5 attempts per key)
                max_retries=5,
            )
            for key in api_keys
        ]

        logger.info(
            "🔑 GeminiKeyPool initialised with %d key(s), model=%s",
            len(api_keys),
            model,
        )

    # ── BaseChatModel protocol attributes ────────────────────────
    @property
    def provider(self) -> str:
        return "google"

    @property
    def name(self) -> str:
        return f"gemini-key-pool-{len(self._keys)}x"

    @property
    def model_name(self) -> str:
        return self.model

    # ── Key rotation helpers ─────────────────────────────────────
    @property
    def _current_key_label(self) -> str:
        return f"Key {self._current_idx + 1}/{len(self._keys)}"

    def _rotate(self) -> None:
        """Advance to the next API key in the pool."""
        prev = self._current_idx + 1
        self._current_idx = (self._current_idx + 1) % len(self._keys)
        logger.warning(
            "🔄 Rate limit hit on Key %d — switching to Key %d",
            prev,
            self._current_idx + 1,
        )

    @staticmethod
    def _is_rate_limit(err: Exception) -> bool:
        """Check whether an exception is a rate-limit / quota error."""
        if isinstance(err, ModelRateLimitError):
            return True
        if isinstance(err, ModelProviderError) and err.status_code == 429:
            return True
        # Catch google-genai's own ClientError / ResourceExhausted
        err_str = str(err).lower()
        return any(
            kw in err_str
            for kw in ("429", "resource exhausted", "rate limit", "quota")
        )

    # ── Core ainvoke with failover ───────────────────────────────
    @overload
    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T] = ...,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T] | None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        """
        Call Gemini with automatic key rotation on rate-limit errors.

        Each key gets ChatGoogle's full internal retry budget (5 retries
        with exponential backoff).  Only when ALL retries on a key fail
        with 429 do we rotate to the next key.
        """
        last_error: Exception | None = None
        attempts = len(self._clients)

        for attempt in range(attempts):
            client = self._clients[self._current_idx]
            try:
                return await client.ainvoke(messages, output_format, **kwargs)

            except Exception as err:
                if self._is_rate_limit(err) and attempt < attempts - 1:
                    last_error = err
                    self._rotate()
                    # Brief cooldown before hitting the next key
                    await asyncio.sleep(1.0)
                    continue
                # Not a rate limit OR all keys exhausted → propagate
                raise

        # Should never reach here, but just in case
        raise last_error or RuntimeError("GeminiKeyPool: all keys exhausted")


# ═══════════════════════════════════════════════════════════════════
# AGENT RUNNER
# ═══════════════════════════════════════════════════════════════════

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

    # ── Initialize the LLM (Gemini 2.0 Flash — Multi-Key Pool) ──
    llm = GeminiKeyPool(
        api_keys=settings.gemini_api_keys,
        model="gemini-2.0-flash",
        temperature=0.1,
        max_output_tokens=8192,
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

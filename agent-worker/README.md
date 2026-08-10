# ActionPilot AI — Agent Worker

Agentic Python worker that consumes browser automation jobs from Redis (BullMQ) and executes them using `browser-use` with Google Gemini 2.0 Flash.

## Architecture

```
Redis (BullMQ Queue) → Python Worker → browser-use Agent → Playwright Browser
         ↑                    │
         │                    ├── Webhooks → Node.js API (audit logs)
         │                    │
         └── Pub/Sub ←────────┘  (HITL OTP flow)
```

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 5. Start the worker
python -m src.main
```

## HITL (Human-in-the-Loop) Flow

When the agent encounters an OTP or CAPTCHA field:

1. Agent invokes `ask_human_for_otp` tool
2. Worker sends `PAUSED_FOR_HITL` webhook to Node.js API
3. Worker subscribes to `actionpilot:hitl:{job_id}` Redis channel
4. Human submits OTP via `POST /api/jobs/:id/submit-otp`
5. Node.js publishes OTP to Redis Pub/Sub
6. Worker receives OTP, types it into the browser, and continues

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `GEMINI_API_KEY` | Google Gemini API key | **required** |
| `WEBHOOK_URL` | Node.js webhook endpoint | `http://localhost:3001/api/webhooks/logs` |
| `WEBHOOK_SECRET` | Shared secret for webhook auth | `your-webhook-secret-key` |
| `HITL_TIMEOUT_SECONDS` | OTP wait timeout | `300` |
| `BROWSER_HEADLESS` | Run browser headless | `true` |

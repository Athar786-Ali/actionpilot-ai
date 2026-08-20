<div align="center">

# 🤖 ActionPilot AI

### Autonomous Browser Automation Platform — Powered by Gemini AI

*Tell the agent what to do in plain English. It launches a real browser, navigates pages, clicks buttons, fills forms, extracts data — and pauses for your OTP when needed.*

[![Live Demo](https://img.shields.io/badge/▶_Watch_Demo-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](#-demo)
[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=for-the-badge&logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js_15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Gemini](https://img.shields.io/badge/Gemini_3.6_Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

**[✨ Features](#-features) · [🏗 Architecture](#-system-architecture) · [🚀 Quick Start](#-quick-start) · [📡 API](#-api-reference) · [🔄 HITL](#-human-in-the-loop-hitl-deep-dive) · [🔑 Multi-Key](#-multi-key-failover-rotation)**

</div>

---

## 🎬 Demo

```
You type:  "Go to amazon.in, search for wireless headphones, extract top 5 with prices"

Agent does: Launch browser → Navigate to Amazon → Type in search bar → Click Search →
            Read results → Extract product names + prices → Return formatted list

You see:   Real-time action logs streaming in a terminal-style UI, then a clean
           result card with numbered items and metadata badges.
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Natural Language Tasks** | Describe any web task in plain English — the AI figures out what to click, type, and navigate |
| 👁️ **Vision-Capable Agent** | Gemini 3.6 Flash *sees* the page via screenshots and reasons about UI elements — no brittle CSS selectors |
| 🔄 **Human-in-the-Loop (HITL)** | Agent auto-pauses on OTP/CAPTCHA, sends you a modal, waits for your code, then resumes seamlessly |
| 🔑 **Multi-Key Failover** | Up to 5 Gemini API keys with automatic rotation on rate limits — zero downtime for heavy workloads |
| 📺 **Real-Time Dashboard** | Glassmorphic Next.js UI with live-streaming action logs, status badges, and enterprise result cards |
| 📋 **Full Audit Trail** | Every click, type, navigate, and scroll is logged to PostgreSQL with timestamps |
| 🏗️ **Microservices Architecture** | Decoupled Node.js API + Python Worker — communicate via Redis (BullMQ + Pub/Sub) + Webhooks |
| 🎯 **Enterprise Result Cards** | Rich text rendering of results — numbered lists, bullet points, success badges, collapsible raw details |

---

## 🏗 System Architecture

```
                            ┌──────────────────────────────┐
                            │     Next.js 15 Frontend      │
                            │  (Glassmorphic Dashboard UI)  │
                            └──────────────┬───────────────┘
                                           │ HTTP (proxied)
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     NODE.JS API GATEWAY  (Express + TypeScript)              │
│                                                                              │
│   POST /api/jobs          GET /api/jobs/:id        POST /api/jobs/:id/       │
│   → Create + Enqueue      → Status + Audit Logs    submit-otp               │
│                                                    → Publish OTP via Redis   │
│                                                                              │
│   ┌────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│   │ Prisma ORM │   │   BullMQ     │   │ Redis Pub/Sub│   │  Zod + HMAC  │  │
│   │ PostgreSQL │   │  Job Queue   │   │  (Publisher)  │   │  Validation  │  │
│   └─────┬──────┘   └──────┬───────┘   └──────┬───────┘   └──────────────┘  │
└─────────┼─────────────────┼──────────────────┼──────────────────────────────┘
          │                 │                  │
          │ Persist         │ Enqueue          │ PUBLISH otp
          ▼                 ▼                  ▼
   ┌────────────┐   ┌────────────┐     ┌────────────┐
   │ PostgreSQL │   │   Redis    │     │   Redis    │
   │  (Jobs +   │   │  (Queue)   │     │ (Pub/Sub)  │
   │ AuditLogs) │   └─────┬──────┘     └─────┬──────┘
   └────────────┘         │                   │
                          │ Consume job       │ SUBSCRIBE
                          ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    PYTHON AGENT WORKER  (browser-use v0.13.8)                │
│                                                                              │
│   ┌──────────────┐   ┌───────────────────────┐   ┌──────────────────────┐  │
│   │ BullMQ       │   │    GeminiKeyPool       │   │   HITL Handler       │  │
│   │ Consumer     │──▶│  (Multi-Key Failover)  │   │  Redis Pub/Sub       │  │
│   │ (main.py)    │   │                        │   │  (Subscriber)        │  │
│   └──────────────┘   │  Key1 → Key2 → Key3   │   └──────────────────────┘  │
│                      │  ChatGoogle × N         │                             │
│                      └───────────┬─────────────┘                             │
│                                  │                                           │
│                      ┌───────────▼─────────────┐                             │
│                      │  browser-use Agent Loop  │                             │
│                      │  Screenshot → LLM → Act  │                             │
│                      └───────────┬─────────────┘                             │
│                                  │                                           │
│                      ┌───────────▼─────────────┐                             │
│                      │  Playwright (Chromium)   │                             │
│                      └─────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Communication Patterns

| Pattern | Technology | Direction | Purpose |
|---------|-----------|-----------|---------|
| **Job Queue** | BullMQ (Redis) | API → Worker | Dispatch browser automation tasks |
| **Webhooks** | HTTP POST | Worker → API | Real-time action logs & status updates |
| **Pub/Sub** | Redis Pub/Sub | API → Worker | Deliver OTP/CAPTCHA codes for HITL |
| **Polling** | HTTP GET (2s) | Frontend → API | Live dashboard updates |
| **Database** | PostgreSQL (Prisma) | API only | Job persistence & audit trail |

---

## 🛠 Tech Stack

<table>
<tr><th>Layer</th><th>Technology</th><th>Why This Choice</th></tr>
<tr>
  <td rowspan="5"><strong>Frontend</strong></td>
  <td>Next.js 15 (App Router)</td><td>Server-side rendering, API route proxying, React 19</td>
</tr>
<tr><td>Tailwind CSS v4</td><td>Utility-first, glassmorphism effects, zero-config</td></tr>
<tr><td>Lucide React</td><td>Tree-shakeable icons, consistent design</td></tr>
<tr><td>TypeScript 5.7+</td><td>Full type safety across the frontend</td></tr>
<tr><td>React 19</td><td>Latest concurrent features, use client components</td></tr>

<tr>
  <td rowspan="6"><strong>API Gateway</strong></td>
  <td>Node.js + Express</td><td>Fast I/O, mature ecosystem, TypeScript support</td>
</tr>
<tr><td>Prisma ORM 6.9+</td><td>Type-safe database access, auto-migrations</td></tr>
<tr><td>BullMQ 5.34+</td><td>Redis-backed job queue, retries, backoff</td></tr>
<tr><td>ioredis 5.6+</td><td>3 dedicated connections (queue, pub, sub)</td></tr>
<tr><td>Zod 3.24+</td><td>Runtime input validation on all endpoints</td></tr>
<tr><td>Helmet + Morgan</td><td>Security headers + HTTP logging</td></tr>

<tr>
  <td rowspan="6"><strong>Agent Worker</strong></td>
  <td>Python 3.11+</td><td>Async/await, type hints, browser-use compatibility</td>
</tr>
<tr><td>browser-use 0.13.8</td><td>LLM-powered browser automation framework</td></tr>
<tr><td>Gemini 3.6 Flash</td><td>Vision-capable, fast, structured output support</td></tr>
<tr><td>Playwright</td><td>Cross-browser automation (Chromium)</td></tr>
<tr><td>Pydantic 2.10+</td><td>Settings validation, data models</td></tr>
<tr><td>redis-py 5.2+</td><td>Pub/Sub for HITL communication</td></tr>

<tr>
  <td rowspan="2"><strong>Infrastructure</strong></td>
  <td>Redis 7+</td><td>Job queue (BullMQ) + HITL Pub/Sub messaging</td>
</tr>
<tr><td>PostgreSQL 15+</td><td>Persistent storage with relational integrity</td></tr>
</table>

---

## 🔑 Multi-Key Failover Rotation

One of the most **production-critical** features. Heavy web automation tasks can exhaust a single API key's rate limit. ActionPilot solves this with a `GeminiKeyPool`:

```
Request → Key 1 (5 internal retries with backoff)
               ↓ 429 Rate Limit
          Key 2 (5 internal retries with backoff)
               ↓ 429 Rate Limit
          Key 3 (5 internal retries with backoff)
               ↓ 429 Rate Limit
          Key 4 → Key 5 → ... → Error only if ALL keys exhausted
```

### How It Works

```python
class GeminiKeyPool:
    """Implements browser-use's BaseChatModel protocol with automatic key rotation."""

    async def ainvoke(self, messages, output_format, **kwargs):
        for attempt in range(len(self._clients)):      # Try each key
            try:
                return await client.ainvoke(...)         # ChatGoogle (5 internal retries)
            except rate_limit_error:
                logger.warning("🔄 Rate limit on Key %d → switching to Key %d", ...)
                self._rotate()                           # Switch to next key
                await asyncio.sleep(1.0)                 # Brief cooldown
        raise last_error                                 # All keys exhausted
```

### Configuration

```env
# .env — Add up to 5 keys for automatic failover
GEMINI_API_KEY_1=AIza...your-first-key
GEMINI_API_KEY_2=AIza...your-second-key
GEMINI_API_KEY_3=AIza...your-third-key
GEMINI_API_KEY_4=
GEMINI_API_KEY_5=
```

> **Math**: Each key gets 5 internal retries × 5 keys = **25 total attempts** with exponential backoff before the agent gives up.

---

## 📁 Project Structure

```
ActionPilot-AI/
│
├── frontend/                                 # Next.js 15 Dashboard
│   ├── app/
│   │   ├── layout.tsx                       # Root layout + global CSS
│   │   ├── page.tsx                         # Main dashboard (663→819 lines)
│   │   └── globals.css                      # Tailwind + glassmorphism + animations
│   ├── lib/
│   │   ├── api.ts                           # Typed API client functions
│   │   └── types.ts                         # Job, AuditLog, ApiResponse types
│   ├── next.config.ts                       # API proxy rewrites to :3001
│   ├── tailwind.config.ts                   # Dark theme configuration
│   └── package.json
│
├── api-backend/                              # Node.js TypeScript API Gateway
│   ├── prisma/
│   │   ├── schema.prisma                    # Job + AuditLog models
│   │   └── migrations/                      # Auto-generated SQL
│   └── src/
│       ├── index.ts                         # Express server + graceful shutdown
│       ├── config/
│       │   ├── env.ts                       # Zod-validated env vars
│       │   ├── prisma.ts                    # Singleton PrismaClient
│       │   └── redis.ts                     # 3× ioredis connections
│       ├── controllers/
│       │   ├── jobController.ts             # Job CRUD + OTP submission
│       │   └── webhookController.ts         # Receive logs from Python
│       ├── routes/
│       │   ├── jobRoutes.ts                 # /api/jobs/* routes
│       │   └── webhookRoutes.ts             # /api/webhooks/* routes
│       └── middleware/
│           └── errorHandler.ts              # Global error handler
│
├── agent-worker/                             # Python Agent Worker
│   └── src/
│       ├── config.py                        # Pydantic Settings (5 Gemini keys)
│       ├── agent_runner.py                  # GeminiKeyPool + browser-use Agent
│       ├── webhook_client.py                # HTTP client → API (with retry)
│       ├── hitl_handler.py                  # Redis Pub/Sub OTP listener
│       └── main.py                          # BullMQ Worker entry point
│
├── README.md                                 # ← You are here
└── LICENSE                                   # MIT License
```

---

## 🗄 Database Schema

```
┌──────────────────────────┐         ┌─────────────────────────────┐
│          jobs             │         │        audit_logs            │
├──────────────────────────┤         ├─────────────────────────────┤
│ id        UUID (PK)      │         │ id            UUID (PK)     │
│ prompt    TEXT            │◄────────│ job_id        UUID (FK)     │
│ status    ENUM            │   1:N   │ action_type   VARCHAR       │
│ result    JSONB (null)    │         │ description   TEXT          │
│ created   TIMESTAMP       │         │ screenshot    VARCHAR (null)│
│ updated   TIMESTAMP       │         │ timestamp     TIMESTAMP     │
└──────────────────────────┘         └─────────────────────────────┘
```

### Job Status State Machine

```
   PENDING ──────▶ RUNNING ──────▶ COMPLETED
                     │    ▲
                     │    │ OTP submitted
                     ▼    │
               PAUSED_FOR_HITL
                     │
                  (timeout)
                     ▼
                   FAILED
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Install |
|------------|---------|---------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Python | 3.11+ | [python.org](https://www.python.org/) |
| PostgreSQL | 15+ | `brew install postgresql@15` |
| Redis | 7+ | `brew install redis` |

### 1. Clone & Start Infrastructure

```bash
git clone https://github.com/Athar786-Ali/actionpilot-ai.git
cd actionpilot-ai

# Start Redis & PostgreSQL
brew services start redis
brew services start postgresql@15
```

### 2. API Backend

```bash
cd api-backend
npm install
cp .env.example .env          # Edit DATABASE_URL if needed
npx prisma generate
npx prisma migrate dev --name init
npm run dev                    # → http://localhost:3001
```

### 3. Agent Worker

```bash
cd agent-worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env           # Add your GEMINI_API_KEY_1 (get at aistudio.google.com/apikey)
python -m src.main             # → Listening on BullMQ queue
```

### 4. Frontend Dashboard

```bash
cd frontend
npm install
npm run dev                    # → http://localhost:3000
```

### 5. Try It

Open **http://localhost:3000**, type a prompt like:

> *"Go to google.com, search for 'best laptops 2026', and extract the top 5 results"*

Hit **Launch Agent** and watch the live execution console stream actions in real-time! 🚀

---

## 📡 API Reference

### Base URL: `http://localhost:3001`

#### `POST /api/jobs` — Create Job

```bash
curl -X POST http://localhost:3001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Go to amazon.in, search wireless headphones, extract top 5 with prices"}'
```

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PENDING"
  }
}
```

#### `GET /api/jobs/:id` — Poll Status & Logs

```json
{
  "success": true,
  "data": {
    "id": "550e8400-...",
    "status": "COMPLETED",
    "resultData": {
      "final_result": "1. Sony WH-1000XM5 — ₹24,990\n2. Samsung Galaxy Buds Pro — ₹12,990\n...",
      "total_actions": 12,
      "is_successful": true
    },
    "auditLogs": [
      { "actionType": "NAVIGATE", "description": "Navigated to https://amazon.in", "timestamp": "..." },
      { "actionType": "TYPE", "description": "Typed 'wireless headphones' into search", "timestamp": "..." },
      { "actionType": "CLICK", "description": "Clicked Search button", "timestamp": "..." }
    ]
  }
}
```

#### `POST /api/jobs/:id/submit-otp` — HITL OTP Submission

```bash
curl -X POST http://localhost:3001/api/jobs/{id}/submit-otp \
  -H "Content-Type: application/json" \
  -d '{"otp": "482916"}'
```

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/jobs` | POST | Create automation job |
| `/api/jobs/:id` | GET | Get status + audit logs |
| `/api/jobs/:id/submit-otp` | POST | Submit OTP (HITL) |
| `/api/webhooks/logs` | POST | Internal: receive worker logs |
| `/health` | GET | Health check |

---

## 🔄 Human-in-the-Loop (HITL) Deep Dive

The HITL mechanism is the most architecturally interesting feature. It enables the agent to **pause mid-execution**, wait for human input, and **resume exactly where it left off**.

### The Problem

Many web workflows involve security checkpoints:
- **OTP** — One-Time Password sent to phone/email
- **CAPTCHA** — reCAPTCHA, hCaptcha, image challenges
- **2FA** — Authenticator app codes
- **Email Verification** — Click-to-confirm links

An AI agent cannot solve these alone. It needs to *pause*, signal a human, and *wait*.

### The Solution — 7-Step Flow

```
 PYTHON WORKER                                    NODE.JS API
┌─────────────────┐                            ┌─────────────────┐
│                 │                            │                 │
│ 1. Agent sees   │   2. Webhook POST          │ 3. Update job   │
│    OTP field ──▶│──── PAUSED_FOR_HITL ─────▶│    status       │
│                 │                            │                 │
│ 4. SUBSCRIBE to │                            │                 │
│    Redis channel│                            │                 │
│    hitl:{jobId} │                            │                 │
│                 │                            │                 │
│    ⏳ WAITING   │                            │ 5. Human enters │
│    (up to 300s) │                            │    OTP on       │
│                 │   6. Redis PUBLISH         │    dashboard    │
│ 7. Receive OTP ◀│◀─── {otp: "482916"} ◀────│                 │
│    Type into    │                            │                 │
│    browser      │                            │                 │
│    Continue ──▶ │                            │                 │
└─────────────────┘                            └─────────────────┘
```

### Frontend HITL Modal

When the agent pauses, the dashboard automatically shows a sleek modal with a glowing alert icon, asking the user to enter their OTP. On submit, the code is published to Redis, and the agent resumes within milliseconds.

### Timeout Safety

If no human responds within `HITL_TIMEOUT_SECONDS` (default: 300s), the handler raises `HITLTimeoutError`, the job is marked `FAILED`, and a descriptive error is logged.

---

## 🧠 Agent Worker Internals

### The Agent Loop

```
┌────────────────────────────────────────────────────────────────┐
│                    AGENT LOOP  (per step)                       │
│                                                                │
│  1. 📸 Screenshot current browser page                         │
│  2. 🧠 Send screenshot + task + history → Gemini 3.6 Flash    │
│  3. 📋 LLM returns structured action(s):                      │
│         click(element)  |  type(text)  |  navigate(url)        │
│         scroll(dir)     |  done(result)                        │
│         ask_human_for_otp(reason)  ← custom HITL tool          │
│  4. ▶️  Execute action(s) via Playwright                       │
│  5. 📡 Log action via webhook → Node.js API                   │
│  6. 🔁 Repeat until done() or max steps                       │
└────────────────────────────────────────────────────────────────┘
```

### Key Implementation Details

| Feature | Implementation |
|---------|---------------|
| **LLM Wrapper** | `GeminiKeyPool` — implements `BaseChatModel` protocol, wraps N × `ChatGoogle` instances |
| **Step Logging** | `register_new_step_callback` — non-invasive hook, no monkey-patching |
| **HITL Tool** | `@controller.action(description=...)` — registered on `Tools` class |
| **OTP Wait** | `asyncio.run_in_executor()` → blocking Redis SUBSCRIBE in thread pool |
| **3 Redis Connections** | Queue consumer, Pub/Sub publisher, Pub/Sub subscriber (SUBSCRIBE blocks) |

---

## 📊 Sequence Diagram — Full Job Lifecycle

```
 Dashboard        API Gateway       PostgreSQL      Redis/BullMQ     Python Worker      Browser
    │                  │                │                │                │                │
    │ POST /api/jobs   │                │                │                │                │
    │─────────────────▶│ INSERT job     │                │                │                │
    │                  │───────────────▶│                │                │                │
    │                  │ Enqueue        │                │                │                │
    │                  │────────────────│───────────────▶│                │                │
    │ 201 {id}         │                │                │                │                │
    │◀─────────────────│                │                │ Consume job    │                │
    │                  │                │                │───────────────▶│                │
    │                  │ Webhook:       │                │                │ Launch Chrome  │
    │                  │ RUNNING        │                │                │───────────────▶│
    │                  │◀───────────────│────────────────│────────────────│                │
    │ Poll GET /jobs/id│                │                │                │                │
    │─────────────────▶│ SELECT job     │                │                │ Navigate       │
    │ {status, logs}   │◀──────────────│                │                │◀──────────────│
    │◀─────────────────│                │                │                │ Click, Type    │
    │                  │ Webhook: DONE  │                │                │◀──────────────│
    │                  │◀───────────────│────────────────│────────────────│                │
    │                  │ UPDATE result  │                │                │ Close browser  │
    │                  │───────────────▶│                │                │───────────────▶│
    │ Final poll       │                │                │                │                │
    │ {COMPLETED, data}│                │                │                │                │
    │◀─────────────────│                │                │                │                │
```

---

## ⚙️ Configuration Reference

### API Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `PORT` | `3001` | API server port |
| `WEBHOOK_SECRET` | — | Shared secret for worker→API webhooks |

### Agent Worker (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY_1` | — | **Required.** Primary Gemini API key |
| `GEMINI_API_KEY_2`…`5` | — | Optional. Additional keys for failover |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `WEBHOOK_URL` | `http://localhost:3001/api/webhooks/logs` | API webhook endpoint |
| `WEBHOOK_SECRET` | — | Must match API's `WEBHOOK_SECRET` |
| `BROWSER_HEADLESS` | `true` | Set `false` to see the browser |
| `HITL_TIMEOUT_SECONDS` | `300` | Max seconds to wait for human OTP |
| `BULLMQ_QUEUE_NAME` | `actionpilot_jobs` | Redis queue name |

---

## 🎨 Frontend — Dashboard UI

The frontend is a single-page Next.js 15 app with a premium dark-mode, glassmorphic aesthetic:

| Component | Description |
|-----------|-------------|
| **Hero Header** | Gradient title "ActionPilot AI" with animated badge and feature pills |
| **Command Center** | Textarea with `Enter` to launch, glow-on-focus border effect |
| **Live Execution Console** | Terminal-style log viewer — macOS dots, timeline dots, auto-scroll, 2s polling |
| **HITL Modal** | Glowing orange modal with OTP input — auto-triggers when agent pauses |
| **Mission Result Card** | Rich text rendering, numbered lists, status badges, collapsible raw details |

### Result Card Design

```
┌─────────────────────────────────────────────────────┐
│ ✅ Mission Result      [✓ Successful] [⚡ 12 Steps] │
├─────────────────────────────────────────────────────┤
│  ┌──┐                                               │
│  │1 │ Sony WH-1000XM5 — ₹24,990                    │
│  └──┘                                               │
│  ┌──┐                                               │
│  │2 │ Samsung Galaxy Buds Pro — ₹12,990             │
│  └──┘                                               │
│  ┌──┐                                               │
│  │3 │ JBL Tune 770NC — ₹4,999                      │
│  └──┘                                               │
├─────────────────────────────────────────────────────┤
│  ▸ View Raw Details  (errors, extracted_content)     │
└─────────────────────────────────────────────────────┘
```

---

## 🧩 Design Decisions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| **Decoupled Node.js + Python** | Node.js excels at I/O-heavy API serving; Python is required by `browser-use` and the ML ecosystem. Decoupling lets each scale independently. |
| **Redis for 3 purposes** | BullMQ queue, HITL Pub/Sub publisher, HITL Pub/Sub subscriber — requires 3 separate connections because `SUBSCRIBE` blocks. Single infrastructure component serves all IPC needs. |
| **Webhooks (Worker → API)** | Push-based: the worker POSTs logs as they happen. No polling delay. Retry-enabled with exponential backoff. |
| **Multi-key failover** | Gemini's free tier has low rate limits. Rather than upgrading to paid, 5 free keys give 5× throughput. The pool is transparent to the Agent — it just sees one LLM. |
| **browser-use native `ChatGoogle`** | Using the library's own LLM wrapper (`browser_use.llm.google.chat.ChatGoogle`) instead of LangChain ensures correct `BaseChatModel` protocol compliance and `ChatInvokeCompletion` return types. |
| **`register_new_step_callback`** | browser-use v0.13.8 provides this hook — cleaner than monkey-patching `Agent.step()`. |
| **PostgreSQL + Prisma** | Type-safe queries, auto-generated migrations, relational integrity for Job→AuditLog. JSONB column for flexible `resultData`. |
| **Next.js API rewrites** | Frontend proxies `/api/*` to `:3001` via `next.config.ts` rewrites — avoids CORS, simplifies deployment. |

---

## 🛡 Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **API Input** | Zod schema validation on all request bodies — rejects malformed input before processing |
| **Job Queue** | BullMQ retries with exponential backoff — failed jobs are retried before marking FAILED |
| **Agent Runner** | `try/except` with full traceback logging — errors are captured in `resultData.errors` |
| **Webhook Client** | Retry with backoff (3 attempts) — network failures don't crash the agent |
| **HITL Timeout** | Configurable timeout (300s default) — prevents indefinite blocking |
| **Step Logging** | `try/except` in callback — logging failures never crash the agent loop |
| **Multi-Key** | Rate limit on Key N → automatic rotation to Key N+1 with 1s cooldown |
| **Browser Cleanup** | `finally` block always closes `BrowserSession` — prevents zombie Chromium processes |

---

## 📈 Scaling Considerations

| Dimension | Current (Dev) | Production Path |
|-----------|--------------|-----------------|
| **Workers** | 1 process | N workers consuming same BullMQ queue (horizontal scale) |
| **API** | Single Express | PM2 cluster mode or Kubernetes deployment |
| **Database** | Local PostgreSQL | Managed PostgreSQL (RDS, Cloud SQL) with connection pooling |
| **Redis** | Local Redis | Redis Cluster or managed Redis (ElastiCache, Upstash) |
| **LLM Keys** | 1-5 free keys | Paid Gemini API with higher rate limits |
| **Browser** | Local Chromium | Remote browser grid (Browserless, Playwright Grid) |
| **Frontend** | Local Next.js dev | Vercel deployment with edge functions |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Athar Ali](https://github.com/Athar786-Ali)**

*ActionPilot AI — Because web automation should be as simple as describing what you want.*

</div>

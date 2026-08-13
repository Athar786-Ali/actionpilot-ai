<div align="center">

# 🤖 ActionPilot AI

### Enterprise-Grade Autonomous Web Automation Platform

*An asynchronous, event-driven orchestration layer over `browser-use` — enabling LLM-powered browser agents that can navigate, interact, and complete complex web tasks with human-in-the-loop support.*

[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=for-the-badge&logo=node.js&logoColor=white)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Gemini](https://img.shields.io/badge/Gemini_2.0_Flash-LLM-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

**[Architecture](#-system-architecture) · [Quick Start](#-quick-start) · [API Reference](#-api-reference) · [HITL Flow](#-human-in-the-loop-hitl-deep-dive) · [Project Structure](#-project-structure)**

</div>

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Human-in-the-Loop (HITL) Deep Dive](#-human-in-the-loop-hitl-deep-dive)
- [Agent Worker Internals](#-agent-worker-internals)
- [Sequence Diagrams](#-sequence-diagrams)
- [Configuration Reference](#-configuration-reference)
- [Design Decisions & Trade-offs](#-design-decisions--trade-offs)
- [Error Handling Strategy](#-error-handling-strategy)
- [Scaling Considerations](#-scaling-considerations)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Problem Statement

Modern enterprise workflows often require automating complex, multi-step interactions with web applications — filling forms, navigating dashboards, extracting data, or completing transactions. These tasks traditionally demand brittle RPA scripts that break with every UI change.

**Key challenges:**
- Web UIs change frequently, breaking hardcoded selectors and scripts
- Many workflows require human intervention (OTP, CAPTCHA, 2FA)
- Browser automation at scale requires robust job queuing and failure recovery
- Real-time visibility into what the agent is doing is critical for trust and debugging

---

## 💡 Solution Overview

**ActionPilot AI** solves this by combining:

1. **LLM-Powered Browser Agents** — Instead of brittle selectors, a Google Gemini 2.0 Flash model *sees* the page (via vision) and *reasons* about what to click, type, and navigate. The agent adapts to UI changes automatically.

2. **Decoupled Microservices Architecture** — A Node.js API Gateway handles client requests, job persistence, and audit logging. A Python Agent Worker handles browser automation. They communicate asynchronously via Redis (BullMQ + Pub/Sub) and Webhooks.

3. **Human-in-the-Loop (HITL)** — When the agent encounters an OTP field, CAPTCHA, or any verification that requires a human, it *pauses execution*, alerts the API, and *waits* for the human to submit the code — then seamlessly resumes.

4. **Full Audit Trail** — Every browser action (click, type, navigate) is logged in real-time to PostgreSQL via webhooks, providing complete observability into agent behavior.

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATION                              │
│                    (Web Dashboard / API Consumer)                        │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                    POST /api/jobs { prompt }
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    NODE.JS API GATEWAY (Express + TypeScript)            │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ Job Routes   │  │ Webhook      │  │ HITL Endpoint  │  │ Health    │ │
│  │ POST /jobs   │  │ POST /logs   │  │ POST /submit-  │  │ GET /     │ │
│  │ GET /jobs/:id│  │ (from Python)│  │   otp          │  │  health   │ │
│  └──────┬───────┘  └──────▲───────┘  └───────┬────────┘  └───────────┘ │
│         │                 │                   │                          │
│         ▼                 │                   ▼                          │
│  ┌──────────────┐         │           ┌────────────────┐                │
│  │   Prisma ORM │         │           │ Redis Pub/Sub  │                │
│  │ (PostgreSQL) │         │           │  (Publisher)   │                │
│  └──────┬───────┘         │           └───────┬────────┘                │
│         │                 │                   │                          │
│         ▼                 │                   │ PUBLISH otp              │
│  ┌──────────────┐         │                   │                          │
│  │   BullMQ     │         │                   │                          │
│  │ (Job Queue)  │         │                   │                          │
│  └──────┬───────┘         │                   │                          │
└─────────┼─────────────────┼───────────────────┼──────────────────────────┘
          │                 │                   │
          │ ENQUEUE         │ HTTP POST         │ Redis Pub/Sub
          │ {jobId, prompt} │ (webhook)         │
          ▼                 │                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PYTHON AGENT WORKER (browser-use + Gemini)             │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐                │
│  │ BullMQ       │  │ Agent Runner │  │ HITL Handler   │                │
│  │ Consumer     │──▶ browser-use  │──▶ Redis Pub/Sub  │                │
│  │ (main.py)    │  │ + Gemini LLM │  │ (Subscriber)   │                │
│  └──────────────┘  └──────┬───────┘  └────────────────┘                │
│                           │                                             │
│                    ┌──────▼───────┐                                     │
│                    │  Playwright  │                                     │
│                    │  (Chromium)  │                                     │
│                    └──────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Communication Patterns

| Pattern | Technology | Direction | Purpose |
|---------|-----------|-----------|---------|
| **Job Queue** | BullMQ (Redis) | API → Worker | Dispatch browser automation tasks |
| **Webhooks** | HTTP POST | Worker → API | Real-time action logs & status updates |
| **Pub/Sub** | Redis Pub/Sub | API → Worker | Deliver OTP/CAPTCHA codes for HITL |
| **Database** | PostgreSQL (Prisma) | API only | Job persistence & audit trail |

---

## 🛠 Tech Stack

### API Gateway (`/api-backend`)

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Node.js** | 18+ | Runtime environment |
| **TypeScript** | 5.7+ | Strict type-safe codebase |
| **Express.js** | 4.21+ | HTTP server & routing |
| **Prisma ORM** | 6.9+ | Type-safe database access with migrations |
| **PostgreSQL** | 15+ | Persistent storage for jobs & audit logs |
| **BullMQ** | 5.34+ | Redis-backed distributed job queue |
| **ioredis** | 5.6+ | Redis client (3 dedicated connections) |
| **Zod** | 3.24+ | Runtime schema validation on all inputs |
| **Helmet** | 8.1+ | HTTP security headers |
| **Morgan** | 1.10+ | HTTP request logging |

### Agent Worker (`/agent-worker`)

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Runtime environment |
| **browser-use** | 0.2+ | LLM-powered browser automation framework |
| **Playwright** | 1.49+ | Cross-browser automation (Chromium) |
| **LangChain** | 0.3+ | LLM orchestration framework |
| **Google Gemini 2.0 Flash** | — | Vision-capable LLM for page understanding |
| **BullMQ (Python)** | 1.5+ | Queue consumer (compatible with Node.js BullMQ) |
| **redis-py** | 5.2+ | Redis Pub/Sub for HITL communication |
| **Pydantic** | 2.10+ | Settings validation & data models |
| **Requests** | 2.32+ | HTTP client with retry logic for webhooks |

### Infrastructure

| Technology | Purpose |
|-----------|---------|
| **Redis 7+** | Job queue (BullMQ) + HITL Pub/Sub messaging |
| **PostgreSQL 15+** | Persistent storage with relational integrity |
| **Docker** | Containerization (optional) |

---

## 📁 Project Structure

```
ActionPilot-AI/
│
├── api-backend/                          # Node.js TypeScript API Gateway
│   ├── .env.example                      # Environment variable template
│   ├── package.json                      # Dependencies & npm scripts
│   ├── tsconfig.json                     # Strict TypeScript configuration
│   │
│   ├── prisma/
│   │   ├── schema.prisma                 # Database schema (Job + AuditLog)
│   │   └── migrations/                   # Auto-generated SQL migrations
│   │
│   └── src/
│       ├── index.ts                      # Express server bootstrap + graceful shutdown
│       │
│       ├── config/
│       │   ├── env.ts                    # Zod-validated environment variables
│       │   ├── prisma.ts                 # Singleton PrismaClient (hot-reload safe)
│       │   └── redis.ts                  # 3× ioredis connections (main, pub, sub)
│       │
│       ├── types/
│       │   └── index.ts                  # All TypeScript interfaces & type definitions
│       │
│       ├── controllers/
│       │   ├── jobController.ts          # POST /jobs, GET /jobs/:id, POST /submit-otp
│       │   └── webhookController.ts      # POST /webhooks/logs (receives from Python)
│       │
│       ├── routes/
│       │   ├── jobRoutes.ts              # /api/jobs/* route definitions
│       │   └── webhookRoutes.ts          # /api/webhooks/* route definitions
│       │
│       ├── middleware/
│       │   └── errorHandler.ts           # Global error handler (env-aware)
│       │
│       └── workers/
│           └── jobQueue.ts               # BullMQ queue initialization + config
│
├── agent-worker/                         # Python Agentic Browser Worker
│   ├── .env.example                      # Environment variable template
│   ├── requirements.txt                  # Python dependencies
│   │
│   └── src/
│       ├── __init__.py                   # Package marker
│       ├── config.py                     # Pydantic Settings + logging setup
│       ├── webhook_client.py             # HTTP client → Node.js API (with retry)
│       ├── hitl_handler.py               # Redis Pub/Sub OTP listener (blocking)
│       ├── agent_runner.py               # browser-use + Gemini agent + HITL tool
│       └── main.py                       # BullMQ Worker entry point
│
└── README.md                             # ← You are here
```

---

## 🗄 Database Schema

The PostgreSQL database uses two tables managed by Prisma ORM:

### Entity Relationship Diagram

```
┌───────────────────────────────┐       ┌───────────────────────────────────┐
│            jobs               │       │           audit_logs              │
├───────────────────────────────┤       ├───────────────────────────────────┤
│ id          UUID (PK)         │       │ id              UUID (PK)        │
│ prompt      TEXT              │◄──────│ job_id          UUID (FK)        │
│ status      JobStatus (ENUM)  │  1:N  │ action_type     VARCHAR          │
│ result_data JSONB (nullable)  │       │ screenshot_url  VARCHAR (null)   │
│ created_at  TIMESTAMP         │       │ description     TEXT             │
│ updated_at  TIMESTAMP         │       │ timestamp       TIMESTAMP        │
└───────────────────────────────┘       └───────────────────────────────────┘
```

### Job Status State Machine

```
                ┌──────────┐
                │ PENDING  │ ← Job created, queued in BullMQ
                └────┬─────┘
                     │ Worker picks up job
                     ▼
                ┌──────────┐
            ┌──│ RUNNING  │──┐
            │  └──────────┘  │
            │                │ Agent detects OTP/CAPTCHA
            │                ▼
            │  ┌───────────────────┐
            │  │ PAUSED_FOR_HITL   │ ← Waiting for human input
            │  └────────┬──────────┘
            │           │ Human submits OTP
            │           ▼
            │  ┌──────────┐
            │  │ RUNNING  │ ← Agent resumes
            │  └────┬─────┘
            │       │
            ▼       ▼
    ┌──────────┐  ┌───────────┐
    │  FAILED  │  │ COMPLETED │
    └──────────┘  └───────────┘
```

### Prisma Schema

```prisma
enum JobStatus {
  PENDING
  RUNNING
  PAUSED_FOR_HITL
  COMPLETED
  FAILED
}

model Job {
  id          String    @id @default(uuid())
  prompt      String
  status      JobStatus @default(PENDING)
  resultData  Json?     @map("result_data")
  createdAt   DateTime  @default(now()) @map("created_at")
  updatedAt   DateTime  @updatedAt @map("updated_at")
  auditLogs   AuditLog[]
  @@map("jobs")
}

model AuditLog {
  id            String   @id @default(uuid())
  jobId         String   @map("job_id")
  actionType    String   @map("action_type")
  screenshotUrl String?  @map("screenshot_url")
  description   String
  timestamp     DateTime @default(now())
  job           Job      @relation(fields: [jobId], references: [id], onDelete: Cascade)
  @@index([jobId])
  @@map("audit_logs")
}
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Installation |
|------------|---------|-------------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Python | 3.11+ | [python.org](https://www.python.org/) |
| PostgreSQL | 15+ | `brew install postgresql@15` |
| Redis | 7+ | `brew install redis` |

### Step 1: Clone the Repository

```bash
git clone https://github.com/Athar786-Ali/actionpilot-ai.git
cd actionpilot-ai
```

### Step 2: Start Infrastructure Services

```bash
# Start PostgreSQL (if not already running)
brew services start postgresql@15

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

### Step 3: Setup the API Backend

```bash
cd api-backend

# Install Node.js dependencies
npm install

# Copy and configure environment variables
cp .env.example .env
# Edit .env → set your DATABASE_URL if different from default

# Generate Prisma client
npx prisma generate

# Run database migrations
npx prisma migrate dev --name init

# Start the API server (development mode with hot-reload)
npm run dev
```

You should see:
```
╔══════════════════════════════════════════════╗
║   🤖 ActionPilot AI — API Gateway           ║
║   🌐 http://localhost:3001                   ║
║   📋 Environment: development               ║
╚══════════════════════════════════════════════╝
```

### Step 4: Setup the Agent Worker

```bash
# Open a new terminal
cd agent-worker

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

# Copy and configure environment variables
cp .env.example .env
# Edit .env → set GEMINI_API_KEY to your actual Google Gemini API key

# Start the worker
python -m src.main
```

You should see:
```
╔══════════════════════════════════════════════╗
║   🤖 ActionPilot AI — Agent Worker           ║
║   📡 Queue: actionpilot:jobs                 ║
║   🔗 Redis: localhost:6379                   ║
╚══════════════════════════════════════════════╝
🟢 Worker started, waiting for jobs...
```

### Step 5: Submit Your First Job

```bash
curl -X POST http://localhost:3001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Go to google.com and search for ActionPilot AI"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "prompt": "Go to google.com and search for ActionPilot AI",
    "status": "PENDING",
    "resultData": null,
    "createdAt": "2026-08-13T12:00:00.000Z",
    "updatedAt": "2026-08-13T12:00:00.000Z"
  }
}
```

---

## 📡 API Reference

### Base URL: `http://localhost:3001`

---

### `POST /api/jobs` — Create Automation Job

Submit a natural language task for the browser agent to execute.

**Request:**
```http
POST /api/jobs
Content-Type: application/json

{
  "prompt": "Go to amazon.in, search for 'wireless headphones', and extract the top 5 results with prices"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "Go to amazon.in, search for 'wireless headphones'...",
    "status": "PENDING",
    "resultData": null,
    "createdAt": "2026-08-13T17:50:00.000Z",
    "updatedAt": "2026-08-13T17:50:00.000Z"
  }
}
```

**Validation Rules:**
| Field | Type | Constraints |
|-------|------|------------|
| `prompt` | `string` | Required, 1–4096 characters |

---

### `GET /api/jobs/:id` — Get Job Status & Audit Logs

Retrieve a job's current status along with its complete audit trail.

**Request:**
```http
GET /api/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "Go to amazon.in, search for 'wireless headphones'...",
    "status": "COMPLETED",
    "resultData": {
      "final_result": "Found 5 products: ...",
      "total_actions": 12
    },
    "createdAt": "2026-08-13T17:50:00.000Z",
    "updatedAt": "2026-08-13T17:50:45.000Z",
    "auditLogs": [
      {
        "id": "log-uuid-1",
        "jobId": "550e8400-...",
        "actionType": "JOB_STARTED",
        "screenshotUrl": null,
        "description": "Agent worker has picked up the job and started execution",
        "timestamp": "2026-08-13T17:50:02.000Z"
      },
      {
        "id": "log-uuid-2",
        "jobId": "550e8400-...",
        "actionType": "NAVIGATE",
        "screenshotUrl": null,
        "description": "Navigated to https://amazon.in",
        "timestamp": "2026-08-13T17:50:05.000Z"
      },
      {
        "id": "log-uuid-3",
        "jobId": "550e8400-...",
        "actionType": "TYPE",
        "screenshotUrl": null,
        "description": "Typed 'wireless headphones' into search field",
        "timestamp": "2026-08-13T17:50:10.000Z"
      }
    ]
  }
}
```

---

### `POST /api/jobs/:id/submit-otp` — Submit OTP (Human-in-the-Loop)

When an agent is paused waiting for human input (status = `PAUSED_FOR_HITL`), use this endpoint to submit the OTP/verification code.

**Request:**
```http
POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/submit-otp
Content-Type: application/json

{
  "otp": "482916"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "OTP submitted and published to worker"
  }
}
```

**Error Cases:**
| HTTP Status | Scenario |
|-------------|----------|
| `404` | Job not found |
| `409` | Job is not in `PAUSED_FOR_HITL` status |
| `400` | Invalid or missing OTP |

---

### `POST /api/webhooks/logs` — Receive Agent Logs (Internal)

Receives real-time action logs from the Python Agent Worker. This is an **internal endpoint** authenticated via the `x-webhook-secret` header.

**Request:**
```http
POST /api/webhooks/logs
Content-Type: application/json
x-webhook-secret: your-webhook-secret-key

{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "actionType": "CLICK",
  "description": "Clicked 'Search' button",
  "screenshotUrl": "https://storage.example.com/screenshot.png",
  "status": "RUNNING"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "logId": "audit-log-uuid"
  }
}
```

---

### `GET /health` — Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "service": "actionpilot-api-backend",
  "timestamp": "2026-08-13T17:50:00.000Z"
}
```

---

## 🔄 Human-in-the-Loop (HITL) Deep Dive

The HITL mechanism is the most architecturally interesting feature of ActionPilot AI. It enables the agent to **pause mid-execution**, wait for human input, and **resume exactly where it left off**.

### Why HITL is Needed

Many web automation workflows involve security checkpoints:
- **OTP (One-Time Password)** — Sent to the user's phone/email
- **CAPTCHA** — reCAPTCHA, hCaptcha, image selection challenges
- **Two-Factor Authentication (2FA)** — Authenticator app codes
- **Email Verification** — Click-to-confirm links

These cannot be solved by the LLM alone. The agent needs to *pause*, signal a human, and *wait*.

### HITL Architecture

```
                        PYTHON WORKER                          NODE.JS API
                     ┌─────────────────┐                  ┌─────────────────┐
                     │                 │                  │                 │
  1. Agent detects   │  browser-use    │   2. Webhook     │  Express        │
     OTP field  ───▶ │  invokes tool:  │ ──────────────▶  │  updates job    │
                     │  ask_human_otp  │   PAUSED_FOR_    │  status to      │
                     │                 │   HITL           │  PAUSED_FOR_    │
                     │  3. Subscribe   │                  │  HITL           │
                     │  to Redis       │                  │                 │
                     │  channel:       │                  │                 │
                     │  actionpilot:   │                  │                 │
                     │  hitl:{jobId}   │                  │                 │
                     │                 │                  │                 │
                     │  ⏳ BLOCKING    │                  │                 │
                     │  WAIT...        │                  │                 │
                     │                 │                  │                 │
                     │                 │   5. Redis       │  4. Human       │
                     │  6. Receive OTP │ ◀────────────── │  submits OTP    │
                     │  from Pub/Sub   │   PUBLISH        │  via POST       │
                     │                 │   {otp: "123"}   │  /submit-otp    │
                     │  7. Type OTP    │                  │                 │
                     │  into browser   │                  │                 │
                     │  & continue     │                  │                 │
                     └─────────────────┘                  └─────────────────┘
```

### Implementation Details

**Step 1 — Detection:** The LLM (Gemini 2.0 Flash with vision) sees the page screenshot and recognizes an OTP/verification prompt. It decides to invoke the custom `ask_human_for_otp` tool registered on the `browser-use` Controller.

**Step 2 — Webhook Notification:** The tool fires an HTTP POST to the Node.js API:
```json
{
  "jobId": "...",
  "actionType": "HITL_REQUESTED",
  "description": "Agent paused for human input: OTP required",
  "status": "PAUSED_FOR_HITL"
}
```

**Step 3 — Redis Subscribe:** A dedicated Redis connection (separate from BullMQ) subscribes to the channel `actionpilot:hitl:{jobId}` using a background thread with a configurable timeout (default: 300 seconds).

**Step 4 — Human Submits OTP:** A human operator (or external system) calls `POST /api/jobs/:id/submit-otp` with the OTP.

**Step 5 — Redis Publish:** The Node.js API publishes the OTP to Redis:
```json
{
  "jobId": "...",
  "otp": "482916",
  "timestamp": "2026-08-13T17:55:00.000Z"
}
```

**Step 6 — Receive & Resume:** The Python worker's background thread receives the message, parses the OTP, and returns it to the `ask_human_for_otp` tool.

**Step 7 — Continue Execution:** The LLM receives the OTP string as the tool's return value and types it into the appropriate browser field. The agent loop continues.

### Timeout Handling

If no human responds within `HITL_TIMEOUT_SECONDS` (default 300s), the HITL handler raises `HITLTimeoutError`, the job is marked as `FAILED`, and a descriptive error is logged to the audit trail.

---

## 🧠 Agent Worker Internals

### How `browser-use` Works with Gemini

```
┌────────────────────────────────────────────────────────────┐
│                    AGENT LOOP (per step)                    │
│                                                            │
│  1. Take screenshot of current browser page                │
│  2. Send screenshot + task + history → Gemini 2.0 Flash    │
│  3. LLM returns structured action(s):                      │
│     • click(selector)                                      │
│     • type(selector, text)                                 │
│     • navigate(url)                                        │
│     • scroll(direction)                                    │
│     • ask_human_for_otp(reason)  ← custom HITL tool        │
│     • done(result)                                         │
│  4. Execute action(s) via Playwright                       │
│  5. Log action via webhook → Node.js API                   │
│  6. Repeat until done() or max steps                       │
└────────────────────────────────────────────────────────────┘
```

### Custom Controller Action Registration

The `ask_human_for_otp` tool is registered on the `browser-use` Controller, making it available to the LLM as a callable function:

```python
@controller.action(
    description=(
        "Use this tool when you encounter an OTP input field, CAPTCHA, "
        "two-factor authentication prompt, or any verification screen "
        "that requires a code from the human user."
    ),
)
async def ask_human_for_otp(reason: str = "OTP or verification code required") -> str:
    # 1. Notify API → PAUSED_FOR_HITL
    webhook.send_status_paused_for_hitl(job_id, reason)
    
    # 2. Block until human submits OTP via Redis Pub/Sub
    otp = await asyncio.get_event_loop().run_in_executor(
        None, wait_for_human_input, job_id
    )
    
    # 3. Return OTP to LLM → it types into the browser
    return otp
```

### Action Logging via Step Instrumentation

Every agent step is instrumented to POST action details to the Node.js webhook endpoint. This is done by wrapping `Agent.step()`:

```python
original_step = agent.step

async def _instrumented_step(*args, **kwargs):
    result = await original_step(*args, **kwargs)
    # Extract action details and POST to webhook
    webhook.send_agent_action(job_id, action_type, description)
    return result

agent.step = _instrumented_step
```

This provides **real-time observability** without modifying the `browser-use` library's internals.

---

## 📊 Sequence Diagrams

### Normal Job Execution (Happy Path)

```
Client          API Gateway         Redis/BullMQ        Python Worker       Browser
  │                  │                    │                    │                │
  │ POST /api/jobs   │                    │                    │                │
  │ {prompt: "..."}  │                    │                    │                │
  │─────────────────▶│                    │                    │                │
  │                  │ Save to PostgreSQL │                    │                │
  │                  │ Enqueue to BullMQ  │                    │                │
  │                  │───────────────────▶│                    │                │
  │  201 {id, status}│                    │                    │                │
  │◀─────────────────│                    │                    │                │
  │                  │                    │ Job consumed       │                │
  │                  │                    │───────────────────▶│                │
  │                  │  Webhook: RUNNING  │                    │                │
  │                  │◀───────────────────│────────────────────│                │
  │                  │                    │                    │ Launch Chromium │
  │                  │                    │                    │───────────────▶│
  │                  │                    │                    │                │
  │                  │  Webhook: NAVIGATE │                    │  Navigate      │
  │                  │◀───────────────────│────────────────────│◀──────────────│
  │                  │                    │                    │                │
  │                  │  Webhook: CLICK    │                    │  Click         │
  │                  │◀───────────────────│────────────────────│◀──────────────│
  │                  │                    │                    │                │
  │                  │  Webhook: TYPE     │                    │  Type text     │
  │                  │◀───────────────────│────────────────────│◀──────────────│
  │                  │                    │                    │                │
  │                  │ Webhook: COMPLETED │                    │ Close browser  │
  │                  │◀───────────────────│────────────────────│───────────────▶│
  │                  │                    │                    │                │
  │ GET /api/jobs/:id│                    │                    │                │
  │─────────────────▶│                    │                    │                │
  │  200 {COMPLETED} │                    │                    │                │
  │◀─────────────────│                    │                    │                │
```

### HITL Flow (OTP Required)

```
Client          API Gateway         Redis Pub/Sub       Python Worker       Browser
  │                  │                    │                    │                │
  │                  │                    │                    │ Agent detects  │
  │                  │                    │                    │ OTP field      │
  │                  │                    │                    │◀──────────────│
  │                  │                    │                    │                │
  │                  │  Webhook:          │                    │ Invoke tool:   │
  │                  │  PAUSED_FOR_HITL   │                    │ ask_human_otp  │
  │                  │◀───────────────────│────────────────────│                │
  │                  │                    │                    │                │
  │                  │                    │ SUBSCRIBE          │                │
  │                  │                    │ actionpilot:hitl:  │                │
  │                  │                    │ {jobId}            │                │
  │                  │                    │◀───────────────────│                │
  │                  │                    │                    │                │
  │                  │                    │                    │ ⏳ Blocking    │
  │                  │                    │                    │    wait...     │
  │                  │                    │                    │                │
  │ GET /api/jobs/:id│                    │                    │                │
  │─────────────────▶│                    │                    │                │
  │ 200 {PAUSED_FOR_ │                    │                    │                │
  │     HITL}        │                    │                    │                │
  │◀─────────────────│                    │                    │                │
  │                  │                    │                    │                │
  │ POST /submit-otp │                    │                    │                │
  │ {otp: "482916"}  │                    │                    │                │
  │─────────────────▶│                    │                    │                │
  │                  │ Update: RUNNING    │                    │                │
  │                  │ PUBLISH otp        │                    │                │
  │                  │───────────────────▶│                    │                │
  │  200 {submitted} │                    │                    │                │
  │◀─────────────────│                    │ Deliver OTP        │                │
  │                  │                    │───────────────────▶│                │
  │                  │                    │                    │                │
  │                  │                    │                    │ Type OTP       │
  │                  │                    │                    │───────────────▶│
  │                  │                    │                    │                │
  │                  │                    │                    │ Continue agent │
  │                  │                    │                    │ loop...        │
```

---

## ⚙ Configuration Reference

### API Backend Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `3001` | Express server port |
| `NODE_ENV` | No | `development` | Environment: `development`, `production`, `test` |
| `DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `REDIS_HOST` | No | `localhost` | Redis server hostname |
| `REDIS_PORT` | No | `6379` | Redis server port |
| `REDIS_PASSWORD` | No | *(empty)* | Redis authentication password |
| `BULLMQ_QUEUE_NAME` | No | `actionpilot:jobs` | BullMQ queue name (must match worker) |
| `REDIS_HITL_CHANNEL_PREFIX` | No | `actionpilot:hitl:` | Redis Pub/Sub channel prefix |
| `WEBHOOK_SECRET` | No | `your-webhook-secret-key` | Shared secret for webhook auth |

### Agent Worker Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | No | `localhost` | Redis server hostname |
| `REDIS_PORT` | No | `6379` | Redis server port |
| `REDIS_PASSWORD` | No | *(empty)* | Redis authentication password |
| `GEMINI_API_KEY` | **Yes** | — | Google Gemini API key ([Get one here](https://aistudio.google.com/apikey)) |
| `WEBHOOK_URL` | No | `http://localhost:3001/api/webhooks/logs` | Node.js webhook endpoint |
| `WEBHOOK_SECRET` | No | `your-webhook-secret-key` | Must match API backend's value |
| `BULLMQ_QUEUE_NAME` | No | `actionpilot:jobs` | Must match API backend's queue name |
| `REDIS_HITL_CHANNEL_PREFIX` | No | `actionpilot:hitl:` | Must match API backend's prefix |
| `HITL_TIMEOUT_SECONDS` | No | `300` | Seconds to wait for human OTP input |
| `BROWSER_HEADLESS` | No | `true` | Run Chromium in headless mode |

### Shared Configuration Contract

> ⚠️ **Critical:** The following values **must be identical** across both services:

| Config Key | Shared Value |
|-----------|--------------|
| `BULLMQ_QUEUE_NAME` | `actionpilot:jobs` |
| `REDIS_HITL_CHANNEL_PREFIX` | `actionpilot:hitl:` |
| `WEBHOOK_SECRET` | *(your chosen secret)* |
| Redis host/port | *(same Redis instance)* |

---

## 🧩 Design Decisions & Trade-offs

### 1. Why Two Separate Services (Node.js + Python)?

| Decision | Rationale |
|----------|-----------|
| **Node.js for API** | Superior async I/O for handling HTTP requests. Rich ecosystem for Express, Prisma, BullMQ. TypeScript provides compile-time safety. |
| **Python for Agent** | `browser-use` and `langchain` are Python-native. The ML/AI ecosystem (LangChain, Playwright bindings) is strongest in Python. |
| **Redis as bridge** | BullMQ has first-class support in both Node.js and Python. Redis Pub/Sub provides low-latency, exactly-once delivery for HITL. |

### 2. Why 3 Separate Redis Connections?

```
Connection 1 (redisConnection) → BullMQ queue operations
Connection 2 (redisPublisher)  → HITL Pub/Sub PUBLISH
Connection 3 (redisSubscriber) → HITL Pub/Sub SUBSCRIBE
```

**Rationale:** Redis Pub/Sub SUBSCRIBE blocks the connection — no other commands can be sent on a subscribed connection. BullMQ also requires its own dedicated connection. Hence, 3 connections are the minimum for correct operation.

### 3. Why Webhooks Instead of Direct DB Access?

| Option | Pros | Cons |
|--------|------|------|
| **Webhooks ✅** | Decoupled services; Python doesn't need Prisma/PostgreSQL driver; language-agnostic; API validates all writes | Extra HTTP hop; slight latency |
| Direct DB access | Lower latency | Tight coupling; duplicated ORM logic; bypasses API validation |

We chose webhooks for **clean service boundaries** — the Python worker is a pure consumer that only needs Redis and HTTP.

### 4. Why BullMQ Over Celery or RabbitMQ?

| Queue System | Why Not |
|-------------|---------|
| **Celery** | Python-only; wouldn't integrate with the Node.js API |
| **RabbitMQ** | Additional infrastructure; BullMQ gives us queue + Pub/Sub on the same Redis instance |
| **BullMQ ✅** | First-class Node.js + Python SDKs; built on Redis (already needed for Pub/Sub); exponential backoff retries; job lifecycle events |

### 5. Why Gemini 2.0 Flash?

| Feature | Benefit |
|---------|---------|
| **Vision capability** | Can see and understand page screenshots — critical for browser-use |
| **Speed** | "Flash" variant is optimized for low-latency responses (~1-2s per step) |
| **Cost** | Significantly cheaper than GPT-4 Vision or Claude for high-volume automation |
| **Context window** | 1M tokens — can handle long browsing sessions with full history |

---

## 🛡 Error Handling Strategy

### API Gateway

| Layer | Mechanism |
|-------|-----------|
| **Input Validation** | Zod schemas on every endpoint — rejects malformed requests before they hit business logic |
| **Controller Layer** | try/catch → `next(err)` pattern delegates to global error handler |
| **Global Error Handler** | Returns stack traces in development, generic message in production |
| **Webhook Auth** | `x-webhook-secret` header validation — rejects unauthenticated webhook calls |

### Agent Worker

| Layer | Mechanism |
|-------|-----------|
| **Config Validation** | Pydantic Settings rejects missing/invalid env vars at startup |
| **Webhook Client** | 3× automatic retries with exponential backoff on 502/503/504 |
| **HITL Timeout** | Configurable timeout (default 300s) → `HITLTimeoutError` → job marked FAILED |
| **Agent Execution** | try/catch around `agent.run()` → FAILED webhook with stack trace |
| **Browser Cleanup** | `finally` block ensures `browser.close()` is always called |
| **Action Logging** | Wrapped in try/catch — logging failures never crash the agent |
| **BullMQ Retries** | Failed jobs are re-raised so BullMQ can retry (3× with exponential backoff) |

---

## 📈 Scaling Considerations

### Current Design (Single Worker)

The current architecture processes **one browser session at a time** (`concurrency: 1`). This is intentional — each Chromium instance consumes ~200-500MB RAM.

### Horizontal Scaling Path

```
                    ┌─────────────────┐
                    │   Load Balancer  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ API Pod 1│  │ API Pod 2│  │ API Pod 3│
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                    ┌──────────────┐
                    │ Redis Cluster│
                    │ (BullMQ +    │
                    │  Pub/Sub)    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Worker 1 │ │ Worker 2 │ │ Worker 3 │
        │ (1 browser│ │ (1 browser│ │(1 browser│
        │  session) │ │  session) │ │ session) │
        └──────────┘ └──────────┘ └──────────┘
```

**Key scaling strategies:**
- **Multiple worker processes** — BullMQ automatically distributes jobs across workers
- **Redis Cluster** — For Pub/Sub and queue at scale
- **PostgreSQL connection pooling** — PgBouncer or Prisma Accelerate
- **Kubernetes** — Each worker pod gets its own Chromium instance
- **Screenshot storage** — Move to S3/GCS for audit log screenshots

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Athar Ali](https://github.com/Athar786-Ali)**

*ActionPilot AI — Let the agent browse for you.*

</div>

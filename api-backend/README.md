# ActionPilot AI — API Backend

Enterprise-grade API Gateway for the ActionPilot autonomous web automation platform.

## Architecture

```
Client → Express API → PostgreSQL (Prisma) + BullMQ (Redis) → Python Agent Worker
                ↑                                                      │
                └────────── Webhooks (real-time audit logs) ───────────┘
```

## Endpoints

| Method | Path                        | Description                              |
|--------|-----------------------------|------------------------------------------|
| POST   | `/api/jobs`                 | Create a new automation job              |
| GET    | `/api/jobs/:id`             | Get job status + audit logs              |
| POST   | `/api/jobs/:id/submit-otp`  | Submit OTP for human-in-the-loop         |
| POST   | `/api/webhooks/logs`        | Receive real-time agent action logs      |
| GET    | `/health`                   | Health check                             |

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Generate Prisma client
npx prisma generate

# 3. Run database migrations
npx prisma migrate dev --name init

# 4. Start development server
npm run dev
```

## Prerequisites

- Node.js 18+
- PostgreSQL 15+
- Redis 7+

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/actionpilot?schema=public
REDIS_HOST=localhost
REDIS_PORT=6379
```

import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { prisma } from '../config/prisma';
import { redisPublisher } from '../config/redis';
import { env } from '../config/env';
import { jobQueue } from '../workers/jobQueue';
import type {
  CreateJobPayload,
  SubmitOtpPayload,
  ApiResponse,
  JobResponse,
  HITLPubSubMessage,
} from '../types';

// ── Validation Schemas ──────────────────────────────────────────
const createJobSchema = z.object({
  prompt: z.string().min(1, 'Prompt is required').max(4096, 'Prompt too long'),
});

const submitOtpSchema = z.object({
  otp: z.string().min(1, 'OTP is required').max(20, 'OTP too long'),
});

// ── POST /api/jobs ──────────────────────────────────────────────
export async function createJob(
  req: Request,
  res: Response<ApiResponse<JobResponse>>,
  next: NextFunction
): Promise<void> {
  try {
    const validation = createJobSchema.safeParse(req.body as CreateJobPayload);
    if (!validation.success) {
      res.status(400).json({
        success: false,
        error: validation.error.errors.map((e) => e.message).join(', '),
      });
      return;
    }

    const { prompt } = validation.data;

    // 1. Persist the job in Postgres
    const job = await prisma.job.create({
      data: { prompt },
    });

    // 2. Enqueue to BullMQ for the Python worker
    await jobQueue.add(
      `job-${job.id}`,
      { jobId: job.id, prompt: job.prompt },
      { jobId: job.id }
    );

    console.log(`🚀 Job ${job.id} created and enqueued`);

    res.status(201).json({
      success: true,
      data: {
        id: job.id,
        prompt: job.prompt,
        status: job.status,
        resultData: job.resultData,
        createdAt: job.createdAt.toISOString(),
        updatedAt: job.updatedAt.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

// ── GET /api/jobs/:id ───────────────────────────────────────────
export async function getJobById(
  req: Request<{ id: string }>,
  res: Response<ApiResponse<JobResponse & { auditLogs: unknown[] }>>,
  next: NextFunction
): Promise<void> {
  try {
    const { id } = req.params;

    const job = await prisma.job.findUnique({
      where: { id },
      include: {
        auditLogs: {
          orderBy: { timestamp: 'asc' },
        },
      },
    });

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    res.status(200).json({
      success: true,
      data: {
        id: job.id,
        prompt: job.prompt,
        status: job.status,
        resultData: job.resultData,
        createdAt: job.createdAt.toISOString(),
        updatedAt: job.updatedAt.toISOString(),
        auditLogs: job.auditLogs,
      },
    });
  } catch (err) {
    next(err);
  }
}

// ── POST /api/jobs/:id/submit-otp ───────────────────────────────
export async function submitOtp(
  req: Request<{ id: string }>,
  res: Response<ApiResponse<{ message: string }>>,
  next: NextFunction
): Promise<void> {
  try {
    const { id } = req.params;
    const validation = submitOtpSchema.safeParse(req.body as SubmitOtpPayload);

    if (!validation.success) {
      res.status(400).json({
        success: false,
        error: validation.error.errors.map((e) => e.message).join(', '),
      });
      return;
    }

    // Verify the job exists and is actually paused for HITL
    const job = await prisma.job.findUnique({ where: { id } });

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    if (job.status !== 'PAUSED_FOR_HITL') {
      res.status(409).json({
        success: false,
        error: `Job is not paused for human input. Current status: ${job.status}`,
      });
      return;
    }

    // Update job status back to RUNNING
    await prisma.job.update({
      where: { id },
      data: { status: 'RUNNING' },
    });

    // Publish OTP to Redis Pub/Sub so the Python worker can resume
    const channel = `${env.REDIS_HITL_CHANNEL_PREFIX}${id}`;
    const message: HITLPubSubMessage = {
      jobId: id,
      otp: validation.data.otp,
      timestamp: new Date().toISOString(),
    };

    await redisPublisher.publish(channel, JSON.stringify(message));

    console.log(`🔑 OTP published for job ${id} on channel ${channel}`);

    // Also log to audit trail
    await prisma.auditLog.create({
      data: {
        jobId: id,
        actionType: 'HITL_OTP_SUBMITTED',
        description: 'Human operator submitted OTP/verification code',
      },
    });

    res.status(200).json({
      success: true,
      data: { message: 'OTP submitted and published to worker' },
    });
  } catch (err) {
    next(err);
  }
}

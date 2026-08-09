import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { prisma } from '../config/prisma';
import { env } from '../config/env';
import type { WebhookLogPayload, ApiResponse } from '../types';
import { JobStatus } from '@prisma/client';

// ── Validation ──────────────────────────────────────────────────
const webhookLogSchema = z.object({
  jobId: z.string().uuid(),
  actionType: z.string().min(1),
  screenshotUrl: z.string().url().optional(),
  description: z.string().min(1),
  status: z.nativeEnum(JobStatus).optional(),
  resultData: z.unknown().optional(),
});

// ── POST /api/webhooks/logs ─────────────────────────────────────
export async function receiveAgentLog(
  req: Request,
  res: Response<ApiResponse<{ logId: string }>>,
  next: NextFunction
): Promise<void> {
  try {
    // Verify webhook secret
    const secret = req.headers['x-webhook-secret'] as string | undefined;
    if (secret !== env.WEBHOOK_SECRET) {
      res.status(401).json({ success: false, error: 'Invalid webhook secret' });
      return;
    }

    const validation = webhookLogSchema.safeParse(req.body as WebhookLogPayload);
    if (!validation.success) {
      res.status(400).json({
        success: false,
        error: validation.error.errors.map((e) => e.message).join(', '),
      });
      return;
    }

    const { jobId, actionType, screenshotUrl, description, status, resultData } =
      validation.data;

    // Verify the job exists
    const job = await prisma.job.findUnique({ where: { id: jobId } });
    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    // Update job status if provided by the worker
    if (status) {
      const updateData: { status: JobStatus; resultData?: unknown } = { status };
      if (resultData !== undefined) {
        updateData.resultData = resultData as object;
      }
      await prisma.job.update({
        where: { id: jobId },
        data: updateData,
      });
    }

    // Create audit log entry
    const auditLog = await prisma.auditLog.create({
      data: {
        jobId,
        actionType,
        screenshotUrl: screenshotUrl ?? null,
        description,
      },
    });

    console.log(`📝 Audit log ${auditLog.id} saved for job ${jobId}: [${actionType}] ${description}`);

    res.status(201).json({
      success: true,
      data: { logId: auditLog.id },
    });
  } catch (err) {
    next(err);
  }
}

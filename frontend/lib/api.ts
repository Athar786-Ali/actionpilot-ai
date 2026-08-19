// ── ActionPilot AI — API Client ──────────────────────────────────

import type { ApiResponse, Job } from './types';

const BASE_URL = '/api';

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return res.json() as Promise<ApiResponse<T>>;
}

/** POST /api/jobs — Create a new automation job */
export async function createJob(prompt: string): Promise<ApiResponse<Job>> {
  return request<Job>('/jobs', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

/** GET /api/jobs/:id — Fetch job status and audit logs */
export async function getJob(
  jobId: string
): Promise<ApiResponse<Job & { auditLogs: Job['auditLogs'] }>> {
  return request<Job & { auditLogs: Job['auditLogs'] }>(`/jobs/${jobId}`);
}

/** POST /api/jobs/:id/submit-otp — Submit OTP for HITL */
export async function submitOtp(
  jobId: string,
  otp: string
): Promise<ApiResponse<{ message: string }>> {
  return request<{ message: string }>(`/jobs/${jobId}/submit-otp`, {
    method: 'POST',
    body: JSON.stringify({ otp }),
  });
}

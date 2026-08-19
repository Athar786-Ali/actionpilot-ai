// ── ActionPilot AI — TypeScript Types ────────────────────────────

export type JobStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'PAUSED_FOR_HITL'
  | 'COMPLETED'
  | 'FAILED';

export interface AuditLog {
  id: string;
  jobId: string;
  actionType: string;
  screenshotUrl: string | null;
  description: string;
  timestamp: string;
}

export interface Job {
  id: string;
  prompt: string;
  status: JobStatus;
  resultData: unknown;
  createdAt: string;
  updatedAt: string;
  auditLogs?: AuditLog[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

import { JobStatus } from '@prisma/client';

/** Payload sent by the client to create a new automation job */
export interface CreateJobPayload {
  prompt: string;
}

/** Shape of a job record returned from the API */
export interface JobResponse {
  id: string;
  prompt: string;
  status: JobStatus;
  resultData: unknown;
  createdAt: string;
  updatedAt: string;
}

/** Payload the Python worker sends to the webhook endpoint */
export interface WebhookLogPayload {
  jobId: string;
  actionType: string;
  screenshotUrl?: string;
  description: string;
}

/** Payload for submitting an OTP via HITL */
export interface SubmitOtpPayload {
  otp: string;
}

/** Data pushed onto the BullMQ queue */
export interface BullMQJobData {
  jobId: string;
  prompt: string;
}

/** Shape of the HITL Pub/Sub message */
export interface HITLPubSubMessage {
  jobId: string;
  otp: string;
  timestamp: string;
}

/** Standard API response envelope */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

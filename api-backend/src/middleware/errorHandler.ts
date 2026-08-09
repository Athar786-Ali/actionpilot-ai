import { Request, Response, NextFunction } from 'express';
import { env } from '../config/env';
import type { ApiResponse } from '../types';

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response<ApiResponse<never>>,
  _next: NextFunction
): void {
  console.error('💥 Unhandled error:', err);

  const statusCode =
    'statusCode' in err ? (err as Error & { statusCode: number }).statusCode : 500;

  res.status(statusCode).json({
    success: false,
    error:
      env.NODE_ENV === 'production'
        ? 'Internal server error'
        : err.message || 'Unknown error',
  });
}

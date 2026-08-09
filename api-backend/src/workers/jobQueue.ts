import { Queue } from 'bullmq';
import { env } from '../config/env';
import { redisConnection } from '../config/redis';
import type { BullMQJobData } from '../types';

export const jobQueue = new Queue<BullMQJobData>(env.BULLMQ_QUEUE_NAME, {
  connection: redisConnection,
  defaultJobOptions: {
    removeOnComplete: { count: 1000, age: 86400 },   // keep last 1000 or 24h
    removeOnFail: { count: 5000, age: 604800 },       // keep last 5000 or 7d
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 3000,
    },
  },
});

jobQueue.on('error', (err) => {
  console.error('❌ BullMQ Queue error:', err.message);
});

console.log(`📋 BullMQ queue "${env.BULLMQ_QUEUE_NAME}" initialized`);

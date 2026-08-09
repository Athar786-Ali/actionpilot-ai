import Redis from 'ioredis';
import { env } from './env';

const redisConfig = {
  host: env.REDIS_HOST,
  port: env.REDIS_PORT,
  password: env.REDIS_PASSWORD || undefined,
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
  retryStrategy: (times: number): number => {
    const delay = Math.min(times * 200, 5000);
    return delay;
  },
};

/** Shared connection for BullMQ and general Redis operations */
export const redisConnection = new Redis(redisConfig);

/** Dedicated publisher for HITL Pub/Sub — must be a separate connection */
export const redisPublisher = new Redis(redisConfig);

/** Dedicated subscriber for HITL Pub/Sub — must be a separate connection */
export const redisSubscriber = new Redis(redisConfig);

redisConnection.on('connect', () => console.log('🔗 Redis connected (main)'));
redisConnection.on('error', (err) => console.error('❌ Redis error (main):', err.message));
redisPublisher.on('connect', () => console.log('🔗 Redis connected (publisher)'));
redisSubscriber.on('connect', () => console.log('🔗 Redis connected (subscriber)'));

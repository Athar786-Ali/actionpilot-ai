import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import { env } from './config/env';
import { redisConnection } from './config/redis';
import { errorHandler } from './middleware/errorHandler';
import jobRoutes from './routes/jobRoutes';
import webhookRoutes from './routes/webhookRoutes';

const app = express();

// ── Global Middleware ───────────────────────────────────────────
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(morgan(env.NODE_ENV === 'production' ? 'combined' : 'dev'));

// ── Health Check ────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.status(200).json({
    status: 'ok',
    service: 'actionpilot-api-backend',
    timestamp: new Date().toISOString(),
  });
});

// ── API Routes ──────────────────────────────────────────────────
app.use('/api/jobs', jobRoutes);
app.use('/api/webhooks', webhookRoutes);

// ── Error Handler ───────────────────────────────────────────────
app.use(errorHandler);

// ── Server Bootstrap ────────────────────────────────────────────
async function bootstrap(): Promise<void> {
  try {
    // Verify Redis connectivity
    await redisConnection.ping();
    console.log('✅ Redis ping successful');

    app.listen(env.PORT, () => {
      console.log(`
  ╔══════════════════════════════════════════════╗
  ║   🤖 ActionPilot AI — API Gateway           ║
  ║   🌐 http://localhost:${env.PORT}                ║
  ║   📋 Environment: ${env.NODE_ENV.padEnd(22)}║
  ╚══════════════════════════════════════════════╝
      `);
    });
  } catch (err) {
    console.error('❌ Failed to start server:', err);
    process.exit(1);
  }
}

bootstrap();

// ── Graceful Shutdown ───────────────────────────────────────────
const signals: NodeJS.Signals[] = ['SIGTERM', 'SIGINT'];
signals.forEach((signal) => {
  process.on(signal, async () => {
    console.log(`\n📴 Received ${signal}, shutting down gracefully...`);
    await redisConnection.quit();
    process.exit(0);
  });
});

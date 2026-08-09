import { Router } from 'express';
import { receiveAgentLog } from '../controllers/webhookController';

const router = Router();

router.post('/logs', receiveAgentLog);

export default router;

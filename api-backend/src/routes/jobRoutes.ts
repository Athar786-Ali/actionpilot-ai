import { Router } from 'express';
import { createJob, getJobById, submitOtp } from '../controllers/jobController';

const router = Router();

router.post('/', createJob);
router.get('/:id', getJobById);
router.post('/:id/submit-otp', submitOtp);

export default router;

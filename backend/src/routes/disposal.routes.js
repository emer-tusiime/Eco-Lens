const multer = require('multer');
const upload = multer({ storage: multer.memoryStorage() });
const router = require('express').Router();
const disposal = require('../controllers/disposal.controller');
const { authenticate } = require('../middleware/auth');

// Public: RPi disposal unit endpoints
router.post('/sessions/start', disposal.startSession);
router.post('/sessions/end', disposal.endSession);
router.post('/classify', upload.single('image'), disposal.classifyImage);
router.post('/events', disposal.recordEvent);
router.get('/kiosks/:unitId/status', disposal.getKioskStatus);
router.patch('/kiosks/:unitId/capacity', disposal.updateKioskCapacity);

// Protected: Mobile app endpoints
router.get('/history', authenticate, disposal.getHistory);
router.get('/stats', authenticate, disposal.getStats);

module.exports = router;
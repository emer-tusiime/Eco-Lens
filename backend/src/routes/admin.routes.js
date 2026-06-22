const express = require('express');
const router = express.Router();
const adminController = require('../controllers/admin.controller');
const { authenticateAdmin } = require('../middleware/auth');

// Public
router.post('/login', adminController.login);

// Protected (admin token required)
router.get('/overview', authenticateAdmin, adminController.overview);
router.get('/kiosks', authenticateAdmin, adminController.listKiosks);
router.post('/kiosks', authenticateAdmin, adminController.registerKiosk);
router.patch('/kiosks/:id', authenticateAdmin, adminController.updateKiosk);

module.exports = router;
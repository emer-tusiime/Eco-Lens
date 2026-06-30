const express = require('express');
const router = express.Router();
const adminController = require('../controllers/admin.controller');
const { authenticateAdmin } = require('../middleware/auth');

// Public
router.post('/login', adminController.login);

// Protected (admin token required)
router.get('/overview', authenticateAdmin, adminController.overview);
router.get('/redemptions', authenticateAdmin, adminController.listRedemptions);
router.get('/kiosks', authenticateAdmin, adminController.listKiosks);
router.post('/kiosks', authenticateAdmin, adminController.registerKiosk);
router.get('/kiosks/:id', authenticateAdmin, adminController.getKiosk);
router.patch('/kiosks/:id', authenticateAdmin, adminController.updateKiosk);
router.post('/kiosks/:id/reset-capacity', authenticateAdmin, adminController.resetKioskCapacity);

// User management
router.get('/users', authenticateAdmin, adminController.listUsers);
router.post('/users', authenticateAdmin, adminController.createUser);
router.patch('/users/:id', authenticateAdmin, adminController.updateUser);

module.exports = router;
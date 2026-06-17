const jwt = require('jsonwebtoken');
const { User } = require('../models');

const authenticate = async (req, res, next) => {
  try {
    const header = req.headers.authorization;
    if (!header || !header.startsWith('Bearer '))
      return res.status(401).json({ error: 'No token provided' });

    const token = header.split(' ')[1];
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findByPk(decoded.id);

    if (!user || !user.isActive)
      return res.status(401).json({ error: 'Invalid or inactive user' });

    req.user = user;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

const generateToken = (user) => {
  return jwt.sign({ id: user.id, email: user.email }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRATION || '7d',
  });
};

const { Admin } = require('../models');

const authenticateAdmin = async (req, res, next) => {
  try {
    const header = req.headers.authorization;
    if (!header || !header.startsWith('Bearer '))
      return res.status(401).json({ error: 'No token provided' });

    const token = header.split(' ')[1];
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    if (!decoded.isAdmin)
      return res.status(403).json({ error: 'Admin access required' });

    const admin = await Admin.findByPk(decoded.id);
    if (!admin || !admin.isActive)
      return res.status(401).json({ error: 'Invalid or inactive admin' });

    req.admin = admin;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

const generateAdminToken = (admin) => {
  return jwt.sign({ id: admin.id, email: admin.email, isAdmin: true }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRATION || '7d',
  });
};

module.exports = { authenticate, generateToken, authenticateAdmin, generateAdminToken };
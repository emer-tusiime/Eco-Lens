require('dotenv').config();
const { sequelize } = require('./config/database');
const { Admin } = require('./models');

const seed = async () => {
  try {
    await sequelize.authenticate();
    await sequelize.sync({ alter: true });

    const email = 'admin@ecolens.com';
    const existing = await Admin.findOne({ where: { email } });
    if (existing) {
      console.log('Admin already exists:', email);
      process.exit(0);
    }

    const admin = await Admin.create({
      name: 'EcoLens Admin',
      email,
      password: 'Admin12345',   // change after first login in production
    });
    console.log('✅ Admin created:', admin.email);
    console.log('   Password: Admin12345');
    process.exit(0);
  } catch (err) {
    console.error('Seed failed:', err);
    process.exit(1);
  }
};

seed();
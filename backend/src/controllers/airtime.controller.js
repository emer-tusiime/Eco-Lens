const { RewardBalance, AirtimeRedemption, RewardTransaction } = require('../models');
const { sequelize } = require('../config/database');

// Normalise a Uganda phone number to +256XXXXXXXXX
function normalizePhone(input) {
  if (!input) return null;
  let p = String(input).replace(/\s+/g, '').replace(/^\+/, '');
  if (p.startsWith('0')) p = '256' + p.slice(1);                 // 0755... -> 256755...
  else if (p.startsWith('7') || p.startsWith('3')) p = '256' + p; // 755...  -> 256755...
  if (!p.startsWith('256') || p.length !== 12) return null;
  return '+' + p;
}

// Detect Uganda mobile network from a normalised +256 number.
// Returns 'MTN', 'AIRTEL', or null (unsupported).
function detectNetwork(normalizedPhone) {
  const prefix = normalizedPhone.slice(4, 6); // two digits after +256
  const mtn = ['77', '78', '76', '39'];
  const airtel = ['70', '75', '74', '20'];
  if (mtn.includes(prefix)) return 'MTN';
  if (airtel.includes(prefix)) return 'AIRTEL';
  return null;
}

// Send airtime via Africa's Talking API
async function sendAirtime(phoneNumber, amount, currencyCode) {
  try {
    const AfricasTalking = require('africastalking');
    const at = AfricasTalking({
      apiKey: process.env.AT_API_KEY,
      username: process.env.AT_USERNAME,
    });
    const airtime = at.AIRTIME;

    const result = await airtime.send({
      recipients: [{ phoneNumber, amount: `${currencyCode} ${amount.toFixed(2)}` }],
    });

    // Parse the response
    const entry = result.responses?.[0];
    if (entry && (entry.status === 'Sent' || entry.status === 'Queued')) {
      return { success: true, requestId: entry.requestId, discount: entry.discount };
    } else {
      return { success: false, error: entry?.errorMessage || result.errorMessage || 'Unknown error' };
    }
  } catch (err) {
    console.error('Africa\'s Talking API error:', err);
    return { success: false, error: err.message || 'API call failed' };
  }
}

// Redeem points for airtime
exports.redeem = async (req, res) => {
  const t = await sequelize.transaction();
  try {
    const { points } = req.body;
    const userId = req.user.id;
    const rate = parseInt(process.env.POINTS_TO_UGX_RATE) || 25;
    const minPoints = parseInt(process.env.MIN_REDEMPTION_POINTS) || 100;
    const currency = process.env.AT_CURRENCY_CODE || 'UGX';

    // Validate points
    if (!points || points < minPoints) {
      await t.rollback();
      return res.status(400).json({ error: `Minimum redemption is ${minPoints} points` });
    }

    // Validate and normalise phone number
    const phoneNumber = normalizePhone(req.user.phone);
    if (!phoneNumber) {
      await t.rollback();
      return res.status(400).json({ error: 'Invalid phone number on account. Please update it to a valid Uganda number (e.g. 0755123456).' });
    }

    // Only MTN and Airtel are supported
    const network = detectNetwork(phoneNumber);
    if (!network) {
      await t.rollback();
      return res.status(400).json({ error: 'Airtime is only supported for MTN and Airtel Uganda numbers.' });
    }

    // Check balance
    const balance = await RewardBalance.findOne({ where: { userId }, transaction: t });
    if (!balance || balance.currentPoints < points) {
      await t.rollback();
      return res.status(400).json({ error: `Insufficient points. You have ${balance?.currentPoints || 0} points.` });
    }

    const ugxAmount = points * rate;

    // Enforce Africa's Talking per-transaction limits for Uganda (UGX 50 - 200,000)
    if (ugxAmount < 50 || ugxAmount > 200000) {
      await t.rollback();
      return res.status(400).json({ error: `Airtime amount (${currency} ${ugxAmount}) is outside the allowed range of ${currency} 50 - 200,000.` });
    }

    // Create pending redemption record
    const redemption = await AirtimeRedemption.create({
      userId, pointsRedeemed: points,
      airtimeAmountUgx: ugxAmount, phoneNumber, status: 'pending',
    }, { transaction: t });

    // Call Africa's Talking API
    const result = await sendAirtime(phoneNumber, ugxAmount, currency);

    if (result.success) {
      // Deduct points ONLY on success
      balance.currentPoints -= points;
      await balance.save({ transaction: t });

      redemption.status = 'successful';
      redemption.atTransactionId = result.requestId;
      await redemption.save({ transaction: t });

      await RewardTransaction.create({
        userId, type: 'redeemed', points: -points,
        description: `Redeemed ${points} points for ${currency} ${ugxAmount} airtime to ${phoneNumber} (${network})`,
      }, { transaction: t });

      await t.commit();

      res.json({
        message: `Airtime of ${currency} ${ugxAmount} sent to ${phoneNumber} (${network}) successfully.`,
        redemption: {
          id: redemption.id, pointsRedeemed: points,
          airtimeAmount: `${currency} ${ugxAmount}`,
          phoneNumber, network, transactionId: result.requestId, status: 'successful',
        },
        remainingPoints: balance.currentPoints,
      });
    } else {
      // Failed — do NOT deduct points
      redemption.status = 'failed';
      redemption.errorMessage = result.error;
      await redemption.save({ transaction: t });
      await t.commit();

      res.status(502).json({
        error: 'Airtime disbursement failed. Points not deducted. Please try again.',
        details: result.error,
      });
    }
  } catch (err) {
    await t.rollback();
    console.error('Redeem error:', err);
    res.status(500).json({ error: 'Redemption failed' });
  }
};

// Get redemption history
exports.getRedemptions = async (req, res) => {
  try {
    const redemptions = await AirtimeRedemption.findAll({
      where: { userId: req.user.id },
      order: [['createdAt', 'DESC']],
      limit: 50,
    });
    res.json({ redemptions });
  } catch (err) {
    res.status(500).json({ error: 'Failed to load redemptions' });
  }
};

// Status callback from Africa's Talking
exports.statusCallback = async (req, res) => {
  try {
    const { requestId, status } = req.body;
    if (!requestId) return res.status(400).json({ error: 'Missing requestId' });

    const redemption = await AirtimeRedemption.findOne({ where: { atTransactionId: requestId } });
    if (redemption) {
      redemption.status = status === 'Success' ? 'successful' : 'failed';
      await redemption.save();
    }

    res.json({ status: 'received' });
  } catch (err) {
    res.status(500).json({ error: 'Callback processing failed' });
  }
};
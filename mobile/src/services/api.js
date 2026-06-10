import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Use your computer's IP address running the backend
const API_BASE = 'https://eco-lens-production.up.railway.app';
const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token automatically
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync('token');

      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      console.error('Token read error:', err);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Auth
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getProfile: () => api.get('/auth/profile'),
  updatePhone: (phone) => api.put('/auth/phone', { phone }),
};

// Disposal
export const disposalAPI = {
  getHistory: (page = 1) =>
    api.get(`/disposal/history?page=${page}`),

  getStats: () =>
    api.get('/disposal/stats'),
};

// Airtime
export const airtimeAPI = {
  redeem: (points) =>
    api.post('/airtime/redeem', { points }),

  getHistory: () =>
    api.get('/airtime/history'),
};

export default api;
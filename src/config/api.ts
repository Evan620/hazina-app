// Use internal Railway URL when deployed, fallback to public URL
const isRailway = window.location.hostname.includes('.up.railway.app');
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// For Railway: use the hazina-app service via internal network
// For local/Vercel: use public Railway URL
const API_URL = import.meta.env.VITE_API_URL ||
  (isRailway ? 'http://hazina-app:8000' : 'https://hazina-app-production.up.railway.app');

export const API_BASE = `${API_URL}/api/v1`;

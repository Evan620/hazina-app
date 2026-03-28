// Use internal Railway URL when deployed, fallback to public URL
const isRailway = window.location.hostname.includes('.up.railway.app');

// For Railway: use private domain for internal networking
// For local/Vercel: use public Railway URL
const API_URL = import.meta.env.VITE_API_URL ||
  (isRailway ? 'https://hazina-app.railway.internal' : 'https://hazina-app-production.up.railway.app');

export const API_BASE = `${API_URL}/api/v1`;

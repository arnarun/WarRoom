import axios from 'axios'

// In production (Railway), VITE_API_URL is the full backend URL e.g. https://backend.up.railway.app
// In local dev, fall back to '' so Vite's proxy handles /api/* → localhost:8000
const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 15000,
})

export default api

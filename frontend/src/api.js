import axios from 'axios';

const API_BASE = '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 min timeout for heavy scraping
});

export async function searchProducts(query, pincode) {
  const res = await api.get('/api/search', {
    params: { q: query, pincode },
  });
  return res.data;
}

export async function getPincodeInfo(pincode) {
  const res = await api.get(`/api/pincode/${pincode}`);
  return res.data;
}

export async function getHealth() {
  const res = await api.get('/api/health');
  return res.data;
}

export default api;

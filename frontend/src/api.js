import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

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

export async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`, {
      headers: { 'User-Agent': 'QuicboApp/1.0' }
    });
    const data = await res.json();
    
    if (data.address) {
      const address = data.address;
      const postcode = address.postcode ? address.postcode.replace(/\s+/g, '') : '';
      const city = address.city || address.town || address.village || '';
      const district = (address.state_district || '').replace(' District', '');
      const state = address.state || '';
      
      if (postcode && postcode.length === 6 && /^\d+$/.test(postcode)) {
        return {
          pincode: postcode,
          city,
          district,
          state,
          full_label: `${city || district} ${postcode}`.trim()
        };
      }
    }
  } catch (err) {
    console.warn("Nominatim frontend fetch failed", err);
  }

  // Fallback to BigDataCloud natively in browser
  try {
    const res = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`);
    const data = await res.json();
    const postcode = data.postcode || '';
    const city = data.city || data.locality || '';
    
    return {
      pincode: postcode,
      city,
      full_label: `${city} ${postcode}`.trim()
    };
  } catch (err) {
    console.error("All geocoding fallbacks failed", err);
    throw new Error('Geocoding failed');
  }
}

export async function prewarmLocation(pincode) {
  try {
    const res = await api.post(`/api/prewarm?pincode=${pincode}`);
    return res.data;
  } catch (e) {
    console.warn('[prewarm] failed:', e?.message);
    return null;
  }
}

export async function getHealth() {
  const res = await api.get('/api/health');
  return res.data;
}

export default api;

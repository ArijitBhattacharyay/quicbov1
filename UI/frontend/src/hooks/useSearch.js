import { useState, useCallback } from 'react';
import { searchProducts } from '../api';

export function useSearch() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuery, setLastQuery] = useState('');
  const [cached, setCached] = useState(false);
  const [searchKey, setSearchKey] = useState(0); // forces ProductGrid remount

  const search = useCallback(async (query, pincode) => {
    const q = query?.trim();
    const pin = pincode?.trim();
    if (!q || !pin) return;

    // Immediately clear old results and show loading
    setLoading(true);
    setError(null);
    setResults(null);
    setLastQuery(q);
    setCached(false);
    setSearchKey(k => k + 1); // force re-render of results

    try {
      const data = await searchProducts(q, pin);
      setResults(data);
      setCached(data.cached || false);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not connect to server. Is the backend running on port 8000?';
      setError(msg);
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResults(null);
    setLoading(false);
    setError(null);
    setLastQuery('');
    setSearchKey(k => k + 1);
  }, []);

  return { results, loading, error, search, reset, lastQuery, cached, searchKey };
}

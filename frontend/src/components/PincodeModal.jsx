import { useState, useEffect } from 'react';
import { MapPin, X, Navigation } from 'lucide-react';
import { getPincodeInfo, reverseGeocode } from '../api';

export default function PincodeModal({ currentPincode, onConfirm, onClose }) {
  const [input, setInput] = useState(currentPincode || '');
  const [loading, setLoading] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [error, setError] = useState('');
  const [locationResult, setLocationResult] = useState(null);
  const [geoCoords, setGeoCoords] = useState(null);

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleLookup = async () => {
    const val = input.trim();
    if (!/^\d{6}$/.test(val)) {
      setError('Please enter a valid 6-digit pincode.');
      return;
    }
    setError('');
    setLoading(true);
    setLocationResult(null);
    setGeoCoords(null);
    try {
      const data = await getPincodeInfo(val);
      setLocationResult(data);
    } catch {
      setError('Could not resolve this pincode. Please check and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGeoLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      return;
    }

    setGeoLoading(true);
    setError('');
    setLocationResult(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setGeoCoords({ lat: latitude, lng: longitude });
        try {
          const data = await reverseGeocode(latitude, longitude);
          setLocationResult(data);
          setInput(data.pincode);
        } catch (err) {
          setError('Could not detect your exact address. Please enter pincode manually.');
        } finally {
          setGeoLoading(false);
        }
      },
      (err) => {
        setGeoLoading(false);
        if (err.code === 1) setError('Location permission denied.');
        else setError('Could not retrieve your location.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleLookup();
  };

  const handleConfirm = () => {
    if (locationResult) {
      onConfirm(locationResult.pincode, locationResult.full_label, geoCoords);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
          <h2 className="modal__title">📍 Set Delivery Location</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9aa0a6', padding: 4 }}
          >
            <X size={18} />
          </button>
        </div>
        <p className="modal__sub">Enter your 6-digit pincode to see prices and delivery times in your area.</p>

        {/* Detect Location Button */}
        {!locationResult && !loading && (
          <button 
            className="modal__geo-btn" 
            onClick={handleGeoLocation}
            disabled={geoLoading}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '12px',
              background: '#f8f9fa',
              border: '1px solid #dee2e6',
              borderRadius: '10px',
              fontSize: '14px',
              fontWeight: 600,
              color: '#FF6B00',
              cursor: 'pointer',
              marginBottom: '16px',
              transition: 'all 0.2s'
            }}
          >
            <Navigation size={16} fill={geoLoading ? 'none' : '#FF6B00'} />
            {geoLoading ? 'Detecting location...' : 'Use Current Location'}
          </button>
        )}

        {/* Input Row */}
        <div className="modal__input-row">
          <input
            className="modal__input"
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="e.g. 110021"
            value={input}
            onChange={(e) => {
              setInput(e.target.value.replace(/\D/, ''));
              setError('');
              setLocationResult(null);
              setGeoCoords(null);
            }}
            onKeyDown={handleKeyDown}
            autoFocus
            id="pincode-input"
          />
          <button
            className="modal__btn"
            onClick={handleLookup}
            disabled={loading || geoLoading || input.length !== 6}
          >
            {loading ? '...' : 'Check'}
          </button>
        </div>

        {error && <p className="modal__error">⚠ {error}</p>}

        {locationResult && (
          <>
            <div className="modal__result">
              <MapPin size={16} color="#16a34a" />
              <div>
                <p className="modal__result-text" style={{ fontWeight: 700 }}>
                  {locationResult.district || locationResult.city}, {locationResult.state}
                </p>
                <p style={{ fontSize: 11, color: '#4b7a34', marginTop: 2 }}>
                  Pincode: {locationResult.pincode} {geoCoords && '• GPS Verified'}
                </p>
              </div>
            </div>
            <button className="modal__confirm-btn" onClick={handleConfirm}>
              ✓ Deliver here
            </button>
          </>
        )}
      </div>
    </div>
  );
}

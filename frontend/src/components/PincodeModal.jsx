import { useState } from 'react';
import { MapPin, X } from 'lucide-react';
import { getPincodeInfo } from '../api';

export default function PincodeModal({ currentPincode, onConfirm, onClose }) {
  const [input, setInput] = useState(currentPincode || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [locationResult, setLocationResult] = useState(null);

  const handleLookup = async () => {
    const val = input.trim();
    if (!/^\d{6}$/.test(val)) {
      setError('Please enter a valid 6-digit pincode.');
      return;
    }
    setError('');
    setLoading(true);
    setLocationResult(null);
    try {
      const data = await getPincodeInfo(val);
      setLocationResult(data);
    } catch {
      setError('Could not resolve this pincode. Please check and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleLookup();
  };

  const handleConfirm = () => {
    if (locationResult) {
      onConfirm(locationResult.pincode, locationResult.full_label);
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
            }}
            onKeyDown={handleKeyDown}
            autoFocus
            id="pincode-input"
          />
          <button
            className="modal__btn"
            onClick={handleLookup}
            disabled={loading || input.length !== 6}
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
                  Pincode: {locationResult.pincode}
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

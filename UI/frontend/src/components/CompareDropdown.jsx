import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { getPlatform, formatPrice, formatDelivery } from '../platforms';

function PlatformLogo({ platformId, size = 22 }) {
  const p = getPlatform(platformId);
  return (
    <div
      style={{
        width: size,
        height: size,
        backgroundColor: p.color,
        color: p.textColor,
        borderRadius: 4,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: size * 0.38,
        flexShrink: 0,
        letterSpacing: '-0.5px',
      }}
    >
      {p.shortLabel}
    </div>
  );
}

export default function CompareDropdown({ offers }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const btnRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (
        menuRef.current && !menuRef.current.contains(e.target) &&
        btnRef.current && !btnRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const available = offers.filter((o) => o.available);
  const unavailable = offers.filter((o) => !o.available);

  return (
    <div className="compare-dropdown" style={{ position: 'relative' }}>
      <button
        ref={btnRef}
        className={`compare-dropdown__trigger${open ? ' open' : ''}`}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        type="button"
      >
        <span>Compare Others</span>
        <ChevronDown
          size={14}
          style={{
            transition: 'transform 0.2s ease',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }}
        />
      </button>

      {open && (
        <div
          ref={menuRef}
          className="compare-dropdown__menu"
          style={{ zIndex: 200 }}
        >
          {available.map((offer) => {
            const p = getPlatform(offer.platform);
            return (
              <div className="compare-dropdown__item" key={offer.platform}>
                <PlatformLogo platformId={offer.platform} size={22} />
                <div className="compare-dropdown__item-info">
                  <span className="compare-dropdown__item-platform">{p.label}</span>
                  <span className="compare-dropdown__item-delivery">
                    🚴 {offer.delivery_label || formatDelivery(offer.delivery_time)}
                  </span>
                </div>
                <span className="compare-dropdown__item-price">
                  {formatPrice(offer.price)}
                </span>
              </div>
            );
          })}

          {unavailable.map((offer) => {
            const p = getPlatform(offer.platform);
            return (
              <div
                className="compare-dropdown__item"
                key={offer.platform}
                style={{ opacity: 0.5 }}
              >
                <PlatformLogo platformId={offer.platform} size={22} />
                <div className="compare-dropdown__item-info">
                  <span className="compare-dropdown__item-platform">{p.label}</span>
                  <span className="compare-dropdown__item-delivery">—</span>
                </div>
                <span className="compare-dropdown__item-na">Not Available</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

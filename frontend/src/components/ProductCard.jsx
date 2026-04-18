import { useState } from 'react';
import { ShoppingCart } from 'lucide-react';
import CompareDropdown from './CompareDropdown';
import { getPlatform, formatPrice, formatDelivery } from '../platforms';

function PlatformLogo({ platformId, size = 22 }) {
  const p = getPlatform(platformId);
  return (
    <div
      className="platform-badge__logo-fallback"
      style={{
        width: size,
        height: size,
        backgroundColor: p.color,
        color: p.textColor,
        fontSize: size * 0.38,
        borderRadius: 4,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {p.shortLabel}
    </div>
  );
}

function ProductImage({ imageUrl, name, emoji }) {
  const [status, setStatus] = useState(imageUrl ? 'loading' : 'error');
  const displayEmoji = emoji || getProductEmoji(name);

  if (!imageUrl || status === 'error') {
    return (
      <div className="product-card__image-placeholder">
        <span style={{ fontSize: 44 }}>{displayEmoji}</span>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Shimmer while loading */}
      {status === 'loading' && (
        <div
          style={{
            position: 'absolute', inset: 0,
            background: 'linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.2s infinite',
            borderRadius: 8,
          }}
        />
      )}
      <img
        className="product-card__image"
        src={imageUrl}
        alt={name}
        crossOrigin="anonymous"
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
        style={{
          opacity: status === 'loaded' ? 1 : 0,
          transition: 'opacity 0.3s ease',
          position: 'relative',
        }}
        loading="lazy"
      />
    </div>
  );
}


function getProductEmoji(name = '') {
  const n = name.toLowerCase();
  if (n.includes('milk') || n.includes('doodh')) return '🥛';
  if (n.includes('dahi') || n.includes('curd') || n.includes('yogurt')) return '🍶';
  if (n.includes('butter')) return '🧈';
  if (n.includes('cheese') || n.includes('paneer')) return '🧀';
  if (n.includes('egg') || n.includes('anda')) return '🥚';
  if (n.includes('bread') || n.includes('atta') || n.includes('flour')) return '🍞';
  if (n.includes('rice') || n.includes('chawal')) return '🍚';
  if (n.includes('oil') || n.includes('tel')) return '🫙';
  if (n.includes('juice') || n.includes('drink')) return '🧃';
  if (n.includes('biscuit') || n.includes('cookie')) return '🍪';
  if (n.includes('chocolate')) return '🍫';
  if (n.includes('coffee')) return '☕';
  if (n.includes('tea') || n.includes('chai')) return '🍵';
  if (n.includes('soap') || n.includes('shampoo')) return '🧴';
  if (n.includes('tomato')) return '🍅';
  if (n.includes('onion')) return '🧅';
  if (n.includes('potato') || n.includes('aloo')) return '🥔';
  if (n.includes('apple')) return '🍎';
  if (n.includes('banana')) return '🍌';
  return '🛒';
}

export default function ProductCard({ product, onAddToCart }) {
  const { name, image_url, quantity, best_offer, all_offers } = product;

  const bestPlatform = best_offer ? getPlatform(best_offer.platform) : null;

  // Filter out the best offer from the dropdown so we don't display it twice
  const otherOffers = all_offers
    ? all_offers.filter((o) => o.platform !== best_offer?.platform)
    : [];

  return (
    <div className="product-card">
      {/* Product Image */}
      <div className="product-card__image-wrap">
        <ProductImage imageUrl={image_url} name={name} emoji={product.emoji} />
      </div>

      {/* Card Body */}
      <div className="product-card__body">
        {/* Name & Quantity */}
        <div>
          <p className="product-card__name">{name}</p>
          {quantity && (
            <p className="product-card__quantity">{quantity}</p>
          )}
        </div>

        {/* Best Offer Section */}
        {best_offer ? (
          <div className="best-offer">
            <p className="best-offer__label">Best Offer</p>
            <div className="best-offer__row">
              <div className="platform-badge">
                <PlatformLogo platformId={best_offer.platform} size={22} />
                <span className="platform-badge__name">{bestPlatform?.label}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                <span className="best-offer__price">{formatPrice(best_offer.price)}</span>
                <span className="best-offer__delivery">
                  {best_offer.delivery_label || formatDelivery(best_offer.delivery_time)}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="best-offer" style={{ background: '#fff5f5', borderColor: '#fecaca' }}>
            <p className="best-offer__label" style={{ color: '#ef4444' }}>Not Available</p>
            <p style={{ fontSize: 12, color: '#ef4444' }}>No platforms have this in stock</p>
          </div>
        )}

        {/* Compare Dropdown */}
        {otherOffers.length > 0 && (
          <CompareDropdown offers={otherOffers} />
        )}
      </div>

      {/* Add to Cart Button */}
      <div className="product-card__footer">
        <button
          className="add-to-cart-btn"
          onClick={() => onAddToCart && onAddToCart(product)}
          disabled={!best_offer}
          style={!best_offer ? { background: '#ccc', cursor: 'not-allowed' } : {}}
        >
          Add to Cart
        </button>
      </div>
    </div>
  );
}

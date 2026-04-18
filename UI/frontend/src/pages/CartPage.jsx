import { useState } from 'react';
import { ArrowLeft, Zap, Trophy, ShoppingBag } from 'lucide-react';

const PLATFORM_COLORS = {
  blinkit:   { bg: '#FFFBEB', accent: '#b45309', border: '#FCD34D', label: 'Blinkit',         short: 'BL' },
  zepto:     { bg: '#F5F3FF', accent: '#7c3aed', border: '#C4B5FD', label: 'Zepto',           short: 'ZP' },
  instamart: { bg: '#FFF7ED', accent: '#ea580c', border: '#FED7AA', label: 'Swiggy Instamart',short: 'SM' },
  bigbasket: { bg: '#F0FDF4', accent: '#16a34a', border: '#86EFAC', label: 'BigBasket',       short: 'BB' },
};

const PLATFORMS = ['blinkit', 'zepto', 'instamart', 'bigbasket'];

function getPrice(item, platform) {
  const o = item.all_offers?.find(x => x.platform === platform);
  return o?.available ? o.price : null;
}
function getDelivery(item, platform) {
  const o = item.all_offers?.find(x => x.platform === platform);
  return o?.available ? o.delivery_time : null;
}

export default function CartPage({ cartItems, onBack, onRemove }) {
  // Selected platform per item (default = best price)
  const [selected, setSelected] = useState(() => {
    const m = {};
    cartItems.forEach(item => {
      const best = [...(item.all_offers || [])]
        .filter(o => o.available)
        .sort((a, b) => (a.price || 9999) - (b.price || 9999))[0];
      m[item.id] = best?.platform || 'blinkit';
    });
    return m;
  });

  if (cartItems.length === 0) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg-main)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <span style={{ fontSize: 72 }}>🛒</span>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#202124' }}>Your cart is empty</h2>
        <p style={{ color: '#6b7280', fontSize: 14 }}>Search for products and add them to compare prices</p>
        <button onClick={onBack} className="add-to-cart-btn" style={{ width: 180 }}>← Back to Search</button>
      </div>
    );
  }

  // Platform totals (all items from one platform)
  const platformTotals = PLATFORMS.map(p => {
    let total = 0, allAvail = true;
    cartItems.forEach(item => {
      const price = getPrice(item, p);
      if (price) total += price;
      else allAvail = false;
    });
    return { platform: p, total, allAvail };
  }).sort((a, b) => a.total - b.total);

  const bestTotal = platformTotals.find(t => t.allAvail)?.total || platformTotals[0].total;
  const fastestPlatform = PLATFORMS.map(p => {
    const times = cartItems.map(item => getDelivery(item, p)).filter(Boolean);
    return { platform: p, maxTime: times.length ? Math.max(...times) : 999 };
  }).sort((a, b) => a.maxTime - b.maxTime)[0];

  // Mixed total (user's custom selection)
  const mixedTotal = cartItems.reduce((sum, item) => {
    const price = getPrice(item, selected[item.id]);
    return sum + (price || 0);
  }, 0);

  // Smart pick: best price per item regardless of platform
  const smartTotal = cartItems.reduce((sum, item) => {
    const best = Math.min(...PLATFORMS.map(p => getPrice(item, p) || 9999).filter(v => v < 9999));
    return sum + (best < 9999 ? best : 0);
  }, 0);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', fontFamily: 'Inter,sans-serif' }}>
      {/* Header */}
      <div style={{ background: '#fff', boxShadow: '0 1px 8px rgba(0,0,0,.08)', padding: '14px 24px', display: 'flex', alignItems: 'center', gap: 16, position: 'sticky', top: 0, zIndex: 50 }}>
        <button
          onClick={onBack}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#374151', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 6, borderRadius: 8, transition: 'background 0.2s' }}
          onMouseEnter={e => e.currentTarget.style.background = '#f3f4f6'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <ArrowLeft size={20} />
        </button>
        <span style={{ fontWeight: 800, fontSize: 20, color: '#FF6B00', letterSpacing: '-1px' }}>quicbo</span>
        <span style={{ fontWeight: 600, color: '#374151', fontSize: 15 }}>/ Cart Comparison</span>
        <span style={{ marginLeft: 'auto', background: '#FF6B00', color: '#fff', borderRadius: 20, padding: '2px 12px', fontSize: 13, fontWeight: 600 }}>{cartItems.length} items</span>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>

        {/* Summary Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12, marginBottom: 24 }}>
          {platformTotals.slice(0, 4).map((pt, idx) => {
            const c = PLATFORM_COLORS[pt.platform];
            const isBest = pt.total === platformTotals[0].total && pt.allAvail;
            const isFastest = pt.platform === fastestPlatform.platform;
            return (
              <div key={pt.platform} style={{
                background: isBest ? c.bg : '#fff',
                borderRadius: 14,
                padding: '16px 18px',
                border: `2px solid ${isBest ? c.border : c.border + '66'}`,
                position: 'relative',
                boxShadow: isBest ? `0 4px 20px ${c.accent}22` : '0 1px 6px rgba(0,0,0,.06)',
                transition: 'transform 0.2s, box-shadow 0.2s',
              }}>
                {isBest && <span style={{ position: 'absolute', top: -10, left: 16, background: c.accent, color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20, display: 'flex', alignItems: 'center', gap: 4 }}><Trophy size={10} /> BEST DEAL</span>}
                {isFastest && !isBest && <span style={{ position: 'absolute', top: -10, left: 16, background: '#8025FB', color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20, display: 'flex', alignItems: 'center', gap: 4 }}><Zap size={10} /> FASTEST</span>}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 6, background: c.bg, border: `1.5px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 11, color: c.accent }}>{c.short}</div>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>{c.label}</span>
                </div>
                <div style={{ fontSize: 26, fontWeight: 800, color: isBest ? c.accent : '#111827' }}>₹{pt.total}</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                  {pt.allAvail ? `All ${cartItems.length} items available` : 'Some items unavailable'}
                </div>
                {isBest && platformTotals.length > 1 && (
                  <div style={{ fontSize: 11, color: c.accent, fontWeight: 700, marginTop: 6, background: `${c.accent}15`, borderRadius: 6, padding: '3px 8px', display: 'inline-block' }}>
                    Save ₹{platformTotals[platformTotals.length - 1].total - pt.total} vs highest
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Comparison Table */}
        <div style={{ background: '#fff', borderRadius: 16, overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,.07)', marginBottom: 24 }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #f3f4f6' }}>
                  <th style={{ padding: '14px 16px', textAlign: 'left', fontWeight: 700, color: '#374151', minWidth: 180 }}>Product</th>
                  {PLATFORMS.map(p => {
                    const c = PLATFORM_COLORS[p];
                    return (
                      <th key={p} style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 700, color: c.accent, minWidth: 140 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                          <div style={{ width: 28, height: 28, borderRadius: 6, background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 11, color: c.accent }}>{c.short}</div>
                          <span style={{ fontSize: 11 }}>{c.label}</span>
                        </div>
                      </th>
                    );
                  })}
                  <th style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 700, color: '#374151', minWidth: 100 }}>Remove</th>
                </tr>
              </thead>
              <tbody>
                {cartItems.map((item, idx) => (
                  <tr key={item.id} style={{ borderBottom: '1px solid #f3f4f6', background: idx % 2 === 0 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 28 }}>{item.emoji || '🛒'}</span>
                        <div>
                          <div style={{ fontWeight: 600, color: '#111827', fontSize: 13 }}>{item.name}</div>
                          <div style={{ color: '#9ca3af', fontSize: 11 }}>{item.quantity}</div>
                        </div>
                      </div>
                      {/* Platform selector */}
                      <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                        {PLATFORMS.map(p => {
                          const price = getPrice(item, p);
                          if (!price) return null;
                          const c = PLATFORM_COLORS[p];
                          const isSelected = selected[item.id] === p;
                          return (
                            <button key={p} onClick={() => setSelected(s => ({ ...s, [item.id]: p }))}
                              style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, border: `1.5px solid ${isSelected ? c.accent : '#e5e7eb'}`, background: isSelected ? c.bg : '#fff', color: isSelected ? c.accent : '#6b7280', fontWeight: isSelected ? 700 : 400, cursor: 'pointer' }}>
                              {c.short}
                            </button>
                          );
                        })}
                      </div>
                    </td>
                    {PLATFORMS.map(p => {
                      const price = getPrice(item, p);
                      const delivery = getDelivery(item, p);
                      const allPrices = PLATFORMS.map(pl => getPrice(item, pl)).filter(Boolean);
                      const isBestForItem = price === Math.min(...allPrices);
                      const c = PLATFORM_COLORS[p];
                      return (
                        <td key={p} style={{ padding: '14px 16px', textAlign: 'center', background: isBestForItem ? c.bg : 'transparent' }}>
                          {price ? (
                            <>
                              <div style={{ fontWeight: 700, color: isBestForItem ? c.accent : '#374151', fontSize: 15 }}>
                                ₹{price} {isBestForItem && '⭐'}
                              </div>
                              <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>🚴 {delivery} mins</div>
                            </>
                          ) : (
                            <span style={{ color: '#d1d5db', fontSize: 12 }}>—</span>
                          )}
                        </td>
                      );
                    })}
                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <button onClick={() => onRemove(item.id)} style={{ background: '#fff5f5', border: '1px solid #fecaca', color: '#ef4444', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>✕</button>
                    </td>
                  </tr>
                ))}
                {/* Total Row */}
                <tr style={{ background: '#1f2937', color: '#fff' }}>
                  <td style={{ padding: '16px', fontWeight: 800, fontSize: 14 }}>
                    <div>Grand Total</div>
                    <div style={{ fontSize: 11, fontWeight: 400, color: '#9ca3af', marginTop: 2 }}>Your smart pick: ₹{mixedTotal}</div>
                  </td>
                  {PLATFORMS.map(p => {
                    const total = platformTotals.find(t => t.platform === p)?.total || 0;
                    const isBest = total === platformTotals[0].total;
                    return (
                      <td key={p} style={{ padding: '16px', textAlign: 'center' }}>
                        <div style={{ fontWeight: 800, fontSize: 17, color: isBest ? '#fbbf24' : '#fff' }}>₹{total}</div>
                        {isBest && <div style={{ fontSize: 10, color: '#fbbf24' }}>BEST</div>}
                      </td>
                    );
                  })}
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Smart Recommendation */}
        <div style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          borderRadius: 16,
          padding: '24px 28px',
          color: '#fff',
          marginBottom: 24,
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Decorative glow */}
          <div style={{ position: 'absolute', top: -30, right: -30, width: 120, height: 120, borderRadius: '50%', background: 'rgba(255,107,0,0.15)', filter: 'blur(40px)' }} />
          <div style={{ position: 'relative' }}>
            <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShoppingBag size={20} style={{ color: '#FF6B00' }} /> Smart Shopping Tip
            </div>
            <div style={{ fontSize: 14, opacity: 0.85, marginBottom: 16, lineHeight: 1.6 }}>
              Best deal: Buy everything from <strong style={{ color: '#FFD700' }}>{PLATFORM_COLORS[platformTotals[0].platform].label}</strong> → <strong>₹{platformTotals[0].total}</strong>
              &nbsp;|&nbsp; Fastest: <strong style={{ color: '#a78bfa' }}>{PLATFORM_COLORS[fastestPlatform.platform].label}</strong> (all in {fastestPlatform.maxTime} mins)
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {platformTotals[0].allAvail && (
                <div style={{ background: 'rgba(255,215,0,0.15)', border: '1px solid rgba(255,215,0,0.4)', borderRadius: 8, padding: '6px 14px', fontSize: 13, fontWeight: 600, color: '#FFD700' }}>
                  🏆 Best total: ₹{platformTotals[0].total} on {PLATFORM_COLORS[platformTotals[0].platform].label}
                </div>
              )}
              <div style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, padding: '6px 14px', fontSize: 13, fontWeight: 600, color: '#e5e7eb' }}>
                🧠 Your mix: ₹{mixedTotal}{smartTotal < mixedTotal ? ` · max savings ₹${smartTotal}` : ''}
              </div>
            </div>
          </div>
        </div>

        {/* Platform CTA Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>
          {platformTotals.map(pt => {
            const c = PLATFORM_COLORS[pt.platform];
            return (
              <a key={pt.platform} href={`https://${pt.platform === 'blinkit' ? 'blinkit.com' : pt.platform === 'zepto' ? 'zepto.com' : pt.platform === 'instamart' ? 'swiggy.com/instamart' : 'bigbasket.com'}`}
                target="_blank" rel="noopener noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#fff', borderRadius: 12, padding: '12px 16px', border: `2px solid ${c.bg}`, textDecoration: 'none', boxShadow: '0 2px 8px rgba(0,0,0,.06)', transition: 'box-shadow 0.2s' }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13, color: c.accent, flexShrink: 0 }}>{c.short}</div>
                <div>
                  <div style={{ fontWeight: 700, color: '#111827', fontSize: 13 }}>Shop on {c.label}</div>
                  <div style={{ color: c.accent, fontWeight: 800, fontSize: 15 }}>₹{pt.total}</div>
                </div>
                <span style={{ marginLeft: 'auto', color: c.accent, fontWeight: 700, fontSize: 18 }}>→</span>
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}

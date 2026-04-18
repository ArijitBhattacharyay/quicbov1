import { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import Navbar from '../components/Navbar';
import ProductGrid from '../components/ProductGrid';
import PincodeModal from '../components/PincodeModal';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useSearch } from '../hooks/useSearch';
import { ShoppingCart } from 'lucide-react';
import { prewarmLocation } from '../api';

const PLATFORMS = [
  { id: 'blinkit',   label: 'Blinkit',          color: '#F8D000', emoji: '🟡' },
  { id: 'zepto',     label: 'Zepto',             color: '#8025FB', emoji: '🟣' },
  { id: 'bigbasket', label: 'BigBasket',         color: '#84B527', emoji: '🟢' },
];

function AnimatedHero({ onSearch }) {
  const [inputVal, setInputVal] = useState('');
  const suggestions = ['amul', 'milk', 'bread', 'eggs', 'ghee', 'paneer', 'rice', 'maggi', 'sunfeast'];

  return (
    <div style={{
      width: '100vw',
      position: 'relative',
      left: '50%',
      right: '50%',
      marginLeft: '-50vw',
      marginRight: '-50vw',
      minHeight: '75vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 20px',
      overflow: 'hidden',
    }}>
      {/* Background Image - Real Grocery Vibe like Flipkart */}
      <div style={{
        position: 'absolute',
        inset: '-20px', // Extra space for panning
        backgroundImage: 'url(https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=1600&q=80)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        zIndex: 0,
        animation: 'slowZoom 20s ease-in-out infinite alternate'
      }} />
      
      {/* Dark Gradient Overlay for text readability */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'linear-gradient(to bottom, rgba(0,0,0,0.4), rgba(0,0,0,0.8))',
        zIndex: 1
      }} />

      <div style={{ position: 'relative', zIndex: 10, width: '100%', maxWidth: '800px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        
        {/* Savings counter strip */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
          <div style={{ background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', borderRadius: 20, padding: '6px 16px', color: '#fff', fontSize: 13, fontWeight: 600, border: '1px solid rgba(255,255,255,0.3)' }}>
            💰 Save up to 30%
          </div>
          <div style={{ background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', borderRadius: 20, padding: '6px 16px', color: '#fff', fontSize: 13, fontWeight: 600, border: '1px solid rgba(255,255,255,0.3)' }}>
            ⚡ 10-Min Delivery
          </div>
          <div style={{ background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)', borderRadius: 20, padding: '6px 16px', color: '#fff', fontSize: 13, fontWeight: 600, border: '1px solid rgba(255,255,255,0.3)' }}>
            🏪 4 Apps Compared
          </div>
        </div>

        {/* Hero text */}
        <h1 style={{ fontSize: 'clamp(32px, 6vw, 56px)', fontWeight: 900, textAlign: 'center', color: '#fff', lineHeight: 1.1, marginBottom: 16, letterSpacing: '-1px' }}>
          Fresh Groceries.<br />
          <span style={{ color: '#FFD700' }}>Best Prices Delivered.</span>
        </h1>
        <p style={{ fontSize: 18, color: '#e5e7eb', marginBottom: 36, textAlign: 'center', maxWidth: 540, fontWeight: 500 }}>
          Search once. Compare prices across Blinkit, Zepto, Swiggy Instamart, and BigBasket live.
        </p>

        {/* Inline search */}
        <div style={{ width: '100%', maxWidth: 640, background: '#fff', borderRadius: 16, boxShadow: '0 12px 32px rgba(0,0,0,0.3)', padding: 8, display: 'flex', gap: 8, marginBottom: 28 }}>
          <input
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && inputVal.trim() && onSearch(inputVal.trim())}
            placeholder="Search for amul, sunfeast, oil, rice..."
            style={{ flex: 1, border: 'none', outline: 'none', padding: '14px 20px', fontSize: 16, fontFamily: 'Inter,sans-serif', color: '#111827' }}
          />
          <button
            onClick={() => inputVal.trim() && onSearch(inputVal.trim())}
            style={{ background: '#FF6B00', color: '#fff', border: 'none', borderRadius: 12, padding: '14px 32px', fontWeight: 800, fontSize: 16, cursor: 'pointer', fontFamily: 'Inter,sans-serif', transition: 'background 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.background = '#e65c00'}
            onMouseLeave={e => e.currentTarget.style.background = '#FF6B00'}
          >
            Search
          </button>
        </div>

        {/* Quick suggestions */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
          <span style={{ color: '#fff', fontSize: 14, fontWeight: 600, marginRight: 8, display: 'flex', alignItems: 'center' }}>Trending:</span>
          {suggestions.map(s => (
            <button key={s} onClick={() => onSearch(s)}
              style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.4)', borderRadius: 20, padding: '6px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer', color: '#fff', fontFamily: 'Inter,sans-serif', transition: 'all 0.2s' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.color = '#FF6B00'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.15)'; e.currentTarget.style.color = '#fff'; }}>
              {s}
            </button>
          ))}
        </div>

        {/* Company Logos Row */}
        <div style={{ display: 'flex', gap: 16, marginTop: 48, flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center' }}>
          <span style={{ color: '#d1d5db', fontSize: 13, fontWeight: 600, marginRight: 8, width: '100%', textAlign: 'center', marginBottom: 4 }}>Compare prices across:</span>
          {[
            { name: 'Blinkit', color: '#F8D000', text: '#854d0e' },
            { name: 'Zepto', color: '#8025FB', text: '#fff' },
            { name: 'Swiggy Instamart', color: '#FC8019', text: '#fff' },
            { name: 'BigBasket', color: '#84B527', text: '#fff' }
          ].map((logo, i) => (
            <div key={logo.name} style={{
              background: logo.color, color: logo.text,
              padding: '8px 20px', borderRadius: '8px',
              fontSize: 16, fontWeight: 800,
              boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
              animation: 'floatBadge 4s ease-in-out infinite',
              animationDelay: `${i * 0.5}s`
            }}>
              {logo.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function HomePage({ cartCount, onAddToCart, onCartClick, onLoginClick, initialPincode, initialLocation }) {
  const [showPincodeModal, setShowPincodeModal] = useState(false);
  const [pincode, setPincode] = useState(initialPincode || '110021');
  const [locationLabel, setLocationLabel] = useState(initialLocation || 'Delhi 110021');
  const { results, loading, error, search, reset, lastQuery, cached, searchKey } = useSearch();

  useEffect(() => {
    if (initialPincode) setPincode(initialPincode);
    if (initialLocation) setLocationLabel(initialLocation);
  }, [initialPincode, initialLocation]);

  const handleSearch = (query) => {
    search(query, pincode);
  };

  const handlePincodeConfirm = (code, label) => {
    setPincode(code);
    setLocationLabel(label);
    setShowPincodeModal(false);
    toast.success(`📍 Location set to ${label}`);
    // Pre-warm: set location on all 4 browsers immediately in background
    toast.loading('⚡ Setting up your location on all platforms...', {
      id: 'prewarm',
      duration: 2000,
    });
    prewarmLocation(code).then(result => {
      if (result) {
        toast.success('✅ All platforms ready! Search will be fast.', { id: 'prewarm', duration: 3000 });
      } else {
        toast.dismiss('prewarm');
      }
    });
  };

  const handleAddToCart = (product) => {
    onAddToCart(product);
    toast.success(`Added to cart!`, { icon: '🛒', style: { fontSize: 13 } });
  };

  const hasResults = results?.products?.length > 0;
  const noResults = results && results.products?.length === 0;

  return (
    <>
      <Toaster position="top-right" toastOptions={{ duration: 2000 }} />

      <Navbar pincode={pincode} location={locationLabel} onLocationClick={() => setShowPincodeModal(true)} onLogoClick={reset} onSearch={handleSearch} onLoginClick={onLoginClick} />

      {/* Cart FAB */}
      {cartCount > 0 && (
        <button onClick={onCartClick} style={{ position: 'fixed', bottom: 28, right: 28, width: 56, height: 56, borderRadius: '50%', background: '#FF6B00', color: '#fff', border: 'none', cursor: 'pointer', boxShadow: '0 4px 20px rgba(255,107,0,.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99 }}>
          <ShoppingCart size={22} />
          <span style={{ position: 'absolute', top: -4, right: -4, width: 20, height: 20, background: '#1A73E8', borderRadius: '50%', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #fff' }}>{cartCount}</span>
        </button>
      )}

      <main className="main-container">
        {error && (
          <div style={{ background: '#fff5f5', border: '1px solid #fecaca', borderRadius: 10, padding: '14px 18px', marginBottom: 20 }}>
            <p style={{ fontSize: 14, fontWeight: 600, color: '#dc2626' }}>⚠️ Search failed — {error}</p>
          </div>
        )}

        {loading && (
          <div>
            <div className="search-status">
              <p className="search-status__title">🔍 Searching across platforms...</p>
              <p className="search-status__sub">Comparing prices on all 3 platforms</p>
              <div className="platform-loading-list">
                {PLATFORMS.map((p, i) => (
                  <div
                    className="platform-loading-item"
                    key={p.id}
                    style={{ animationDelay: `${i * 0.2}s` }}
                  >
                    <div className="spinner" style={{ borderTopColor: p.color }} />
                    <span style={{ color: p.color, fontWeight: 600 }}>{p.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="product-grid" style={{ marginTop: 8 }}>
              <LoadingSkeleton count={8} />
            </div>
          </div>
        )}

        {hasResults && !loading && (
          <>
            <div className="page-header">
              <h1>Results for "{lastQuery}" {cached && <span style={{ fontSize: 11, background: '#e8f0fe', color: '#1A73E8', padding: '2px 8px', borderRadius: 10, marginLeft: 8 }}>cached</span>}</h1>
              <p>{results.total} products · {results.location}</p>
            </div>
            <ProductGrid key={searchKey} products={results.products} loading={false} onAddToCart={handleAddToCart} />
          </>
        )}

        {noResults && !loading && (
          <div className="empty-state">
            <span className="empty-state__icon">🔎</span>
            <h2 className="empty-state__title">No results for "{lastQuery}"</h2>
            <p className="empty-state__text">Try searching one of these popular items:</p>
            <div className="empty-state__chips">
              {['amul', 'milk', 'bread', 'eggs', 'ghee', 'paneer', 'rice', 'maggi', 'oil'].map(s => (
                <button key={s} className="empty-state__chip" onClick={() => handleSearch(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {!results && !loading && !error && (
          <AnimatedHero onSearch={handleSearch} />
        )}
      </main>

      {showPincodeModal && (
        <PincodeModal currentPincode={pincode} onConfirm={handlePincodeConfirm} onClose={() => setShowPincodeModal(false)} />
      )}
    </>
  );
}

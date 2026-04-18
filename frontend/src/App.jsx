import { useState, useCallback, useEffect } from 'react';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import CartPage from './pages/CartPage';
import { prewarmLocation } from './api';
import './index.css';

export default function App() {
  const [page, setPage] = useState('landing');
  const [cartItems, setCartItems] = useState([]);

  // Location state — detected on landing page, passed to HomePage
  const [detectedPincode, setDetectedPincode] = useState(null);
  const [detectedLocation, setDetectedLocation] = useState(null);

  const handleAddToCart = (product) => {
    const key = `${product.name}::${product.quantity}`;
    setCartItems(prev => prev.find(p => `${p.name}::${p.quantity}` === key) ? prev : [...prev, product]);
  };
  const handleRemoveFromCart = (id) => setCartItems(prev => prev.filter(p => p.id !== id));

  // Called by LandingPage when geolocation + reverse-geocode succeeds
  const handleLocationDetected = useCallback((pincode, label) => {
    setDetectedPincode(pincode);
    setDetectedLocation(label);

    // Immediately prewarm all 4 scraper browsers with this pincode
    console.log('[App] Starting prewarm...', pincode);
    prewarmLocation(pincode).then(result => {
      if (result) {
        console.log('[App] Prewarm complete — all platforms ready!', result);
      } else {
        console.warn('[App] Prewarm failed');
      }
    });
  }, []);

  return (
    <>
      {page === 'landing' && (
        <div className="page-enter">
          <LandingPage
            onGetStarted={() => setPage('login')}
            onLocationDetected={handleLocationDetected}
          />
        </div>
      )}
      {page === 'login' && (
        <div className="page-enter">
          <LoginPage onLogin={() => setPage('home')} />
        </div>
      )}
      {page === 'home' && (
        <div className="page-enter">
          <HomePage
            cartCount={cartItems.length}
            onAddToCart={handleAddToCart}
            onCartClick={() => setPage('cart')}
            onLoginClick={() => setPage('login')}
            initialPincode={detectedPincode}
            initialLocation={detectedLocation}
          />
        </div>
      )}
      {page === 'cart' && (
        <div className="page-enter">
          <CartPage
            cartItems={cartItems}
            onBack={() => setPage('home')}
            onRemove={handleRemoveFromCart}
          />
        </div>
      )}
    </>
  );
}

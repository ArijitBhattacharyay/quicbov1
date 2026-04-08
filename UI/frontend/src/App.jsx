import { useState } from 'react';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import CartPage from './pages/CartPage';
import './index.css';

export default function App() {
  const [page, setPage] = useState('login');
  const [cartItems, setCartItems] = useState([]);

  const handleAddToCart = (product) => {
    setCartItems(prev => prev.find(p => p.id === product.id) ? prev : [...prev, product]);
  };
  const handleRemoveFromCart = (id) => setCartItems(prev => prev.filter(p => p.id !== id));

  return (
    <>
      {page === 'login' && <LoginPage onLogin={() => setPage('home')} />}
      {page === 'home' && (
        <HomePage
          cartCount={cartItems.length}
          onAddToCart={handleAddToCart}
          onCartClick={() => setPage('cart')}
          onLoginClick={() => setPage('login')}
        />
      )}
      {page === 'cart' && (
        <CartPage
          cartItems={cartItems}
          onBack={() => setPage('home')}
          onRemove={handleRemoveFromCart}
        />
      )}
    </>
  );
}

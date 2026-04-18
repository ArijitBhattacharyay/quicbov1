import { useRef, useEffect, useState } from 'react';
import { MapPin, ChevronDown, Search, User } from 'lucide-react';

export default function Navbar({ pincode, location, onLocationClick, onLogoClick, onSearch, onLoginClick }) {
  const inputRef = useRef(null);
  const navRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const query = inputRef.current?.value?.trim();
    if (query) {
      onSearch(query);
      inputRef.current.value = '';
    }
  };

  const displayLocation = location || (pincode ? pincode : 'Select Location');

  return (
    <nav ref={navRef} className={`navbar${scrolled ? ' scrolled' : ''}`}>
      <button className="navbar__logo" onClick={onLogoClick} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
        quicbo
      </button>
      <div className="divider" />

      <button className="navbar__location" onClick={onLocationClick}>
        <MapPin size={16} color="#FF6B00" />
        <div className="navbar__location-text">
          <span className="navbar__location-label">Deliver to</span>
          <span className="navbar__location-value">
            {displayLocation}
            <span className="navbar__location-edit">✎</span>
            <ChevronDown size={12} />
          </span>
        </div>
      </button>

      {/* FORM ONLY — no onKeyDown, form natively handles Enter key */}
      <form className="navbar__search" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          className="navbar__search-input"
          type="text"
          placeholder="Search fresh groceries..."
          id="main-search-input"
          autoComplete="off"
        />
        <button type="submit" className="navbar__search-btn" aria-label="Search">
          <Search size={17} />
        </button>
      </form>

      <button
        className="navbar__profile"
        onClick={onLoginClick}
        aria-label="Profile"
        style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#e5e7eb', borderRadius: '20px', padding: '6px 12px', fontSize: '14px', fontWeight: 'bold', color: '#111827', cursor: 'pointer', border: 'none' }}
      >
        <User size={16} /> Login
      </button>
    </nav>
  );
}

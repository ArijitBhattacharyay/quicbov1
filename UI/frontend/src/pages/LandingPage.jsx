import React, { useEffect, useState } from 'react';
import { reverseGeocode } from '../api';
import './LandingPage.css';

export default function LandingPage({ onGetStarted, onLocationDetected }) {
  const [locationStatus, setLocationStatus] = useState('idle'); // idle | detecting | success | denied | error
  const [detectedLocation, setDetectedLocation] = useState(null);

  useEffect(() => {
    // Navbar scroll effect
    const handleScroll = () => {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        if (window.scrollY > 50) {
          navbar.style.background = 'rgba(255, 255, 255, 0.9)';
          navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.05)';
        } else {
          navbar.style.background = 'rgba(255, 255, 255, 0.7)';
          navbar.style.boxShadow = 'none';
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    
    // Animation for items
    const mockItems = document.querySelectorAll('.mock-item, .mock-summary');
    mockItems.forEach((item, index) => {
      item.style.opacity = '0';
      item.style.transform = 'translateY(20px)';
      item.style.transition = 'all 0.5s ease ' + (index * 0.2) + 's';
      
      setTimeout(() => {
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
      }, 500);
    });

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const fetchLocation = (proceedToNextPage = false) => {
    if (!navigator.geolocation) {
      setLocationStatus('error');
      if (proceedToNextPage) onGetStarted();
      return;
    }

    setLocationStatus('detecting');

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const data = await reverseGeocode(latitude, longitude);
          setDetectedLocation(data);
          setLocationStatus('success');
          if (onLocationDetected) {
            onLocationDetected(data.pincode, data.full_label);
          }
          if (proceedToNextPage) onGetStarted();
        } catch (err) {
          console.warn('[Location] Reverse geocode failed:', err);
          setLocationStatus('error');
          if (proceedToNextPage) onGetStarted();
        }
      },
      (err) => {
        console.warn('[Location] Permission denied or error:', err.message);
        setLocationStatus(err.code === 1 ? 'denied' : 'error');
        if (proceedToNextPage) onGetStarted();
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000,
      }
    );
  };

  // Ask for location right away when the page loads (or is refreshed)
  useEffect(() => {
    fetchLocation(false);
  }, []);

  const handleGetStarted = () => {
    // If successfully located, just proceed. Otherwise, try again.
    if (locationStatus === 'success') {
      onGetStarted();
    } else {
      fetchLocation(true);
    }
  };

  return (
    <div className="landing-wrapper">
      <div className="blob-bg"></div>

      <nav className="navbar">
        <div className="nav-container">
          <a href="#" className="logo-link">
            <img src="/quicbo.in.png" alt="Quicbo Logo" className="logo-img" />
          </a>

          {/* Location status indicator in navbar */}
          <div className="lp-location-status">
            {locationStatus === 'detecting' && (
              <div className="lp-location-badge lp-location-detecting">
                <span className="lp-location-pulse"></span>
                <span>Detecting your location…</span>
              </div>
            )}
            {locationStatus === 'success' && detectedLocation && (
              <div className="lp-location-badge lp-location-success">
                <span className="lp-location-pin">📍</span>
                <span>{detectedLocation.full_label}</span>
                <span className="lp-location-check">✓</span>
              </div>
            )}
            {locationStatus === 'denied' && (
              <div className="lp-location-badge lp-location-denied">
                <span>📍 Location access needed for best results</span>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="hero">
        <div className="container hero-container">
          <div className="hero-content">
            <div className="badge">🚀 The Ultimate Comparison Tool</div>
            <h1 className="hero-title">One App for Comparing <span>Everything</span></h1>
            <p className="hero-subtitle">
              From 10 Minutes to 10 AM—Every Deal, Every App, One Dashboard.
            </p>

            {/* Location detected banner */}
            {locationStatus === 'success' && detectedLocation && (
              <div className="lp-detected-banner">
                <div className="lp-detected-icon">📍</div>
                <div className="lp-detected-text">
                  <strong>Location detected!</strong>
                  <span>{detectedLocation.city || detectedLocation.district}, {detectedLocation.state} — {detectedLocation.pincode}</span>
                </div>
                <div className="lp-detected-badge">Ready to compare ⚡</div>
              </div>
            )}

            <div className="hero-actions">
              <button className="btn-primary" onClick={handleGetStarted}>
                {locationStatus === 'detecting' ? 'Detecting Location...' : (locationStatus === 'success' ? '⚡ Get Started — Location Ready!' : 'Get Started Now')}
              </button>
              <a href="#about" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-block', textAlign: 'center' }}>Learn More</a>
            </div>
          </div>
          
          <div className="hero-visual">
            <div className="glass-card main-card">
              <div className="card-header">
                <div className="circle"></div>
                <div className="circle"></div>
                <div className="circle"></div>
              </div>
              <div className="card-body">
                <div className="mock-item">
                  <div className="mock-info">
                    <div className="mock-logo zepto">Z</div>
                    <div>
                      <h4>Grocery Item</h4>
                      <p>10 mins</p>
                    </div>
                  </div>
                  <h3 className="price orange">₹45</h3>
                </div>
                <div className="mock-item">
                  <div className="mock-info">
                    <div className="mock-logo blinkit">B</div>
                    <div>
                      <h4>Grocery Item</h4>
                      <p>12 mins</p>
                    </div>
                  </div>
                  <h3 className="price">₹50</h3>
                </div>
                <div className="mock-item">
                  <div className="mock-info">
                    <div className="mock-logo amazon">a</div>
                    <div>
                      <h4>Electronics</h4>
                      <p>Next Day</p>
                    </div>
                  </div>
                  <h3 className="price orange">₹64k</h3>
                </div>
                <div className="mock-item">
                  <div className="mock-info">
                    <div className="mock-logo flipkart">f</div>
                    <div>
                      <h4>Electronics</h4>
                      <p>3 Days</p>
                    </div>
                  </div>
                  <h3 className="price">₹65k</h3>
                </div>
                <div className="mock-summary">
                  <span>Best Deal Found!</span>
                  <span className="orange-text">Save ₹5 and 2 mins</span>
                </div>
              </div>
            </div>
            <div className="glass-card small-card floating-1">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
              <span>Save Time</span>
            </div>
            <div className="glass-card small-card floating-2">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
              <span>Save Money</span>
            </div>
          </div>
        </div>
      </main>

      <section className="coming-soon-banner">
        <div className="container">
          <div className="coming-soon-content">
            <span className="pulse-dot"></span>
            <h2>quicbo is <span className="orange-text">Coming Soon</span></h2>
            <p>We're putting the finishing touches on the ultimate comparison engine. Get ready to save time and money like never before.</p>
          </div>
        </div>
      </section>

      <section id="about" className="about-section">
        <div className="container about-container">
          <div className="about-header">
            <h2>About <span className="orange-text">quicbo</span></h2>
            <h3>Your All-in-One Shopping Intelligence</h3>
            <p>The digital marketplace is massive, but finding the best deal shouldn't be a full-time job. quicbo is a powerful commerce aggregator built to give you total clarity. Whether you need groceries in 10 minutes or a laptop by tomorrow, we scan the entire internet to find you the best price and the fastest delivery.</p>
          </div>

          <div className="about-grid">
            <div className="about-card">
              <div className="card-icon">⚡</div>
              <h4>Why quicbo?</h4>
              <p>The same product can have different prices, delivery fees, and arrival times across Amazon, Flipkart, Blinkit, Zepto, Myntra and many more. Checking them all manually is exhausting. <span className="orange-text">quicbo</span> eliminates the guesswork by consolidating the entire retail landscape into one seamless dashboard.</p>
            </div>
            <div className="about-card">
              <div className="card-icon">🎯</div>
              <h4>Our Mission</h4>
              <p>To build the world's most transparent shopping experience. We believe that shoppers deserve the full picture before they hit "buy." Our mission is to save you every possible rupee and every spare minute, making commerce simple, fast, and fair.</p>
            </div>
          </div>

          <div className="features-wrapper">
            <h3>What quicbo Does For You</h3>
            <div className="features-grid">
              <div className="feature-item">
                <h5>Universal Price Comparison</h5>
                <p>Daily milk to high-end electronics, compare prices across quick-commerce apps and giant marketplaces instantly.</p>
              </div>
              <div className="feature-item">
                <h5>Speed vs. Savings</h5>
                <p>We show you the trade-off. Choose "Quickest" for immediate needs or "Cheapest" for planned purchases.</p>
              </div>
              <div className="feature-item">
                <h5>Inventory Tracking</h5>
                <p>If an item is sold out, quicbo finds where it's still in stock, saving you from frustration.</p>
              </div>
              <div className="feature-item">
                <h5>Unified Search</h5>
                <p>One search bar to rule them all. No more switching tabs; find everything in one place.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

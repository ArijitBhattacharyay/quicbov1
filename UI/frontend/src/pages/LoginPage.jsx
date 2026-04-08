import { useState, useRef, useEffect } from 'react';

export default function LoginPage({ onLogin }) {
  const [step, setStep] = useState('phone'); // 'phone' | 'otp'
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [timer, setTimer] = useState(0);
  const [error, setError] = useState('');
  const otpRefs = useRef([]);
  const timerRef = useRef(null);

  const startTimer = () => {
    setTimer(30);
    timerRef.current = setInterval(() => {
      setTimer(t => {
        if (t <= 1) { clearInterval(timerRef.current); return 0; }
        return t - 1;
      });
    }, 1000);
  };

  const handleSendOtp = (e) => {
    e?.preventDefault();
    if (phone.length !== 10) { setError('Enter a valid 10-digit mobile number'); return; }
    setError('');
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setStep('otp');
      startTimer();
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    }, 1200);
  };

  const handleOtpChange = (val, idx) => {
    if (!/^\d*$/.test(val)) return;
    const next = [...otp];
    next[idx] = val.slice(-1);
    setOtp(next);
    if (val && idx < 5) otpRefs.current[idx + 1]?.focus();
  };

  const handleOtpKey = (e, idx) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) otpRefs.current[idx - 1]?.focus();
  };

  const handleVerify = (e) => {
    e?.preventDefault();
    const code = otp.join('');
    if (code.length < 6) { setError('Enter the 6-digit OTP'); return; }
    if (code !== '123456') { setError('Invalid OTP. Please enter 123456'); return; }
    setError('');
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(); }, 1000);
  };

  const handleResend = () => {
    if (timer > 0) return;
    setOtp(['', '', '', '', '', '']);
    setError('');
    startTimer();
    setTimeout(() => otpRefs.current[0]?.focus(), 100);
  };

  return (
    <div style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter,sans-serif' }}>

      {/* Animated gradient background */}
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, #FF6B00 0%, #FF9A3C 40%, #1A73E8 100%)', zIndex: 0 }}>
        {/* Floating circles */}
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{
            position: 'absolute',
            width: [120, 80, 160, 60, 200, 90][i],
            height: [120, 80, 160, 60, 200, 90][i],
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.08)',
            top: ['10%', '60%', '30%', '80%', '5%', '50%'][i],
            left: ['5%', '80%', '60%', '15%', '85%', '40%'][i],
            animation: `floatBubble ${[6, 4, 8, 5, 7, 6][i]}s ease-in-out infinite`,
            animationDelay: `${[0, 1, 2, 0.5, 1.5, 3][i]}s`,
          }} />
        ))}
      </div>

      {/* Floating food emojis */}
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 1 }}>
        {['🥛', '🧈', '🍞', '🥚', '🍚', '🫙', '🍜', '🍪'].map((emoji, i) => (
          <div key={i} style={{
            position: 'absolute',
            fontSize: [28, 22, 32, 20, 26, 24, 28, 22][i],
            top: [`${5 + i * 12}%`],
            left: [`${10 + i * 10}%`],
            animation: `foodFloat ${4 + i * 0.5}s ease-in-out infinite`,
            animationDelay: `${i * 0.4}s`,
            opacity: 0.6,
          }}>{emoji}</div>
        ))}
      </div>

      {/* Login Card */}
      <div style={{
        position: 'relative', zIndex: 10,
            width: '100%', maxWidth: 420, margin: '16px',
            background: 'rgba(255,255,255,0.95)',
            backdropFilter: 'blur(20px)',
            borderRadius: 24, padding: '40px 36px',
            boxShadow: '0 24px 60px rgba(0,0,0,0.25)',
          }}>
            {/* Logo */}
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
              <div style={{ fontSize: 44, fontWeight: 900, color: '#FF6B00', letterSpacing: '-2.5px', lineHeight: 1 }}>quicbo</div>
              <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4, fontWeight: 500 }}>Compare prices. Save more. Every time.</div>
            </div>

            {step === 'phone' ? (
              <form onSubmit={handleSendOtp}>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 6 }}>Welcome back 👋</div>
                <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 24 }}>Enter your phone number to continue</div>

            <div style={{ display: 'flex', border: '2px solid #e5e7eb', borderRadius: 12, overflow: 'hidden', marginBottom: 16, transition: 'border-color 0.2s' }}
              onFocus={e => e.currentTarget.style.borderColor = '#FF6B00'}
              onBlur={e => e.currentTarget.style.borderColor = '#e5e7eb'}>
              <div style={{ padding: '14px 16px', background: '#f9fafb', borderRight: '1.5px solid #e5e7eb', color: '#374151', fontWeight: 600, fontSize: 15, flexShrink: 0 }}>🇮🇳 +91</div>
              <input
                type="tel" inputMode="numeric" maxLength={10}
                placeholder="10-digit mobile number"
                value={phone}
                onChange={e => { setPhone(e.target.value.replace(/\D/g, '')); setError(''); }}
                style={{ flex: 1, padding: '14px 16px', border: 'none', outline: 'none', fontSize: 16, fontFamily: 'Inter,sans-serif', letterSpacing: 1, color: '#111827' }}
                autoFocus
              />
            </div>

            {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12, fontWeight: 500 }}>⚠️ {error}</div>}

            <button type="submit" disabled={loading}
              style={{ width: '100%', padding: '14px', borderRadius: 12, border: 'none', cursor: loading ? 'not-allowed' : 'pointer', background: loading ? '#f0f0f0' : 'linear-gradient(135deg,#FF6B00,#FF9A3C)', color: loading ? '#9ca3af' : '#fff', fontWeight: 700, fontSize: 16, transition: 'all 0.2s', fontFamily: 'Inter,sans-serif' }}>
              {loading ? '⏳ Sending OTP...' : 'Get OTP →'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 20 }}>
              <button type="button" onClick={onLogin}
                style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: 13, cursor: 'pointer', textDecoration: 'underline' }}>
                Skip for now →
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleVerify}>
            <button type="button" onClick={() => { setStep('phone'); setOtp(['','','','','','']); setError(''); }}
              style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: 13, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 4 }}>
              ← Change number
            </button>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginBottom: 4 }}>Verify OTP 📲</div>
            <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 24 }}>We sent a 6-digit OTP to +91 {phone}. Use <strong>123456</strong> to login.</div>

            {/* OTP Boxes */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 20, justifyContent: 'center' }}>
              {otp.map((d, i) => (
                <input key={i} ref={el => otpRefs.current[i] = el}
                  type="tel" inputMode="numeric" maxLength={1}
                  value={d}
                  onChange={e => handleOtpChange(e.target.value, i)}
                  onKeyDown={e => handleOtpKey(e, i)}
                  style={{ width: 44, height: 52, textAlign: 'center', fontSize: 22, fontWeight: 700, border: `2.5px solid ${d ? '#FF6B00' : '#e5e7eb'}`, borderRadius: 12, outline: 'none', color: '#111827', fontFamily: 'Inter,sans-serif', background: d ? '#fff7ed' : '#fff', transition: 'all 0.15s' }}
                />
              ))}
            </div>

            {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12, fontWeight: 500, textAlign: 'center' }}>⚠️ {error}</div>}

            <button type="submit" disabled={loading}
              style={{ width: '100%', padding: '14px', borderRadius: 12, border: 'none', cursor: loading ? 'not-allowed' : 'pointer', background: loading ? '#f0f0f0' : 'linear-gradient(135deg,#FF6B00,#FF9A3C)', color: loading ? '#9ca3af' : '#fff', fontWeight: 700, fontSize: 16, fontFamily: 'Inter,sans-serif' }}>
              {loading ? '✓ Verifying...' : 'Verify & Continue →'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13 }}>
              {timer > 0
                ? <span style={{ color: '#9ca3af' }}>Resend OTP in <strong style={{ color: '#FF6B00' }}>{timer}s</strong></span>
                : <button type="button" onClick={handleResend}
                    style={{ background: 'none', border: 'none', color: '#FF6B00', fontWeight: 600, cursor: 'pointer', fontSize: 13 }}>Resend OTP</button>
              }
            </div>
          </form>
        )}

        {/* Platform badges */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 28, flexWrap: 'wrap' }}>
          {[{ label: 'Blinkit', color: '#F8D000', text: '#854d0e' }, { label: 'Zepto', color: '#8025FB', text: '#fff' }, { label: 'Instamart', color: '#FC8019', text: '#fff' }, { label: 'BigBasket', color: '#84B527', text: '#fff' }].map(p => (
            <div key={p.label} style={{ background: p.color, color: p.text, borderRadius: 6, padding: '3px 8px', fontSize: 10, fontWeight: 700 }}>{p.label}</div>
          ))}
        </div>
        <div style={{ textAlign: 'center', fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Live prices from all major platforms</div>
      </div>

      <style>{`
        @keyframes floatBubble {
          0%,100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-20px) scale(1.05); }
        }
        @keyframes foodFloat {
          0%,100% { transform: translateY(0) rotate(-5deg); opacity: 0.5; }
          50% { transform: translateY(-15px) rotate(5deg); opacity: 0.8; }
        }
      `}</style>
    </div>
  );
}

export default function LoadingSkeleton({ count = 8 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton skeleton-image" />
          <div className="skeleton-body">
            <div className="skeleton skeleton-line" style={{ width: '85%' }} />
            <div className="skeleton skeleton-line" style={{ width: '55%' }} />
            <div
              className="skeleton skeleton-line"
              style={{ width: '100%', height: 54, borderRadius: 8, marginTop: 4 }}
            />
            <div
              className="skeleton skeleton-line"
              style={{ width: '100%', height: 32, borderRadius: 8 }}
            />
            <div
              className="skeleton skeleton-line"
              style={{ width: '100%', height: 36, borderRadius: 8 }}
            />
          </div>
        </div>
      ))}
    </>
  );
}

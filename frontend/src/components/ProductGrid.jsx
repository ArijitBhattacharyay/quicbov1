import ProductCard from './ProductCard';
import LoadingSkeleton from './LoadingSkeleton';

export default function ProductGrid({ products, loading, onAddToCart }) {
  if (loading) {
    return (
      <div className="product-grid">
        <LoadingSkeleton count={8} />
      </div>
    );
  }

  if (!products || products.length === 0) return null;

  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          onAddToCart={onAddToCart}
        />
      ))}
    </div>
  );
}

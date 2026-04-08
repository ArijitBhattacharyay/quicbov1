/**
 * Platform brand colors, logos (emoji fallbacks), and metadata.
 */
export const PLATFORMS = {
  blinkit: {
    id: 'blinkit',
    label: 'Blinkit',
    color: '#F8D000',
    textColor: '#1a1a1a',
    emoji: '🟡',
    shortLabel: 'BL',
    url: 'https://blinkit.com',
  },
  zepto: {
    id: 'zepto',
    label: 'Zepto',
    color: '#8025FB',
    textColor: '#fff',
    emoji: '🟣',
    shortLabel: 'Z',
    url: 'https://www.zepto.com',
  },
  instamart: {
    id: 'instamart',
    label: 'Swiggy Instamart',
    shortLabel: 'SI',
    color: '#FC8019',
    textColor: '#fff',
    emoji: '🟠',
    url: 'https://www.swiggy.com/instamart',
  },
  bigbasket: {
    id: 'bigbasket',
    label: 'BigBasket',
    shortLabel: 'BB',
    color: '#84B527',
    textColor: '#fff',
    emoji: '🟢',
    url: 'https://www.bigbasket.com',
  },
};

export function getPlatform(id) {
  return PLATFORMS[id] || {
    id,
    label: id,
    color: '#999',
    textColor: '#fff',
    shortLabel: id.substring(0, 2).toUpperCase(),
    url: '#',
  };
}

export function formatPrice(price) {
  if (price == null) return 'N/A';
  return `₹${price.toFixed(0)}`;
}

export function formatDelivery(mins) {
  if (!mins) return 'N/A';
  return `${mins} min`;
}

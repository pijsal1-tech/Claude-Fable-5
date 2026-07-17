// Utility helpers used by app.js (call-site fixture for symbol tests).
export function formatPrice(amount) {
  return '$' + amount.toFixed(2);
}

export function applyDiscount(amount, percent) {
  return amount * (1 - percent / 100);
}

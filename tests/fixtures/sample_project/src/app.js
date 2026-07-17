// Entry point of the fixture app.
import { formatPrice, applyDiscount } from './utils.js';

function renderTitle(price) {
  const el = document.getElementById('title');
  el.textContent = 'Total: ' + formatPrice(applyDiscount(price, 10));
}

renderTitle(100);

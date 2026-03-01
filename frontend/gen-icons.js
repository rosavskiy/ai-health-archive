const fs = require('fs');
const path = require('path');
const dir = path.join(__dirname, 'public', 'icons');
fs.mkdirSync(dir, { recursive: true });

function makeSvg(size) {
  const cx = size / 2;
  const w = size * 0.18;
  const h = size * 0.42;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
  <rect width="${size}" height="${size}" rx="${size * 0.2}" fill="#0ea5e9"/>
  <rect x="${cx - w / 2}" y="${cx - h / 2}" width="${w}" height="${h}" rx="4" fill="white"/>
  <rect x="${cx - h / 2}" y="${cx - w / 2}" width="${h}" height="${w}" rx="4" fill="white"/>
</svg>`;
}

// Write SVGs (browsers and service workers accept SVG, and we'll also serve them as fallback)
fs.writeFileSync(path.join(dir, 'icon-192.svg'), makeSvg(192));
fs.writeFileSync(path.join(dir, 'icon-512.svg'), makeSvg(512));
fs.writeFileSync(path.join(dir, 'badge-72.svg'), makeSvg(72));

// Create minimal valid 1x1 PNG as placeholder for actual PNG paths
// This is a base64-encoded 192x192 blue PNG with white cross
// We redirect manifest.json to use .svg icons instead
console.log('SVG icons created in public/icons/');
console.log('Files:', fs.readdirSync(dir));

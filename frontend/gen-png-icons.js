// Generates minimal valid PNG icons using pure Node.js (no deps)
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const dir = path.join(__dirname, 'public', 'icons');
fs.mkdirSync(dir, { recursive: true });

function makePng(size) {
  const bg = { r: 14, g: 165, b: 233 };   // brand-500 #0ea5e9
  const fg = { r: 255, g: 255, b: 255 };  // white

  // Draw pixels
  const pixels = [];
  for (let y = 0; y < size; y++) {
    const row = [];
    for (let x = 0; x < size; x++) {
      const cx = size / 2, cy = size / 2;
      const bw = size * 0.18, bh = size * 0.42;
      const inCross =
        (Math.abs(x - cx) < bw / 2 && Math.abs(y - cy) < bh / 2) ||
        (Math.abs(x - cx) < bh / 2 && Math.abs(y - cy) < bw / 2);
      const c = inCross ? fg : bg;
      row.push(c.r, c.g, c.b);
    }
    pixels.push(row);
  }

  // Build raw scanlines (filter byte 0 per row)
  const rawRows = pixels.map(row => Buffer.concat([Buffer.from([0]), Buffer.from(row)]));
  const rawData = zlib.deflateSync(Buffer.concat(rawRows));

  function chunk(type, data) {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const typeB = Buffer.from(type);
    const crc = crc32(Buffer.concat([typeB, data]));
    const crcB = Buffer.alloc(4); crcB.writeUInt32BE(crc >>> 0);
    return Buffer.concat([len, typeB, data, crcB]);
  }

  function crc32(buf) {
    let crc = -1;
    const table = makeCrcTable();
    for (const b of buf) crc = (table[(crc ^ b) & 0xff] ^ (crc >>> 8));
    return (crc ^ -1);
  }

  function makeCrcTable() {
    const t = new Int32Array(256);
    for (let i = 0; i < 256; i++) {
      let c = i;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      t[i] = c;
    }
    return t;
  }

  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(size, 0);
  ihdrData.writeUInt32BE(size, 4);
  ihdrData[8] = 8;  // bit depth
  ihdrData[9] = 2;  // color type RGB
  ihdrData[10] = 0; ihdrData[11] = 0; ihdrData[12] = 0;

  return Buffer.concat([sig, chunk('IHDR', ihdrData), chunk('IDAT', rawData), chunk('IEND', Buffer.alloc(0))]);
}

for (const size of [72, 192, 512]) {
  const png = makePng(size);
  fs.writeFileSync(path.join(dir, `icon-${size}.png`), png);
  console.log(`icon-${size}.png created (${png.length} bytes)`);
}

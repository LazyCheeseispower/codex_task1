import { FOOD_DB } from '../data/foodDb.js';

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function rgbToHsl(r, g, b) {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) * 60;
    else if (max === gn) h = ((bn - rn) / d + 2) * 60;
    else h = ((rn - gn) / d + 4) * 60;
  }
  return [h, s, l];
}

function classifyHsl(h, s, l) {
  if (s < 0.1) {
    if (l > 0.84) return 'white';
    if (l < 0.3) return 'dark';
    return 'neutral';
  }
  if (h >= 70 && h <= 165) return 'green';
  if (h >= 40 && h < 70) return 'yellow';
  if (h >= 15 && h < 40) return s < 0.45 && l < 0.6 ? 'brown' : 'orange';
  if (h >= 0 && h < 15) return s < 0.5 && l < 0.55 ? 'brown' : 'red';
  if (h >= 340) return s < 0.5 && l < 0.55 ? 'brown' : 'red';
  if (h >= 165 && h <= 230) return 'teal';
  if (h > 230 && h < 340) return s < 0.4 ? 'neutral' : 'pink';
  return 'neutral';
}

function colorDistance(a, b) {
  return Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2);
}

function extractFeatures(ctx) {
  const size = ctx.canvas.width;
  const imageData = ctx.getImageData(0, 0, size, size);
  const data = imageData.data;
  const counts = { white: 0, yellow: 0, orange: 0, red: 0, brown: 0, green: 0, dark: 0, neutral: 0, pink: 0, teal: 0 };
  const margin = Math.floor(size * 0.1);
  let total = 0;
  let satSum = 0;
  let edgeSum = 0;
  let edgeN = 0;

  const cornerPoints = [
    [4, 4],
    [size - 5, 4],
    [4, size - 5],
    [size - 5, size - 5]
  ];
  const corners = cornerPoints.map(([cx, cy]) => {
    let r = 0;
    let g = 0;
    let b = 0;
    let n = 0;
    for (let dy = -8; dy <= 8; dy += 2) {
      for (let dx = -8; dx <= 8; dx += 2) {
        const px = Math.max(0, Math.min(size - 1, cx + dx));
        const py = Math.max(0, Math.min(size - 1, cy + dy));
        const idx = (py * size + px) * 4;
        r += data[idx];
        g += data[idx + 1];
        b += data[idx + 2];
        n += 1;
      }
    }
    return [r / n, g / n, b / n];
  });
  const bg = corners.reduce(
    (acc, c) => [acc[0] + c[0] / 4, acc[1] + c[1] / 4, acc[2] + c[2] / 4],
    [0, 0, 0]
  );

  let foreground = 0;
  for (let y = margin; y < size - margin; y += 2) {
    let prevLum = null;
    for (let x = margin; x < size - margin; x += 2) {
      const idx = (y * size + x) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const [h, s, l] = rgbToHsl(r, g, b);
      const cat = classifyHsl(h, s, l);
      counts[cat] += 1;
      total += 1;
      satSum += s;
      if (colorDistance([r, g, b], bg) > 34 || s > 0.28) foreground += 1;
      const lum = r * 0.299 + g * 0.587 + b * 0.114;
      if (prevLum !== null) {
        edgeSum += Math.abs(lum - prevLum);
        edgeN += 1;
      }
      prevLum = lum;
    }
  }

  const normalized = {};
  Object.keys(counts).forEach((key) => {
    normalized[key] = counts[key] / total;
  });

  return {
    ...normalized,
    coverage: Math.min(0.9, Math.max(0.2, foreground / total)),
    satAvg: satSum / total,
    edgeDensity: edgeN ? Math.min(1, edgeSum / (edgeN * 40)) : 0.2
  };
}

function pickFoods(feat) {
  const keys = ['white', 'yellow', 'orange', 'red', 'brown', 'green', 'dark', 'neutral', 'pink', 'teal'];
  const scored = FOOD_DB.map((food) => {
    let score = 0;
    keys.forEach((key) => {
      score += (food.sig[key] || 0) * (feat[key] || 0);
    });
    score += feat.coverage * 0.05;
    if (food.complex && feat.edgeDensity > 0.24) score += 0.045;
    return { food, score: score + Math.random() * 0.008 };
  }).sort((a, b) => b.score - a.score);

  const chosen = [];
  const groups = new Set();
  for (const item of scored) {
    if (chosen.length >= 3) break;
    if (groups.has(item.food.group)) continue;
    groups.add(item.food.group);
    chosen.push(item.food);
  }
  if (!chosen.length) chosen.push(FOOD_DB[0]);

  const factor = 0.7 + feat.coverage * 0.8;
  return chosen.map((food) => {
    let grams = Math.round(((food.grams || 150) * factor) / 5) * 5;
    grams = Math.max(30, Math.min(500, grams));
    return {
      id: food.id,
      name: food.name,
      kcal: food.kcal,
      p: food.p,
      c: food.c,
      f: food.f,
      grams,
      color: food.color,
      group: food.group
    };
  });
}

export async function analyzeImage(dataUrl) {
  const img = await loadImage(dataUrl);
  const size = 160;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const scale = Math.max(size / img.naturalWidth, size / img.naturalHeight);
  const w = img.naturalWidth * scale;
  const h = img.naturalHeight * scale;
  ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);

  const feat = extractFeatures(ctx);
  const items = pickFoods(feat);
  const confidence = Math.min(0.96, Math.max(0.62, 0.58 + feat.coverage * 0.1 + feat.satAvg * 0.32 + feat.edgeDensity * 0.18));
  return { items, confidence, features: feat };
}

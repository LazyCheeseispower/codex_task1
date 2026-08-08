function ellipse(ctx, x, y, rx, ry, fill) {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

function circle(ctx, x, y, r, fill) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

function roundedRect(ctx, x, y, w, h, r, fill) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
}

function drawRiceTomatoEgg(ctx, w, h) {
  ctx.fillStyle = '#e6d7b8';
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 8; i += 1) {
    ctx.fillStyle = 'rgba(160,130,90,.08)';
    ctx.fillRect(0, (i * 34 + 10) % h, w, 2);
  }
  ellipse(ctx, w / 2, h / 2 + 12, 128, 98, 'rgba(60,42,24,.18)');
  ellipse(ctx, w / 2, h / 2 + 4, 126, 96, '#ffffff');
  ellipse(ctx, w / 2, h / 2 + 4, 106, 78, '#f6f3ea');
  ellipse(ctx, 118, 110, 52, 36, '#f7f1e2');
  ellipse(ctx, 118, 124, 46, 20, 'rgba(0,0,0,.05)');
  circle(ctx, 206, 108, 23, '#f4a93d');
  circle(ctx, 228, 128, 19, '#e8663c');
  circle(ctx, 196, 134, 17, '#f2c14f');
  circle(ctx, 222, 100, 14, '#ef8f35');
  circle(ctx, 208, 148, 13, '#d94a45');
  circle(ctx, 236, 150, 11, '#f0b04c');
  const scallions = [[158, 102], [168, 114], [180, 104], [172, 128], [190, 120], [150, 126], [160, 140]];
  scallions.forEach(([x, y]) => circle(ctx, x, y, 3, '#79a95c'));
}

function drawChickenBroccoli(ctx, w, h) {
  ctx.fillStyle = '#ece7db';
  ctx.fillRect(0, 0, w, h);
  ellipse(ctx, w / 2, h / 2 + 10, 128, 98, 'rgba(70,58,42,.14)');
  ellipse(ctx, w / 2, h / 2 + 2, 126, 96, '#ffffff');
  ellipse(ctx, w / 2, h / 2 + 2, 104, 76, '#f7f4ec');
  ellipse(ctx, 150, 192, 44, 26, '#f7f1e2');
  ellipse(ctx, 150, 198, 38, 18, 'rgba(0,0,0,.05)');
  roundedRect(ctx, 102, 102, 66, 30, 12, '#d9b98a');
  roundedRect(ctx, 116, 138, 58, 26, 11, '#cfa97d');
  ctx.fillStyle = 'rgba(140,105,70,.35)';
  ctx.fillRect(118, 110, 34, 3);
  ctx.fillRect(130, 146, 30, 3);
  const florets = [[232, 104, 22, '#4e7a3a'], [252, 122, 20, '#5f8c46'], [218, 124, 18, '#437031'], [244, 146, 16, '#56853f']];
  florets.forEach(([x, y, r, fill]) => circle(ctx, x, y, r, fill));
  [[236, 100, '#8ab569'], [222, 120, '#7fae5a'], [248, 140, '#8ab569']].forEach(([x, y, fill]) => circle(ctx, x, y, 4, fill));
  circle(ctx, 272, 190, 17, '#f3cf55');
  circle(ctx, 272, 190, 12, '#f8e49b');
}

function drawBeefNoodle(ctx, w, h) {
  ctx.fillStyle = '#6b5b4e';
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 7; i += 1) {
    ctx.fillStyle = 'rgba(30,20,12,.10)';
    ctx.fillRect(0, (i * 42 + 18) % h, w, 2);
  }
  ellipse(ctx, w / 2, h / 2 + 16, 132, 102, 'rgba(20,12,8,.28)');
  ellipse(ctx, w / 2, h / 2 + 6, 130, 100, '#f0eadc');
  ellipse(ctx, w / 2, h / 2 + 6, 112, 84, '#a4632e');
  ctx.strokeStyle = '#e0bc82';
  ctx.lineWidth = 6;
  ctx.lineCap = 'round';
  const noodleArcs = [[-52, -12, 92, 0.5, 1.5], [-10, 26, 72, 2.2, 3.6], [36, -20, 78, 1.2, 2.6], [-28, 52, 64, 1.6, 3.1]];
  noodleArcs.forEach(([x, y, r, a0, a1]) => {
    ctx.beginPath();
    ctx.arc(w / 2 + x, h / 2 + y, r, a0, a1);
    ctx.stroke();
  });
  const beef = [[128, 126, 40, 24, '#6e3c28'], [196, 148, 44, 26, '#7d452b'], [176, 112, 36, 22, '#5f331f']];
  beef.forEach(([x, y, bw, bh, fill]) => roundedRect(ctx, x, y, bw, bh, 7, fill));
  const greens = [[148, 104], [188, 106], [214, 130], [158, 158], [238, 108]];
  greens.forEach(([x, y]) => circle(ctx, x, y, 5, '#6f9a4c'));
  ctx.strokeStyle = '#3e3227';
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(42, 34);
  ctx.lineTo(118, 118);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(70, 30);
  ctx.lineTo(140, 106);
  ctx.stroke();
}

function drawSalad(ctx, w, h) {
  ctx.fillStyle = '#d9d3c4';
  ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 6; i += 1) {
    ctx.fillStyle = 'rgba(120,110,90,.07)';
    ctx.fillRect(0, (i * 50 + 20) % h, w, 2);
  }
  ellipse(ctx, w / 2, h / 2 + 14, 132, 102, 'rgba(40,25,15,.24)');
  ellipse(ctx, w / 2, h / 2 + 4, 130, 100, '#8a5a3a');
  ellipse(ctx, w / 2, h / 2 + 4, 112, 84, '#5f3d2a');
  const greens = [
    [140, 108, 30, '#5e9c43'],
    [196, 96, 34, '#77b257'],
    [226, 132, 28, '#4c8038'],
    [166, 142, 26, '#69a34c'],
    [126, 138, 22, '#558d3d'],
    [212, 160, 24, '#6faa50'],
    [156, 104, 18, '#7fb85c']
  ];
  greens.forEach(([x, y, r, fill]) => circle(ctx, x, y, r, fill));
  [[244, 108, 11, '#d94a45'], [184, 170, 10, '#e05a4c'], [112, 126, 9, '#d94a45']].forEach(([x, y, r, fill]) => circle(ctx, x, y, r, fill));
  [[258, 148, 12, '#cfe3b5', '#7fad62'], [130, 172, 11, '#d4e7b9', '#7fad62']].forEach(([x, y, r, fill, rim]) => {
    circle(ctx, x, y, r, rim);
    circle(ctx, x, y, r - 4, fill);
  });
  ctx.strokeStyle = '#f0a63b';
  ctx.lineWidth = 3;
  for (let i = 0; i < 5; i += 1) {
    const x = 212 + i * 18;
    const y = 132 + Math.sin(i) * 8;
    ctx.beginPath();
    ctx.moveTo(x - 7, y);
    ctx.lineTo(x + 7, y);
    ctx.stroke();
  }
}

const SAMPLE_SPECS = [
  { label: '米饭番茄炒蛋', draw: drawRiceTomatoEgg },
  { label: '鸡胸肉西兰花', draw: drawChickenBroccoli },
  { label: '红烧牛肉面', draw: drawBeefNoodle },
  { label: '蔬果沙拉', draw: drawSalad }
];

export function buildSamples() {
  return SAMPLE_SPECS.map((spec, index) => {
    const canvas = document.createElement('canvas');
    canvas.width = 360;
    canvas.height = 270;
    spec.draw(canvas.getContext('2d'), 360, 270);
    return {
      id: index,
      label: spec.label,
      dataUrl: canvas.toDataURL('image/jpeg', 0.9)
    };
  });
}

import { reactive, computed } from 'vue';
import { analyzeImage } from './analytics/analyzer.js';

const HISTORY_KEY = 'kcal-history-v1';
const GOAL_KEY = 'kcal-goal';

function todayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function loadHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export const store = reactive({
  imageDataUrl: null,
  items: [],
  confidence: 0,
  meal: '午餐',
  analyzing: false,
  cameraStream: null,
  facing: 'environment',
  goal: Number(localStorage.getItem(GOAL_KEY)) || 2000,
  history: loadHistory(),
  analyzeStep: 0,
  stageHint: '',
  toastMessage: '',
  drawerOpen: false,
  pickerOpen: false,
  foodQuery: ''
});

export const currentKcal = computed(() => {
  return store.items.reduce((sum, item) => sum + (item.grams / 100) * item.kcal, 0);
});

export const currentMacros = computed(() => {
  const macros = { p: 0, c: 0, f: 0 };
  store.items.forEach((item) => {
    macros.p += (item.grams / 100) * item.p;
    macros.c += (item.grams / 100) * item.c;
    macros.f += (item.grams / 100) * item.f;
  });
  return macros;
});

export const todayKcal = computed(() => {
  const key = todayKey();
  return store.history.filter((entry) => entry.date === key).reduce((sum, entry) => sum + entry.kcal, 0);
});

let toastTimer = null;

export function toast(message) {
  store.toastMessage = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    store.toastMessage = '';
  }, 2400);
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function runAnalysis() {
  if (!store.imageDataUrl || store.analyzing) return;
  store.analyzing = true;
  store.analyzeStep = 0;
  const delays = [520, 720, 560, 420];
  for (let i = 0; i < delays.length; i += 1) {
    store.analyzeStep = i;
    await wait(delays[i]);
  }
  try {
    const result = await analyzeImage(store.imageDataUrl);
    store.items = result.items;
    store.confidence = result.confidence;
  } catch {
    toast('分析失败，请更换照片后重试');
  }
  store.analyzing = false;
  store.stageHint = '';
}

export function stopCameraStream() {
  if (store.cameraStream) {
    store.cameraStream.getTracks().forEach((track) => track.stop());
    store.cameraStream = null;
  }
}

export function setImage(dataUrl) {
  store.imageDataUrl = dataUrl;
  store.stageHint = '';
}

function makeImageForStorage(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const maxW = 640;
      const scale = Math.min(1, maxW / img.naturalWidth);
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL('image/jpeg', 0.72));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

function makeThumb(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 112;
      canvas.height = 84;
      const ctx = canvas.getContext('2d');
      const scale = Math.max(112 / img.naturalWidth, 84 / img.naturalHeight);
      const w = img.naturalWidth * scale;
      const h = img.naturalHeight * scale;
      ctx.drawImage(img, (112 - w) / 2, (84 - h) / 2, w, h);
      resolve(canvas.toDataURL('image/jpeg', 0.7));
    };
    img.onerror = () => resolve('');
    img.src = dataUrl;
  });
}

function persistHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(store.history));
}

export async function saveCurrentToHistory() {
  if (!store.items.length) {
    toast('请先识别一张餐食照片');
    return;
  }
  const image = await makeImageForStorage(store.imageDataUrl);
  const thumb = await makeThumb(image);
  const entry = {
    id: Date.now().toString(36),
    date: todayKey(),
    time: new Date().toTimeString().slice(0, 5),
    meal: store.meal,
    kcal: Math.round(currentKcal.value),
    names: store.items.map((item) => item.name).join('、'),
    count: store.items.length,
    image,
    thumb
  };
  store.history.unshift(entry);
  store.history = store.history.slice(0, 30);
  persistHistory();
  toast('已保存到历史记录');
}

export function removeHistory(id) {
  store.history = store.history.filter((entry) => entry.id !== id);
  persistHistory();
}

export function clearHistory() {
  store.history = [];
  persistHistory();
}

export function loadFromHistory(entry) {
  stopCameraStream();
  store.meal = entry.meal;
  store.drawerOpen = false;
  setImage(entry.image);
  runAnalysis();
}

export function setGoal() {
  const value = window.prompt('每日热量目标（千卡）', String(store.goal));
  const num = Number(value);
  if (value === null) return;
  if (!Number.isFinite(num) || num < 800 || num > 6000) {
    toast('请输入 800 - 6000 之间的目标');
    return;
  }
  store.goal = Math.round(num);
  localStorage.setItem(GOAL_KEY, String(store.goal));
  toast('每日目标已更新');
}

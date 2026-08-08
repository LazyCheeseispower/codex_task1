<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import Icon from './Icon.vue';
import { store, toast, runAnalysis, stopCameraStream, setImage } from '../store.js';
import { buildSamples } from '../analytics/samples.js';

const videoEl = ref(null);
const canvasEl = ref(null);
const fileInput = ref(null);
const samples = buildSamples();
const dragActive = ref(false);

const hasCamera = computed(() => !!store.cameraStream);
const hasImage = computed(() => !!store.imageDataUrl);
const showCanvas = computed(() => hasImage.value && !hasCamera.value);

watch(
  () => store.cameraStream,
  (stream) => {
    const video = videoEl.value;
    if (!video) return;
    video.srcObject = stream;
    if (stream) video.play().catch(() => {});
  }
);

watch(
  () => store.imageDataUrl,
  (dataUrl) => {
    const canvas = canvasEl.value;
    if (!dataUrl || !canvas) return;
    const img = new Image();
    img.onload = () => {
      canvas.width = 1280;
      canvas.height = 960;
      const ctx = canvas.getContext('2d');
      const scale = Math.max(1280 / img.naturalWidth, 960 / img.naturalHeight);
      const w = img.naturalWidth * scale;
      const h = img.naturalHeight * scale;
      ctx.drawImage(img, (1280 - w) / 2, (960 - h) / 2, w, h);
    };
    img.src = dataUrl;
  }
);

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    toast('当前浏览器不支持摄像头');
    return;
  }
  stopCameraStream();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: store.facing, width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false
    });
    store.cameraStream = stream;
  } catch {
    toast('无法访问摄像头，可改用上传图片');
  }
}

async function switchCamera() {
  store.facing = store.facing === 'environment' ? 'user' : 'environment';
  await startCamera();
}

function capturePhoto() {
  const video = videoEl.value;
  const canvas = canvasEl.value;
  if (!store.cameraStream || video.readyState < 2 || !canvas) return;
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 960;
  canvas.getContext('2d').drawImage(video, 0, 0);
  setImage(canvas.toDataURL('image/jpeg', 0.9));
  store.stageHint = '照片已拍摄，正在分析';
  runAnalysis();
}

function handleShutter() {
  if (hasCamera.value) capturePhoto();
  else startCamera();
}

function pickFile() {
  fileInput.value?.click();
}

function onFileChange(event) {
  const file = event.target.files?.[0];
  if (file) handleFile(file);
  event.target.value = '';
}

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    toast('请选择图片文件');
    return;
  }
  stopCameraStream();
  const reader = new FileReader();
  reader.onload = () => {
    setImage(reader.result);
    runAnalysis();
  };
  reader.readAsDataURL(file);
}

function onDrop(event) {
  dragActive.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file) handleFile(file);
}

function useSample(sample) {
  stopCameraStream();
  setImage(sample.dataUrl);
  runAnalysis();
}

onBeforeUnmount(stopCameraStream);
</script>

<template>
  <section class="panel capture-panel">
    <div class="panel-head">
      <div>
        <h2>拍摄识别</h2>
        <p>对准餐盘，保持光线充足</p>
      </div>
      <span class="mode-tag"><Icon name="camera" :size="15" />拍照模式</span>
    </div>

    <div
      class="stage"
      :class="{ dragging: dragActive }"
      role="region"
      aria-label="取景框"
      @dragover.prevent="dragActive = true"
      @dragleave="dragActive = false"
      @drop.prevent="onDrop"
    >
      <video ref="videoEl" playsinline muted autoplay :hidden="!hasCamera"></video>
      <canvas ref="canvasEl" class="preview-canvas" :hidden="!showCanvas"></canvas>
      <button v-if="!hasCamera && !showCanvas" class="stage-empty" @click="startCamera">
        <span class="stage-empty-icon"><Icon name="scan" :size="27" /></span>
        <p>将食物放入取景框</p>
        <small>点击开启相机，或拖入图片</small>
      </button>
      <div class="guide-frame" aria-hidden="true">
        <span class="g g-tl"></span>
        <span class="g g-tr"></span>
        <span class="g g-bl"></span>
        <span class="g g-br"></span>
      </div>
      <div v-if="store.stageHint" class="stage-hint">{{ store.stageHint }}</div>
    </div>

    <div class="capture-toolbar">
      <button class="btn" @click="pickFile"><Icon name="upload" />上传图片</button>
      <button class="shutter" @click="handleShutter" :title="hasCamera ? '拍摄' : '开启相机'" aria-label="拍摄或开启相机">
        <span class="shutter-ring"></span>
      </button>
      <button class="icon-btn" :disabled="!hasCamera" @click="switchCamera" title="切换镜头" aria-label="切换镜头">
        <Icon name="switch" />
      </button>
    </div>
    <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />

    <div class="sample-strip">
      <span class="strip-title"><Icon name="sparkles" :size="14" />示例餐盘</span>
      <div class="sample-list">
        <button v-for="sample in samples" :key="sample.id" class="sample-thumb" @click="useSample(sample)">
          <img :src="sample.dataUrl" :alt="sample.label" />
          <span>{{ sample.label }}</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import CapturePanel from './components/CapturePanel.vue';
import ResultPanel from './components/ResultPanel.vue';
import HistoryDrawer from './components/HistoryDrawer.vue';
import FoodPickerModal from './components/FoodPickerModal.vue';
import Icon from './components/Icon.vue';
import { store, todayKcal, setGoal } from './store.js';
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <span class="brand-mark"><Icon name="flame" :size="21" /></span>
        <div class="brand-text">
          <h1>热量相机</h1>
          <p>拍照识别食物热量</p>
        </div>
      </div>
      <div class="topbar-actions">
        <button class="goal-chip" @click="setGoal" title="调整每日热量目标">
          <Icon name="target" :size="16" />
          <span>今日 <b>{{ Math.round(todayKcal) }}</b> / <span>{{ store.goal }}</span> 千卡</span>
        </button>
        <button class="icon-btn" @click="store.drawerOpen = true" title="历史记录" aria-label="历史记录">
          <Icon name="history" />
        </button>
      </div>
    </div>
  </header>

  <main class="layout">
    <CapturePanel />
    <ResultPanel />
  </main>

  <HistoryDrawer />
  <FoodPickerModal />
  <div class="toast" :class="{ show: store.toastMessage }" role="status">{{ store.toastMessage }}</div>
</template>

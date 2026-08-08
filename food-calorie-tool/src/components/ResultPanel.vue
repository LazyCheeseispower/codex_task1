<script setup>
import { computed } from 'vue';
import Icon from './Icon.vue';
import { store, currentKcal, currentMacros, todayKcal, runAnalysis, saveCurrentToHistory } from '../store.js';

const kcal = currentKcal;
const macros = currentMacros;
const today = todayKcal;
const analyzeSteps = ['读取图像', '识别食材', '估算份量', '计算热量'];

const confLabel = computed(() => {
  if (store.confidence >= 0.82) return '高置信度';
  if (store.confidence >= 0.7) return '中等置信度';
  return '低置信度';
});

const confClass = computed(() => {
  if (store.confidence >= 0.82) return '';
  return store.confidence >= 0.7 ? 'mid' : 'low';
});

const todayPercent = computed(() => Math.min(100, (today.value / store.goal) * 100));

const equivalences = computed(() => {
  const value = Math.round(kcal.value);
  return [
    { label: '步行', icon: 'walk', value: Math.max(1, Math.round(value / 4.5)) },
    { label: '慢跑', icon: 'run', value: Math.max(1, Math.round(value / 9.5)) },
    { label: '骑行', icon: 'bike', value: Math.max(1, Math.round(value / 7.5)) }
  ];
});

const macroBars = computed(() => {
  const kcalValue = Math.max(1, kcal.value);
  return {
    p: Math.min(100, ((macros.value.p * 4) / kcalValue) * 100),
    c: Math.min(100, ((macros.value.c * 4) / kcalValue) * 100),
    f: Math.min(100, ((macros.value.f * 9) / kcalValue) * 100)
  };
});

function updateGrams(item, event) {
  item.grams = Number(event.target.value);
}

function removeItem(index) {
  store.items.splice(index, 1);
}

function openPicker() {
  store.foodQuery = '';
  store.pickerOpen = true;
}
</script>

<template>
  <section class="panel result-panel">
    <div class="panel-head">
      <div>
        <h2>识别结果</h2>
        <p>{{ store.items.length ? `${store.meal} · 估算仅供参考` : '等待一张食物照片' }}</p>
      </div>
    </div>

    <div class="result-body">
      <div v-if="!store.analyzing && !store.items.length" class="empty-state">
        <span class="empty-icon"><Icon name="utensils" :size="28" /></span>
        <h3>还没有识别结果</h3>
        <p>拍摄或上传餐食照片后，这里会显示热量与营养估算。</p>
      </div>

      <div v-else-if="store.analyzing" class="analyzing-state">
        <div class="scan-anim"><span></span><span></span><span></span></div>
        <p>正在识别食材…</p>
        <ol class="analyze-steps">
          <li
            v-for="(step, index) in analyzeSteps"
            :key="step"
            :class="{ done: index < store.analyzeStep, active: index === store.analyzeStep }"
          >
            {{ step }}
          </li>
        </ol>
      </div>

      <div v-else class="result-state">
        <div class="daily-progress">
          <div class="dp-head">
            <span><Icon name="zap" :size="14" />今日摄入</span>
            <b><span>{{ Math.round(today) }}</span> / <span>{{ store.goal }}</span> 千卡</b>
          </div>
          <div class="dp-track"><i :style="{ width: todayPercent + '%' }"></i></div>
        </div>

        <div class="kcal-hero">
          <div class="kcal-number">
            <span class="kcal-value">{{ Math.round(kcal) }}</span>
            <span class="kcal-unit">千卡</span>
          </div>
          <div class="hero-side">
            <span class="conf-chip" :class="confClass"><i></i><span>{{ confLabel }}</span></span>
            <span class="meal-chip"><Icon name="clock" :size="13" />{{ store.meal }}估算</span>
          </div>
        </div>

        <div class="macro-card">
          <div class="macro-row">
            <span>蛋白质</span>
            <div class="macro-track"><i class="protein" :style="{ width: macroBars.p + '%' }"></i></div>
            <b>{{ Math.round(macros.p) }}g</b>
          </div>
          <div class="macro-row">
            <span>碳水</span>
            <div class="macro-track"><i class="carbs" :style="{ width: macroBars.c + '%' }"></i></div>
            <b>{{ Math.round(macros.c) }}g</b>
          </div>
          <div class="macro-row">
            <span>脂肪</span>
            <div class="macro-track"><i class="fat" :style="{ width: macroBars.f + '%' }"></i></div>
            <b>{{ Math.round(macros.f) }}g</b>
          </div>
        </div>

        <div class="food-block">
          <div class="block-head">
            <h3>识别食材</h3>
            <button class="link-btn" @click="openPicker"><Icon name="plus" :size="14" />添加</button>
          </div>
          <ul class="food-list">
            <li v-for="(item, index) in store.items" :key="index" class="food-item">
              <div class="food-item-head">
                <div>
                  <span class="food-dot" :style="{ '--dot': item.color }"></span>
                  <b>{{ item.name }}</b>
                </div>
                <span class="food-kcal">{{ Math.round((item.grams / 100) * item.kcal) }} 千卡</span>
              </div>
              <div class="food-slider">
                <input
                  type="range"
                  min="30"
                  max="500"
                  step="5"
                  :value="item.grams"
                  @input="updateGrams(item, $event)"
                  :aria-label="item.name + '份量'"
                />
                <span>{{ item.grams }}g</span>
              </div>
            </li>
          </ul>
        </div>

        <div class="equiv-block">
          <div class="block-head"><h3>运动消耗</h3></div>
          <div class="equiv-grid">
            <div v-for="item in equivalences" :key="item.label" class="equiv-tile">
              <Icon :name="item.icon" :size="20" />
              <b>{{ item.value }} 分钟</b>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>

        <div class="action-bar">
          <label class="meal-select">
            <span>餐次</span>
            <select v-model="store.meal">
              <option>早餐</option>
              <option>午餐</option>
              <option>晚餐</option>
              <option>加餐</option>
            </select>
          </label>
          <button class="btn" @click="runAnalysis"><Icon name="refresh" />重新分析</button>
          <button class="btn primary" @click="saveCurrentToHistory"><Icon name="save" />保存记录</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import Icon from './Icon.vue';
import { store, removeHistory, clearHistory, loadFromHistory } from '../store.js';

const countLabel = computed(() => `${store.history.length} 条记录`);

function close() {
  store.drawerOpen = false;
}

function openEntry(entry) {
  loadFromHistory(entry);
}
</script>

<template>
  <div v-if="store.drawerOpen" class="drawer-backdrop" @click="close"></div>
  <aside class="drawer" :class="{ open: store.drawerOpen }" aria-hidden="!store.drawerOpen">
    <div class="drawer-head">
      <h3>历史记录</h3>
      <button class="icon-btn" @click="close" title="关闭" aria-label="关闭"><Icon name="x" /></button>
    </div>
    <div class="drawer-sub">
      <span>{{ countLabel }}</span>
      <button class="link-btn danger" @click="clearHistory"><Icon name="trash" :size="14" />清空</button>
    </div>
    <ul class="history-list">
      <li v-for="entry in store.history" :key="entry.id" class="history-item" @click="openEntry(entry)">
        <img :src="entry.thumb" :alt="entry.names" />
        <div class="history-item-main">
          <b>{{ entry.meal }} · {{ entry.names }}</b>
          <span>{{ entry.date }} {{ entry.time }} · {{ entry.count }} 项</span>
        </div>
        <div class="history-item-kcal">
          <b>{{ entry.kcal }}</b>
          <small>千卡</small>
          <button class="icon-btn icon-btn-sm" @click.stop="removeHistory(entry.id)" title="删除" aria-label="删除">
            <Icon name="trash" :size="14" />
          </button>
        </div>
      </li>
      <li v-if="!store.history.length" class="history-empty">还没有保存的记录</li>
    </ul>
  </aside>
</template>

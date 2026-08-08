<script setup>
import { computed } from 'vue';
import Icon from './Icon.vue';
import { store } from '../store.js';
import { FOOD_DB } from '../data/foodDb.js';

const filtered = computed(() => {
  const query = store.foodQuery.trim().toLowerCase();
  if (!query) return FOOD_DB;
  return FOOD_DB.filter((food) => food.name.toLowerCase().includes(query));
});

function addFood(food) {
  store.items.push({ ...food, grams: food.grams });
  store.pickerOpen = false;
}

function close() {
  store.pickerOpen = false;
}
</script>

<template>
  <div v-if="store.pickerOpen" class="modal-backdrop" @click.self="close">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="pickerTitle">
      <div class="modal-head">
        <h3 id="pickerTitle">添加食物</h3>
        <button class="icon-btn" @click="close" title="关闭" aria-label="关闭"><Icon name="x" /></button>
      </div>
      <input v-model="store.foodQuery" type="search" class="food-search" placeholder="搜索食物名称" />
      <div class="food-picker-list">
        <button v-for="food in filtered" :key="food.id" class="picker-item" @click="addFood(food)">
          <span class="food-dot" :style="{ '--dot': food.color }"></span>
          <span class="picker-main">
            <b>{{ food.name }}</b>
            <small>100g · {{ food.kcal }} 千卡</small>
          </span>
          <span class="picker-macro">P {{ food.p }} / C {{ food.c }} / F {{ food.f }}</span>
          <span class="picker-plus">+</span>
        </button>
        <p v-if="!filtered.length" class="picker-empty">没有匹配的食物</p>
      </div>
    </div>
  </div>
</template>

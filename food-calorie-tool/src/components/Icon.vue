<script setup>
import { ICONS } from '../data/icons.js';

defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 18 }
});
</script>

<template>
  <svg
    class="icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="ICONS[name] || ''"
  ></svg>
</template>

<script setup>
defineProps({ name: { type: String, required: true }, size: { type: Number, default: 18 } })
const shapes = {
  book: ['M3 4.5c3-1 6-1 9 1v15c-3-2-6-2-9-1zM21 4.5c-3-1-6-1-9 1v15c3-2 6-2 9-1z'],
  file: ['M14 3H5v18h14V8zM14 3v5h5M8 12h8M8 16h6'],
  chat: ['M4 4h16v12H9l-5 4zM8 8h8M8 12h5'],
  plus: ['M12 5v14M5 12h14'],
  user: ['M9 8a3 3 0 1 0 6 0a3 3 0 1 0-6 0M5 20v-2c0-6 14-6 14 0v2'],
  chevron: ['m9 5 7 7-7 7'],
  up: ['M12 19V5m-6 6 6-6 6 6'],
  copy: ['M8 8h12v12H8zM16 4H4v12'],
  trace: ['M8 5h12M8 12h12M8 19h12M3 5h.1M3 12h.1M3 19h.1'],
  history: ['M4 8a9 9 0 1 1-1 7M4 3v5h5M12 7v6l4 2'],
  menu: ['M4 6h16M4 12h16M4 18h16'],
  close: ['m6 6 12 12M6 18 18 6'],
  trash: ['M4 6h16M9 3h6M6 6l1 15h10l1-15M10 10v7M14 10v7'],
  download: ['M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5'],
  link: ['M10 13a4 4 0 0 0 6 0l4-4a4 4 0 0 0-6-6l-2 2M14 11a4 4 0 0 0-6 0l-4 4a4 4 0 0 0 6 6l2-2'],
}
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path v-for="(d, i) in shapes[name] || shapes.file" :key="i" :d="d" />
  </svg>
</template>

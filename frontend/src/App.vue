<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()

onMounted(async () => {
  // 应用主题（默认暗色）
  applyTheme(settings.theme)
  await settings.load()
  applyTheme(settings.theme)
})

function applyTheme(theme: 'dark' | 'light') {
  const el = document.documentElement
  el.classList.toggle('dark', theme === 'dark')
  el.classList.toggle('light', theme === 'light')
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { width: 100%; height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', Roboto, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: background-color .3s ease, color .3s ease;
}
</style>

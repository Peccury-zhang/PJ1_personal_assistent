<template>
  <div class="search-panel">
    <div class="search-head">
      <el-icon><Search /></el-icon>
      <span>联网搜索 · {{ results.length }} 条结果</span>
    </div>
    <a
      v-for="(r, i) in results"
      :key="`${r.url}-${i}`"
      class="search-item"
      :href="r.url"
      target="_blank"
      rel="noopener noreferrer"
    >
      <span class="search-idx">{{ i + 1 }}</span>
      <span class="search-body">
        <span class="search-title">{{ r.title }}</span>
        <span v-if="r.snippet" class="search-snippet">{{ r.snippet }}</span>
        <span class="search-src pa-muted">{{ r.source }}</span>
      </span>
    </a>
  </div>
</template>

<script setup lang="ts">
import type { SearchResult } from '@/types'

defineProps<{ results: SearchResult[] }>()
</script>

<style scoped>
.search-panel {
  display: flex; flex-direction: column; gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
}
.search-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--color-text-secondary);
  margin-bottom: 2px;
}
.search-head .el-icon { color: var(--color-info); }
.search-item {
  display: flex; gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: background var(--transition-fast);
}
.search-item:hover { background: var(--color-surface-hover); }
.search-idx {
  flex-shrink: 0; width: 18px; height: 18px; margin-top: 1px;
  border-radius: 50%;
  background: rgba(59, 130, 246, .18); color: var(--color-info);
  font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.search-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.search-title { font-size: 13px; font-weight: 600; color: var(--color-text-primary); }
.search-item:hover .search-title { color: var(--color-primary-light); }
.search-snippet {
  font-size: 12px; line-height: 1.6; color: var(--color-text-secondary);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.search-src { font-size: 11px; }
</style>

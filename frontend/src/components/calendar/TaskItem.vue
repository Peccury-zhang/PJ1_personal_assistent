<template>
  <div class="task-item" :class="{ done: task.done, compact }">
    <el-checkbox
      :model-value="task.done"
      class="task-check"
      @change="(v: any) => emit('toggle', !!v)"
    />
    <div class="task-body" @click="emit('edit')">
      <div class="task-title-row">
        <span class="prio-dot" :style="{ background: prio.color }" />
        <span class="task-title">{{ task.title }}</span>
      </div>
      <div v-if="task.note && !compact" class="task-note pa-muted">{{ task.note }}</div>
    </div>
    <div class="task-ops">
      <el-tag size="small" :color="prio.color" effect="dark" class="prio-tag" disable-transitions>
        {{ prio.label }}
      </el-tag>
      <div class="row-actions">
        <el-button size="small" type="warning" circle title="编辑" @click.stop="emit('edit')">
          <el-icon><Edit /></el-icon>
        </el-button>
        <el-button size="small" type="danger" circle title="删除" @click.stop="emit('remove')">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Task } from '@/types'
import { PRIORITY_META } from '@/utils/date'

const props = withDefaults(defineProps<{ task: Task; compact?: boolean }>(), { compact: false })
const emit = defineEmits<{
  (e: 'toggle', v: boolean): void
  (e: 'edit'): void
  (e: 'remove'): void
}>()

const prio = computed(() => PRIORITY_META[props.task.priority] || PRIORITY_META.normal)
</script>

<style scoped>
.task-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);
}
.task-item:hover { border-color: var(--color-border-hover); }
.task-item.compact { padding: 7px 9px; gap: 7px; }
.task-check { height: auto; }
.task-body { flex: 1; min-width: 0; cursor: pointer; }
.task-title-row { display: flex; align-items: center; gap: 7px; }
.prio-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.task-title {
  font-size: 14px; color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.task-item.done .task-title { text-decoration: line-through; color: var(--color-text-muted); }
.task-item.done .prio-dot { opacity: .4; }
.task-note {
  font-size: 12px; margin-top: 4px; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.task-ops { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.prio-tag { border: none; font-size: 11px; height: 20px; line-height: 20px; padding: 0 7px; }
.compact .prio-tag { display: none; }
</style>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑任务' : '新增任务'"
    width="480px"
    :close-on-click-modal="false"
    append-to-body
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <div v-if="dateLabel" class="date-label pa-muted">{{ dateLabel }}</div>
    <el-form :model="form" label-width="64px" @submit.prevent>
      <el-form-item label="标题" required>
        <el-input
          ref="titleRef"
          v-model="form.title"
          placeholder="要做什么？"
          maxlength="200"
          show-word-limit
          @keyup.enter="submit"
        />
      </el-form-item>
      <el-form-item label="优先级">
        <el-radio-group v-model="form.priority">
          <el-radio-button value="high">高</el-radio-button>
          <el-radio-button value="normal">中</el-radio-button>
          <el-radio-button value="low">低</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" :rows="3" maxlength="2000" placeholder="可选" />
      </el-form-item>
      <el-form-item label="已完成">
        <el-switch v-model="form.done" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="submit">
        <el-icon><Check /></el-icon>&nbsp;确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { Task, Priority } from '@/types'

const props = withDefaults(defineProps<{
  modelValue: boolean
  task?: Task | null
  dateLabel?: string
  initialDone?: boolean
}>(), { initialDone: false })
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'save', payload: Partial<Task>): void
}>()

const titleRef = ref()
const isEdit = computed(() => !!props.task?.id)

const form = reactive({
  title: '',
  priority: 'normal' as Priority,
  note: '',
  done: false
})

function onOpen() {
  const t = props.task
  form.title = t?.title || ''
  form.priority = t?.priority || 'normal'
  form.note = t?.note || ''
  // 编辑沿用原状态；新增时由 initialDone 预置（从「已完成」卡新增即为已完成）
  form.done = t ? !!t.done : !!props.initialDone
  nextTick(() => titleRef.value?.focus?.())
}

function submit() {
  if (!form.title.trim()) { ElMessage.warning('请填写任务标题'); return }
  emit('save', {
    ...(props.task?.id ? { id: props.task.id, created_at: props.task.created_at } : {}),
    title: form.title.trim(),
    priority: form.priority,
    note: form.note,
    done: form.done
  })
  emit('update:modelValue', false)
}
</script>

<style scoped>
.date-label { font-size: 13px; margin-bottom: 12px; }
</style>

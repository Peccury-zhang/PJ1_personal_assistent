<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑日记' : '写日记'"
    width="480px"
    :close-on-click-modal="false"
    append-to-body
  >
    <el-input
      v-model="content"
      type="textarea"
      :rows="7"
      maxlength="5000"
      show-word-limit
      placeholder="记录今天的想法…"
    />
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { DiaryEntry } from '@/types'

const props = defineProps<{ modelValue: boolean; entry?: DiaryEntry | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'save', content: string): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})
const content = ref('')
const isEdit = computed(() => !!props.entry?.id)

watch(() => props.modelValue, (v) => {
  if (v) content.value = props.entry?.content || ''
})

function submit() {
  const c = content.value.trim()
  if (!c) {
    ElMessage.warning('日记内容不能为空')
    return
  }
  emit('save', c)
  visible.value = false
}
</script>

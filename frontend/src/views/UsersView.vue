<template>
  <div class="users-view">
    <div class="uv-head">
      <div>
        <div class="uv-title">账户管理</div>
        <div class="uv-sub pa-muted">按账户 ID / 用户名 / 密码 / 等级管理账户（仅管理员可见）</div>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>&nbsp;新增用户
      </el-button>
    </div>

    <div class="uv-table pa-card">
      <el-table v-loading="loading" :data="users" stripe style="width: 100%">
        <el-table-column prop="id" label="账户ID" width="110" />
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column label="用户等级" width="120">
          <template #default="{ row }">
            <el-tag :type="row.level === 'admin' ? 'warning' : 'info'" effect="light" size="small">
              {{ row.level === 'admin' ? '管理员' : '普通' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openEdit(row)">
              <el-icon><Edit /></el-icon>&nbsp;编辑
            </el-button>
            <el-button text size="small" type="danger" @click="onRemove(row)">
              <el-icon><Delete /></el-icon>&nbsp;删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增 / 编辑 对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="420px" :close-on-click-modal="false">
      <el-form :model="form" label-width="80px" @submit.prevent>
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" maxlength="30" placeholder="可随意修改" />
        </el-form-item>
        <el-form-item label="密码" :required="!isEdit">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            maxlength="64"
            :placeholder="isEdit ? '留空表示不修改密码' : '设置登录密码'"
          />
        </el-form-item>
        <el-form-item label="用户等级">
          <el-radio-group v-model="form.level">
            <el-radio-button value="admin">管理员</el-radio-button>
            <el-radio-button value="user">普通</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api'
import type { AuthUser, UserLevel } from '@/types'

const users = ref<AuthUser[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({ username: '', password: '', level: 'user' as UserLevel })

async function load() {
  loading.value = true
  try {
    const r = await api.listUsers()
    users.value = r.users
  } finally {
    loading.value = false
  }
}
onMounted(load)

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.username = ''
  form.password = ''
  form.level = 'user'
  dialogVisible.value = true
}
function openEdit(row: AuthUser) {
  isEdit.value = true
  editingId.value = row.id
  form.username = row.username
  form.password = ''
  form.level = row.level
  dialogVisible.value = true
}

async function onSave() {
  if (!form.username.trim()) { ElMessage.warning('请填写用户名'); return }
  if (!isEdit.value && !form.password) { ElMessage.warning('请设置密码'); return }
  saving.value = true
  try {
    if (isEdit.value && editingId.value != null) {
      await api.updateUser(editingId.value, {
        username: form.username.trim(),
        level: form.level,
        ...(form.password ? { password: form.password } : {})
      })
      ElMessage.success('已保存')
    } else {
      await api.createUser({ username: form.username.trim(), password: form.password, level: form.level })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await load()
  } catch { /* 拦截器已提示 */ } finally {
    saving.value = false
  }
}

async function onRemove(row: AuthUser) {
  try {
    await ElMessageBox.confirm(`删除用户「${row.username}」（ID ${row.id}）？`, '确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
  } catch { return }
  try {
    await api.deleteUser(row.id)
    ElMessage.success('已删除')
    await load()
  } catch { /* 拦截器已提示 */ }
}
</script>

<style scoped>
.users-view { display: flex; flex-direction: column; gap: 16px; height: 100%; }
.uv-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.uv-title { font-size: 18px; font-weight: 700; color: var(--color-text-primary); }
.uv-sub { font-size: 12.5px; margin-top: 4px; }
.uv-table { padding: 8px; }
</style>

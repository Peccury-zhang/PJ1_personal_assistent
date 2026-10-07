<template>
  <div class="butler-view">
    <div class="hero pa-card">
      <div class="hero-icon"><el-icon :size="34"><MagicStick /></el-icon></div>
      <div class="hero-text">
        <h2>智能助手</h2>
        <p class="pa-secondary">
          「个人全能助手」的通用 AI 能力入口。当前版本已上线 <b>日历任务</b>、<b>AI 周报</b>、<b>天气</b> 三大模块，
          智能助手面板正在规划中。
        </p>
      </div>
    </div>

    <div class="grid">
      <div v-for="f in features" :key="f.title" class="feat pa-card">
        <div class="feat-head">
          <el-icon :size="20" :color="f.color"><component :is="f.icon" /></el-icon>
          <span class="feat-title">{{ f.title }}</span>
          <el-tag size="small" :type="f.done ? 'success' : 'info'" effect="plain">
            {{ f.done ? '已上线' : '规划中' }}
          </el-tag>
        </div>
        <p class="feat-desc pa-muted">{{ f.desc }}</p>
      </div>
    </div>

    <div class="tip pa-card">
      <el-icon color="#f59e0b"><InfoFilled /></el-icon>
      <span class="pa-secondary">
        提示：AI 相关能力（周报生成等）需先在
        <el-link type="primary" @click="emit('open-settings')">设置 → AI 模型</el-link>
        中配置 API Key，默认模型 qwen3.8-flash，可在设置里加载并切换你阿里云账号可用的全部模型。
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{ (e: 'open-settings'): void }>()

const features = [
  { title: '日历与任务', icon: 'Calendar', color: '#3b82f6', done: true, desc: '月/周视图管理每日任务，农历、节气、节日、天气一屏尽览。' },
  { title: 'AI 周报', icon: 'Document', color: '#10b981', done: true, desc: '一键汇总本周完成情况，流式生成 Markdown 周报并导出到本地。' },
  { title: '天气', icon: 'Sunny', color: '#f59e0b', done: true, desc: '当天实况 + 未来 7 天预报，含气压、紫外线、风力、空气质量，多城市对比。' },
  { title: '智能对话', icon: 'ChatDotRound', color: '#8b5cf6', done: false, desc: '基于已配置模型的通用问答与任务助手（规划中）。' },
  { title: '日程提醒', icon: 'Bell', color: '#ec4899', done: false, desc: '任务到期提醒与每日计划推送（规划中）。' },
  { title: '数据洞察', icon: 'DataLine', color: '#06b6d4', done: false, desc: '完成率趋势、习惯分析等可视化统计（规划中）。' }
]
</script>

<style scoped>
.butler-view { display: flex; flex-direction: column; gap: 16px; }

.hero { padding: 24px; display: flex; align-items: center; gap: 18px; }
.hero-icon {
  width: 60px; height: 60px; flex-shrink: 0; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(245,158,11,.2), rgba(139,92,246,.2));
  color: var(--color-primary);
}
.hero-text h2 { font-size: 20px; color: var(--color-text-primary); margin-bottom: 6px; }
.hero-text p { font-size: 13.5px; line-height: 1.6; max-width: 760px; }
.hero-text b { color: var(--color-primary); }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.feat { padding: 16px 18px; }
.feat-head { display: flex; align-items: center; gap: 9px; }
.feat-title { font-size: 15px; font-weight: 700; color: var(--color-text-primary); flex: 1; }
.feat-desc { font-size: 12.5px; line-height: 1.6; margin-top: 10px; }

.tip { padding: 14px 16px; display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.6; }
</style>

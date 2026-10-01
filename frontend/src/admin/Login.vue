<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-card__head">
        <img v-if="brandState.logo" :src="brandState.logo" alt="站点 Logo" class="mark mark--img" />
        <div v-else class="mark">{{ brandState.initial }}</div>
        <div>
          <h1>{{ brandState.name || '尚标易' }} · 运营后台</h1>
          <p>商标管理 · 批量导入 · 报价单运营</p>
        </div>
      </div>
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            size="large"
            show-password
            placeholder="请输入密码"
            :prefix-icon="Lock"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="admin.loading" class="login-submit" @click="submit">
          登录后台
        </el-button>
      </el-form>
      <p class="login-hint">
        初始账号 <code>admin</code> / <code>admin888</code>，请登录后立即在「运营账户」中修改密码。
      </p>
      <router-link to="/" class="login-back">← 返回前台首页</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { siteApi } from '@/api'
import { useAdminStore } from '@/stores/auth'
import { applyBranding, brandState } from '@/utils/branding'

const admin = useAdminStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: 'admin', password: '' })

onMounted(async () => {
  try {
    // 品牌跟随站点配置（响应式 brandState 驱动模板）
    applyBranding(await siteApi.config())
  } catch {
    /* 配置拉取失败时用默认品牌 */
  }
})

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  await admin.login(form.username, form.password)
  ElMessage.success(`欢迎回来，${admin.displayName}`)
  router.push((route.query.redirect as string) || '/admin/dashboard')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(1100px 520px at 12% -10%, #13233f 0%, transparent 60%),
    linear-gradient(160deg, #0f172a 0%, #1b2a45 52%, #0f172a 100%);
  padding: var(--space-6);
}
.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: var(--radius-xl);
  padding: var(--space-10);
  box-shadow: var(--shadow-lg);
}
.login-card__head {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}
.mark {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--radius-lg);
  background: var(--color-primary);
  color: #fff;
  font-family: Georgia, serif;
  font-size: 22px;
  display: grid;
  place-items: center;
}
.mark--img {
  object-fit: contain;
  background: #fff;
  border: 1px solid var(--color-border);
  padding: 4px;
}
.login-card__head h1 {
  margin: 0;
  font-size: var(--text-lg);
  letter-spacing: 0.5px;
}
.login-card__head p {
  margin: 4px 0 0;
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
.login-submit {
  width: 100%;
  margin-top: var(--space-2);
}
.login-hint {
  margin: var(--space-6) 0 0;
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
  line-height: 1.7;
}
.login-hint code {
  background: var(--color-muted);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}
.login-back {
  display: inline-block;
  margin-top: var(--space-4);
  font-size: var(--text-xs);
}
</style>
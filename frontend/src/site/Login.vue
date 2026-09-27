<template>
  <div class="auth-page">
    <div class="panel-card auth-card">
      <h1 class="auth-title">登录</h1>
      <p class="auth-sub">登录后可收藏商标、生成专属报价单</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="手机号">
          <el-input v-model="phone" maxlength="11" placeholder="请输入 11 位手机号" :prefix-icon="Iphone" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password placeholder="请输入密码" :prefix-icon="Lock" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" class="full" :loading="loading" @click="submit">登录</el-button>
      </el-form>

      <div class="auth-foot">
        <span class="text-muted">还没有账号？</span>
        <router-link :to="{ path: '/register', query: route.query }">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const phone = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!/^\d{11}$/.test(phone.value.trim())) return ElMessage.warning('请输入 11 位手机号')
  if (!password.value) return ElMessage.warning('请输入密码')
  loading.value = true
  try {
    await user.login(phone.value.trim(), password.value)
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch {
    /* 错误提示由 http 拦截器统一处理 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 62vh;
  display: grid;
  place-items: center;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: var(--space-8);
}
.auth-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-2xl);
}
.auth-sub {
  margin: 0 0 var(--space-6);
  color: var(--color-muted-fg);
  font-size: var(--text-sm);
}
.full {
  width: 100%;
  height: 46px;
}
.auth-foot {
  margin-top: var(--space-5);
  font-size: var(--text-sm);
  display: flex;
  gap: var(--space-2);
  justify-content: center;
}
</style>
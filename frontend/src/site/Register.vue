<template>
  <div class="auth-page">
    <div class="panel-card auth-card">
      <h1 class="auth-title">注册</h1>
      <p class="auth-sub">注册即可收藏商标、生成专属报价单</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="手机号">
          <el-input v-model="phone" maxlength="11" placeholder="请输入 11 位手机号" :prefix-icon="Iphone" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password placeholder="至少 6 位字符" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item label="昵称（选填）">
          <el-input v-model="nickname" maxlength="20" placeholder="不填将自动生成" />
        </el-form-item>
        <el-form-item label="图形验证码">
          <div class="captcha-row">
            <el-input v-model="captcha" maxlength="4" placeholder="输入右侧字符" @keyup.enter="submit" />
            <button type="button" class="captcha-img" aria-label="点击刷新验证码" @click="loadCaptcha">
              <img v-if="captchaUrl" :src="captchaUrl" alt="图形验证码，点击刷新" />
              <span v-else>加载中…</span>
            </button>
          </div>
        </el-form-item>
        <el-button type="primary" size="large" class="full" :loading="loading" @click="submit">注册</el-button>
      </el-form>

      <div class="auth-foot">
        <span class="text-muted">已有账号？</span>
        <router-link :to="{ path: '/login', query: route.query }">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Lock } from '@element-plus/icons-vue'
import { http } from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const phone = ref('')
const password = ref('')
const nickname = ref('')
const captcha = ref('')
const captchaKey = ref('')
const captchaUrl = ref('')
const loading = ref(false)

async function loadCaptcha() {
  try {
    const res = await http.get('/api/auth/captcha', { responseType: 'blob' })
    captchaKey.value = String(res.headers['x-captcha-key'] || '')
    if (captchaUrl.value) URL.revokeObjectURL(captchaUrl.value)
    captchaUrl.value = URL.createObjectURL(res.data as Blob)
  } catch {
    ElMessage.error('验证码加载失败，请点击刷新')
  }
}

async function submit() {
  if (!/^\d{11}$/.test(phone.value.trim())) return ElMessage.warning('请输入 11 位手机号')
  if (password.value.length < 6) return ElMessage.warning('密码至少 6 位')
  if (!captcha.value.trim()) return ElMessage.warning('请输入图形验证码')
  loading.value = true
  try {
    await user.register({
      phone: phone.value.trim(),
      password: password.value,
      nickname: nickname.value.trim() || null,
      captcha: captcha.value.trim(),
      captcha_key: captchaKey.value,
    })
    ElMessage.success('注册成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch {
    captcha.value = ''
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(loadCaptcha)
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
.captcha-row {
  display: flex;
  gap: var(--space-3);
  width: 100%;
}
.captcha-img {
  width: 120px;
  height: 40px;
  flex: none;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #f1f5f9;
  cursor: pointer;
  overflow: hidden;
  display: grid;
  place-items: center;
  color: var(--color-subtle-fg);
  font-size: var(--text-xs);
}
.captcha-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
/* 本页不在 .site-container 里，手机上需自行补页边距，否则卡片会贴到屏幕边缘 */
@media (max-width: 820px) {
  .auth-page {
    padding: var(--space-5) max(var(--space-4), env(safe-area-inset-left)) var(--space-6)
      max(var(--space-4), env(safe-area-inset-right));
  }
  .auth-card {
    padding: var(--space-6);
  }
  .full {
    min-height: 46px;
  }
  .captcha-img {
    height: 44px;
  }
}
</style>
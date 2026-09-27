<script lang="ts">
import { ref as vueRef } from 'vue'
import { siteApi, type SiteConfig } from '@/api'

/**
 * 站点配置全站共享缓存：SiteLayout 挂载时请求一次，
 * 其它页面（静态页 / 报价单等）直接复用，避免每页重复请求。
 * 注意：本文件同时有 <script> 与 <script setup> 两个块，
 * 二者会合并到同一作用域，因此这里用别名引入 ref，避免与 setup 块的 ref 重复声明。
 */
export const siteConfig = vueRef<SiteConfig | null>(null)
let inflight: Promise<SiteConfig> | null = null

export function ensureSiteConfig(force = false): Promise<SiteConfig> {
  if (!force && siteConfig.value) return Promise.resolve(siteConfig.value)
  if (!inflight) {
    inflight = siteApi
      .config()
      .then((c) => {
        siteConfig.value = c
        return c
      })
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}
</script>

<template>
  <div class="site-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <router-link to="/" class="site-logo" aria-label="返回首页">
          <img v-if="config?.logo_url" :src="config.logo_url" :alt="`${config?.site_name || '商标交易平台'} Logo`" class="site-logo__img" />
          <span v-else class="site-logo__mark">尚</span>
          <span class="site-logo__text">
            <strong>{{ config?.site_name || '尚标易 · 商标交易平台' }}</strong>
            <span>{{ config?.site_subtitle || '精选现成商标 · 即买即用' }}</span>
          </span>
        </router-link>

        <form class="header-search" role="search" @submit.prevent="onSearch">
          <el-input v-model="keyword" placeholder="搜索商标名 / 注册号" clearable aria-label="搜索商标">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </form>

        <nav class="site-nav" aria-label="主导航">
          <router-link to="/">首页</router-link>
          <router-link to="/trademarks">全部商标</router-link>
          <router-link to="/process">交易流程</router-link>
          <router-link to="/about">关于我们</router-link>
          <router-link to="/contact">联系我们</router-link>
        </nav>

        <div class="site-header__actions">
          <button class="cart-pill" type="button" @click="router.push('/cart')">
            <el-icon><ShoppingCart /></el-icon>
            报价单 <b>{{ user.cartCount }}</b>
          </button>

          <el-dropdown v-if="user.isLoggedIn" trigger="click" @command="onUserCommand">
            <button class="user-chip" type="button">
              <el-icon><User /></el-icon>
              <span class="user-chip__name">{{ user.profile?.nickname || user.profile?.phone }}</span>
              <el-icon><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="center">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <template v-else>
            <router-link class="header-login" :to="{ path: '/login', query: { redirect: route.fullPath } }">登录</router-link>
            <router-link class="header-register" to="/register">注册</router-link>
          </template>

          <el-icon class="nav-toggle" role="button" tabindex="0" aria-label="打开导航菜单" @click="drawer = true" @keyup.enter="drawer = true">
            <Menu />
          </el-icon>
        </div>
      </div>
    </header>

    <main class="site-main">
      <router-view />
    </main>

    <footer class="site-footer">
      <div class="site-footer__inner">
        <div>
          <h4>{{ config?.site_name || '尚标易 · 商标交易平台' }}</h4>
          <p>{{ config?.company_intro }}</p>
        </div>
        <div>
          <h4>快捷链接</h4>
          <ul>
            <li><router-link to="/trademarks">全部商标</router-link></li>
            <li><router-link to="/process">交易流程</router-link></li>
            <li><router-link to="/about">关于我们</router-link></li>
            <li><router-link to="/contact">联系我们</router-link></li>
          </ul>
        </div>
        <div>
          <h4>联系方式</h4>
          <ul>
            <li>电话：{{ config?.contact_phone || '—' }}</li>
            <li>地址：{{ config?.address || '—' }}</li>
            <li>工作时间：{{ config?.service_hours || '—' }}</li>
          </ul>
        </div>
        <div>
          <h4>客服微信</h4>
          <p class="footer-wechat">
            <span class="mono-id">{{ config?.service_wechat || '—' }}</span>
            <el-button
              v-if="config?.service_wechat"
              link
              type="primary"
              :icon="CopyDocument"
              @click="copyWechat"
            >
              复制微信号
            </el-button>
          </p>
          <p>{{ config?.service_text }}</p>
        </div>
      </div>
      <div class="site-footer__bottom">
        <span>{{ config?.copyright }}</span>
        <span>{{ config?.icp }}</span>
      </div>
    </footer>

    <el-drawer v-model="drawer" title="导航菜单" direction="rtl" size="72%">
      <nav class="drawer-nav">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path" @click="drawer = false">
          {{ item.label }}
        </router-link>
      </nav>
      <div class="drawer-foot">
        <template v-if="user.isLoggedIn">
          <el-button type="primary" class="block" @click="go('/user')">个人中心</el-button>
          <el-button class="block" @click="onUserCommand('logout')">退出登录</el-button>
        </template>
        <template v-else>
          <el-button type="primary" class="block" @click="go('/login')">登录</el-button>
          <el-button class="block" @click="go('/register')">注册</el-button>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, CopyDocument, Menu, Search, ShoppingCart, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const keyword = ref('')
const drawer = ref(false)

// 复用模块级缓存（见本文件脚本顶部的 siteConfig），把模板绑定指向它
const config = siteConfig

const navItems = [
  { path: '/', label: '首页' },
  { path: '/trademarks', label: '全部商标' },
  { path: '/process', label: '交易流程' },
  { path: '/about', label: '关于我们' },
  { path: '/contact', label: '联系我们' },
]

const currentRedirect = computed(() => route.fullPath)

function onSearch() {
  const q = keyword.value.trim()
  router.push(q ? { path: '/trademarks', query: { q } } : { path: '/trademarks' })
}

function onUserCommand(cmd: string) {
  drawer.value = false
  if (cmd === 'center') return router.push('/user')
  if (cmd === 'logout') {
    user.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  }
}

function go(path: string) {
  drawer.value = false
  if (path === '/login') return router.push({ path, query: { redirect: currentRedirect.value } })
  router.push(path)
}

function copyWechat() {
  const wx = config.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

onMounted(async () => {
  await ensureSiteConfig()
  if (user.isLoggedIn) await user.loadFavorites()
})
</script>

<style scoped>
.site-main {
  flex: 1;
}
.cart-pill,
.user-chip {
  font-family: inherit;
}
.site-logo__img {
  height: 36px;
  width: auto;
  display: block;
}
.header-search {
  width: 250px;
  flex: none;
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: #fff;
  color: var(--color-fg);
  font-size: var(--text-base);
  cursor: pointer;
  max-width: 190px;
}
.user-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.user-chip__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-login {
  font-size: var(--text-md);
  color: var(--color-muted-fg);
}
.header-register {
  padding: 7px 16px;
  border-radius: 6px;
  background: var(--color-accent);
  color: #fff;
  font-size: var(--text-base);
}
.header-register:hover {
  background: var(--color-accent-600);
}
.nav-toggle {
  display: none;
  font-size: 22px;
  cursor: pointer;
  color: var(--color-muted-fg);
}
.footer-wechat {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.drawer-nav {
  display: flex;
  flex-direction: column;
}
.drawer-nav a {
  padding: var(--space-4) var(--space-2);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-fg);
  font-size: var(--text-md);
}
.drawer-nav a.router-link-active {
  color: var(--color-accent);
}
.drawer-foot {
  margin-top: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.block {
  width: 100%;
  margin-left: 0 !important;
  height: 44px;
}
@media (max-width: 820px) {
  .header-search {
    display: none;
  }
  .nav-toggle {
    display: block;
  }
  .user-chip__name {
    display: none;
  }
}
</style>
<template>
  <el-container class="admin-shell">
    <el-aside :width="collapsed ? '64px' : '216px'" class="admin-aside">
      <div class="brand" :class="{ 'brand--mini': collapsed }">
        <img v-if="brandState.logo" :src="brandState.logo" alt="站点 Logo" class="brand__logo" />
        <div v-else class="brand__mark">{{ brandState.initial }}</div>
        <div v-if="!collapsed" class="brand__text">
          <strong :title="brandState.name">{{ brandState.name || '运营后台' }}</strong>
          <span>运营后台</span>
        </div>
      </div>
      <el-menu
        :default-active="activePath"
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        router
        class="admin-menu"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataLine /></el-icon><template #title>数据看板</template>
        </el-menu-item>
        <el-sub-menu index="tm">
          <template #title><el-icon><Goods /></el-icon><span>商标管理</span></template>
          <el-menu-item index="/admin/trademarks">商标列表</el-menu-item>
          <el-menu-item index="/admin/trademarks/new">新增商标</el-menu-item>
          <el-menu-item index="/admin/trademarks/import">批量导入</el-menu-item>
          <el-menu-item index="/admin/trademarks/batches">导入批次</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/admin/submissions">
          <el-icon><Stamp /></el-icon>
          <template #title>
            寄售审核
            <el-badge v-if="pendingSubmissions" :value="pendingSubmissions" class="menu-badge" />
          </template>
        </el-menu-item>
        <el-menu-item index="/admin/customers">
          <el-icon><User /></el-icon><template #title>客户管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/quotes">
          <el-icon><Tickets /></el-icon><template #title>报价单管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/expiring">
          <el-icon><AlarmClock /></el-icon><template #title>到期提醒</template>
        </el-menu-item>
        <el-menu-item v-if="admin.isSuper" index="/admin/settings">
          <el-icon><Setting /></el-icon><template #title>网站配置</template>
        </el-menu-item>
        <el-menu-item v-if="admin.isSuper" index="/admin/admins">
          <el-icon><Avatar /></el-icon><template #title>运营账户</template>
        </el-menu-item>
        <el-menu-item v-if="admin.isSuper" index="/admin/content">
          <el-icon><FolderOpened /></el-icon><template #title>内容迁移</template>
        </el-menu-item>
        <el-menu-item v-if="admin.isSuper" index="/admin/logs">
          <el-icon><Document /></el-icon><template #title>操作日志</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="admin-header__left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" /><Expand v-else />
          </el-icon>
          <span class="admin-header__title">{{ pageTitle }}</span>
        </div>
        <div class="admin-header__right">
          <el-tag v-if="admin.isSuper" type="warning" effect="plain" size="small">超级管理员</el-tag>
          <el-tag v-else type="info" effect="plain" size="small">普通运营</el-tag>
          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <el-icon><UserFilled /></el-icon>{{ admin.displayName }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="site">访问前台</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminSubmissionApi, siteApi } from '@/api'
import { useAdminStore } from '@/stores/auth'
import { applyBranding, brandState } from '@/utils/branding'

const admin = useAdminStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
/** 待审核寄售数量：菜单上直接显示未处理量 */
const pendingSubmissions = ref(0)

onMounted(async () => {
  try {
    // 后台侧边栏名称与 Logo、浏览器标签图标与标题，全部跟随站点配置（brandState 是响应式的，
    // 所以在「网站配置」里保存后会当场更新，不需要刷新页面）
    applyBranding(await siteApi.config())
  } catch {
    /* 配置拉取失败不影响后台使用 */
  }
  try {
    pendingSubmissions.value = (await adminSubmissionApi.summary()).pending
  } catch {
    /* 忽略 */
  }
})

const activePath = computed(() => {
  const p = route.path
  if (p.startsWith('/admin/trademarks/') && p !== '/admin/trademarks') return p
  return p
})

const TITLES: Record<string, string> = {
  '/admin/dashboard': '数据看板',
  '/admin/trademarks': '商标列表',
  '/admin/trademarks/import': '批量导入',
  '/admin/trademarks/batches': '导入批次',
  '/admin/trademarks/new': '新增商标',
  '/admin/submissions': '寄售审核',
  '/admin/content': '内容迁移',
  '/admin/customers': '客户管理',
  '/admin/quotes': '报价单管理',
  '/admin/expiring': '商标到期提醒',
  '/admin/settings': '网站配置',
  '/admin/admins': '运营账户',
  '/admin/logs': '操作日志',
}
const pageTitle = computed(() => {
  if (route.name === 'admin-tm-edit') return '编辑商标'
  return TITLES[route.path] || '运营后台'
})

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    admin.logout()
    router.push('/admin/login')
  } else if (cmd === 'site') {
    window.open('/', '_blank')
  }
}
</script>

<style scoped>
.admin-shell {
  height: 100vh;
}
.admin-aside {
  background: #0f172a;
  transition: width var(--transition);
  overflow-x: hidden;
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 60px;
  padding: 0 var(--space-5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.brand--mini {
  padding: 0 14px;
}
.brand__logo {
  width: 32px;
  height: 32px;
  flex: none;
  object-fit: contain;
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.08);
}
.brand__mark {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: var(--radius);
  background: var(--color-accent);
  color: #fff;
  font-family: Georgia, serif;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  white-space: nowrap;
}
.brand__text strong {
  color: #fff;
  font-size: var(--text-md);
  letter-spacing: 0.5px;
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.brand__text span {
  color: #64748b;
  font-size: 11px;
}
.admin-menu {
  border-right: none;
  --el-menu-sub-item-height: 40px;
}
.menu-badge {
  margin-left: 6px;
  vertical-align: middle;
}
.menu-badge :deep(.el-badge__content) {
  border: none;
  transform: scale(0.85);
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  padding: 0 var(--space-6);
}
.admin-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.collapse-btn {
  font-size: 18px;
  color: var(--color-muted-fg);
  cursor: pointer;
}
.admin-header__title {
  font-size: var(--text-md);
  font-weight: 600;
}
.admin-header__right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--color-muted-fg);
  font-size: var(--text-base);
}
.admin-main {
  background: var(--color-bg);
  padding: var(--space-6);
  overflow-y: auto;
}
@media (max-width: 900px) {
  .admin-main {
    padding: var(--space-4);
  }
}
</style>
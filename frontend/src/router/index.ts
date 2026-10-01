import { createRouter, createWebHistory } from 'vue-router'
import { setAdminPageTitle, setPageTitle } from '@/utils/branding'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    // ---------------- 前台 ----------------
    {
      path: '/',
      component: () => import('@/site/SiteLayout.vue'),
      children: [
        { path: '', name: 'home', component: () => import('@/site/Home.vue') },
        { path: 'trademarks', name: 'site-list', component: () => import('@/site/TrademarkList.vue'), meta: { title: '全部商标' } },
        { path: 'trademark/:id', name: 'site-detail', component: () => import('@/site/TrademarkDetail.vue') },
        { path: 'sell', name: 'site-sell', component: () => import('@/site/SellSubmission.vue'), meta: { title: '我要卖标' } },
        { path: 'cart', name: 'cart', component: () => import('@/site/QuoteCart.vue'), meta: { title: '报价单' } },
        { path: 'login', name: 'site-login', component: () => import('@/site/Login.vue'), meta: { title: '登录' } },
        { path: 'register', name: 'site-register', component: () => import('@/site/Register.vue'), meta: { title: '注册' } },
        { path: 'user', name: 'user-center', component: () => import('@/site/UserCenter.vue'), meta: { title: '个人中心' } },
        { path: 'about', name: 'about', component: () => import('@/site/StaticPage.vue'), props: { page: 'about' }, meta: { title: '关于我们' } },
        { path: 'process', name: 'process', component: () => import('@/site/StaticPage.vue'), props: { page: 'process' }, meta: { title: '交易流程' } },
        { path: 'contact', name: 'contact', component: () => import('@/site/StaticPage.vue'), props: { page: 'contact' }, meta: { title: '联系我们' } },
      ],
    },
    { path: '/quote/:token', name: 'quote-share', component: () => import('@/site/QuoteShare.vue'), meta: { title: '商标报价单' } },

    // ---------------- 后台 ----------------
    { path: '/admin/login', name: 'admin-login', component: () => import('@/admin/Login.vue'), meta: { title: '运营后台登录' } },
    {
      path: '/admin',
      component: () => import('@/admin/AdminLayout.vue'),
      meta: { requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/admin/Dashboard.vue'), meta: { title: '数据看板' } },
        { path: 'trademarks', name: 'admin-trademarks', component: () => import('@/admin/TrademarkList.vue'), meta: { title: '商标列表' } },
        { path: 'trademarks/import', name: 'admin-import', component: () => import('@/admin/ImportWizard.vue'), meta: { title: '批量导入' } },
        { path: 'trademarks/batches', name: 'admin-batches', component: () => import('@/admin/BatchHistory.vue'), meta: { title: '导入批次' } },
        { path: 'trademarks/new', name: 'admin-tm-new', component: () => import('@/admin/TrademarkForm.vue'), meta: { title: '新增商标' } },
        { path: 'trademarks/:id/edit', name: 'admin-tm-edit', component: () => import('@/admin/TrademarkForm.vue'), meta: { title: '编辑商标' } },
        { path: 'submissions', name: 'admin-submissions', component: () => import('@/admin/SubmissionReview.vue'), meta: { title: '寄售审核' } },
        { path: 'content', name: 'admin-content', component: () => import('@/admin/ContentTransfer.vue'), meta: { title: '内容迁移' } },
        { path: 'customers', name: 'admin-customers', component: () => import('@/admin/Customers.vue'), meta: { title: '客户管理' } },
        { path: 'quotes', name: 'admin-quotes', component: () => import('@/admin/Quotes.vue'), meta: { title: '报价单管理' } },
        { path: 'expiring', name: 'admin-expiring', component: () => import('@/admin/Expiring.vue'), meta: { title: '到期提醒' } },
        { path: 'settings', name: 'admin-settings', component: () => import('@/admin/Settings.vue'), meta: { title: '网站配置' } },
        { path: 'admins', name: 'admin-accounts', component: () => import('@/admin/AdminAccounts.vue'), meta: { title: '运营账户' } },
        { path: 'logs', name: 'admin-logs', component: () => import('@/admin/Logs.vue'), meta: { title: '操作日志' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/site/NotFound.vue'), meta: { title: '页面不存在' } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAdmin && !localStorage.getItem('admin_token')) {
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  }
  return true
})

// 页面标题跟随路由（站点名由 branding.applyBranding 提供）
// 后台外壳页面用「页面 - 运营后台 · 站点名」，站名改了两处标题都会立即跟着变
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  const isAdminShell = to.path.startsWith('/admin') && to.path !== '/admin/login'
  if (isAdminShell) {
    setAdminPageTitle(title)
  } else {
    setPageTitle(title)
  }
})

export default router
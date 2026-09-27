import { createRouter, createWebHistory } from 'vue-router'

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
        { path: 'trademarks', name: 'site-list', component: () => import('@/site/TrademarkList.vue') },
        { path: 'trademark/:id', name: 'site-detail', component: () => import('@/site/TrademarkDetail.vue') },
        { path: 'cart', name: 'cart', component: () => import('@/site/QuoteCart.vue') },
        { path: 'login', name: 'site-login', component: () => import('@/site/Login.vue') },
        { path: 'register', name: 'site-register', component: () => import('@/site/Register.vue') },
        { path: 'user', name: 'user-center', component: () => import('@/site/UserCenter.vue') },
        { path: 'about', name: 'about', component: () => import('@/site/StaticPage.vue'), props: { page: 'about' } },
        { path: 'process', name: 'process', component: () => import('@/site/StaticPage.vue'), props: { page: 'process' } },
        { path: 'contact', name: 'contact', component: () => import('@/site/StaticPage.vue'), props: { page: 'contact' } },
      ],
    },
    { path: '/quote/:token', name: 'quote-share', component: () => import('@/site/QuoteShare.vue') },

    // ---------------- 后台 ----------------
    { path: '/admin/login', name: 'admin-login', component: () => import('@/admin/Login.vue') },
    {
      path: '/admin',
      component: () => import('@/admin/AdminLayout.vue'),
      meta: { requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/admin/Dashboard.vue') },
        { path: 'trademarks', name: 'admin-trademarks', component: () => import('@/admin/TrademarkList.vue') },
        { path: 'trademarks/import', name: 'admin-import', component: () => import('@/admin/ImportWizard.vue') },
        { path: 'trademarks/batches', name: 'admin-batches', component: () => import('@/admin/BatchHistory.vue') },
        { path: 'trademarks/new', name: 'admin-tm-new', component: () => import('@/admin/TrademarkForm.vue') },
        { path: 'trademarks/:id/edit', name: 'admin-tm-edit', component: () => import('@/admin/TrademarkForm.vue') },
        { path: 'customers', name: 'admin-customers', component: () => import('@/admin/Customers.vue') },
        { path: 'quotes', name: 'admin-quotes', component: () => import('@/admin/Quotes.vue') },
        { path: 'expiring', name: 'admin-expiring', component: () => import('@/admin/Expiring.vue') },
        { path: 'settings', name: 'admin-settings', component: () => import('@/admin/Settings.vue') },
        { path: 'admins', name: 'admin-accounts', component: () => import('@/admin/AdminAccounts.vue') },
        { path: 'logs', name: 'admin-logs', component: () => import('@/admin/Logs.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/site/NotFound.vue') },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAdmin && !localStorage.getItem('admin_token')) {
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
/**
 * 网页头（浏览器标题 / 图标）品牌化。
 *
 * 背景：后台改了站点名称、Logo、图标后，SPA 的 <title> 与 favicon 仍是 index.html 里的静态值，
 * 造成「后台改了但网页头没变」。这里在拿到站点配置后统一改写 document.title 与 <link rel="icon">。
 */

import { reactive } from 'vue'

let siteName = ''
let homeTitle = ''
let defaultIcon = ''
/** 记住当前页面标题，站点配置更新后可立刻重渲染，不必等下一次路由跳转 */
let lastPageTitle: string | undefined
let lastSuffix: string | undefined
/** 后台外壳页面：标题后缀统一为「运营后台 · 站点名」 */
let adminMode = false

/**
 * 当前站点品牌（响应式）：后台侧边栏、后台登录页直接绑这个，
 * 所以保存配置后会当场更新，不需要刷新页面。
 */
export const brandState = reactive({
  /** 站点名称 */
  name: '',
  /** Logo 图片地址，空则用首字母方块 */
  logo: '',
  /** 首字母，用于无 Logo 时的方块 */
  initial: '标',
})

function currentIconHref(): string {
  if (defaultIcon) return defaultIcon
  const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  defaultIcon = link?.getAttribute('href') || ''
  return defaultIcon
}

/** 设置浏览器标签页图标；传入空值则回退到内置图标 */
export function setFavicon(url?: string | null) {
  const href = (url || '').trim() || currentIconHref()
  if (!href) return
  let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.type = href.startsWith('data:image/svg') ? 'image/svg+xml' : ''
  link.href = href
  // 同步 apple-touch-icon，移动端「添加到主屏幕」也用同一张图
  let apple = document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')
  if (!apple) {
    apple = document.createElement('link')
    apple.rel = 'apple-touch-icon'
    document.head.appendChild(apple)
  }
  apple.href = href
}

/** 应用站点配置：站点名、首页标题、图标，并**立刻**重写当前页面标题与界面品牌 */
export function applyBranding(cfg?: { site_name?: string; seo_home_title?: string; logo_url?: string; favicon_url?: string } | null) {
  if (!cfg) return
  const name = (cfg.site_name || '').trim()
  if (name) siteName = name
  brandState.name = name
  brandState.initial = (name || '标').slice(0, 1)
  brandState.logo = cfg.logo_url || ''
  homeTitle = (cfg.seo_home_title || '').trim() || siteName
  setFavicon(cfg.favicon_url || cfg.logo_url)
  renderTitle()
}

function renderTitle() {
  if (!lastPageTitle) {
    document.title = homeTitle || siteName || document.title
    return
  }
  if (adminMode) {
    const tail = siteName ? `运营后台 · ${siteName}` : '运营后台'
    document.title = `${lastPageTitle} - ${tail}`
    return
  }
  const tail = lastSuffix || siteName
  document.title = tail ? `${lastPageTitle} - ${tail}` : lastPageTitle
}

/** 页面级标题：不传则回到首页标题 */
export function setPageTitle(pageTitle?: string, suffix?: string) {
  lastPageTitle = pageTitle
  lastSuffix = suffix
  adminMode = false
  renderTitle()
}

/** 后台外壳页面标题：后缀固定为「运营后台 · 站点名」，站名变了标题会跟着变 */
export function setAdminPageTitle(pageTitle?: string) {
  lastPageTitle = pageTitle
  adminMode = true
  renderTitle()
}

export function getSiteName() {
  return siteName
}
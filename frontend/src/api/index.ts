import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

export const http = axios.create({ baseURL: '', timeout: 180000 })

/** 后台用 admin_token，前台用 user_token；前台接口也允许携带用户令牌以支持收藏等 */
http.interceptors.request.use((cfg) => {
  const url = cfg.url || ''
  const isAdmin = url.startsWith('/api/admin')
  const token = isAdmin
    ? localStorage.getItem('admin_token')
    : localStorage.getItem('user_token') || ''
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err?.response?.status
    const detail = err?.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : err.message || '请求失败'
    if (status === 401 && location.pathname.startsWith('/admin')) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_profile')
      if (!location.pathname.includes('/admin/login')) {
        ElMessage.error('登录已失效，请重新登录')
        location.href = '/admin/login'
      }
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(err)
  },
)

// --------------------------------------------------------------------------- //
// 类型
// --------------------------------------------------------------------------- //
export interface ColumnDef {
  key: string
  label: string
  kind: 'core' | 'extra' | 'system'
  data_type: 'text' | 'number' | 'date' | 'price' | 'image'
  sort?: number
  visible?: boolean
  filled_count: number
  first_seen_file?: string | null
}

export interface TrademarkRow {
  id: number
  /** 唯一编号：系统生成，如 TM-20260927-0001，内部识别用 */
  serial_no: string
  /** 商标编号：官方注册号，来自 Excel，如 711386408046645262 */
  trademark_no: string | null
  name: string
  category: number | null
  /** 金额：null 表示源表没有价格，前台显示「面议」 */
  price: number | null
  has_price: boolean
  status: 'on_sale' | 'off_shelf' | 'sold' | 'reserved'
  is_featured: boolean
  registration_date: string | null
  expiry_date?: string | null
  legal_status?: string | null
  application_count: number | null
  groups?: string | null
  products?: string | null
  ai_description?: string | null
  remark?: string | null
  view_count: number
  quote_count: number
  source_file?: string | null
  source_row?: number | null
  /** 动态列数据：Excel 里带进来、系统未预置的列 */
  extra: Record<string, unknown>
  created_at: string | null
  images: { url: string; is_primary: boolean }[]
}

export interface Page<T> {
  total: number
  page: number
  page_size: number
  columns?: ColumnDef[]
  items: T[]
  hints?: string[]
}

export interface ImportBatch {
  id: number
  filename: string
  sheet_name: string | null
  total_rows: number
  image_count: number
  status: 'pending' | 'running' | 'done' | 'failed' | 'analyzing'
  progress: number
  success_count: number
  updated_count: number
  skipped_count: number
  failed_count: number
  message: string | null
  created_at: string | null
  finished_at: string | null
  column_count: number
  columns: {
    key: string
    header: string
    label: string
    mapped_field: string | null
    data_type: string
    samples: string[]
    non_empty: number
  }[]
  errors: { row: number; reason: string }[]
  options: Record<string, unknown>
}

export interface ImportPreview {
  batch_id: number
  filename: string
  sheet_name: string
  total_rows: number
  image_count: number
  columns: ImportBatch['columns']
  warnings: string[]
  preview_rows: { excel_row: number; cells: Record<string, unknown>; images: string[] }[]
  auto_mapping: Record<string, string>
}

export interface PublicCard {
  id: number
  name: string
  category: number | null
  trademark_no: string | null
  price: number | null
  price_text: string
  status: { code: string; label: string }
  is_featured: boolean
  registration_date: string | null
  image: string | null
  view_count: number
}

export interface SiteConfig {
  site_name: string
  site_subtitle: string
  logo_url: string
  icp: string
  copyright: string
  contact_phone: string
  address: string
  company_intro: string
  service_wechat: string
  service_qr: string
  service_hours: string
  service_text: string
  process_steps: { title: string; desc: string }[]
  display_fields: Record<string, boolean>
  seo_home_title: string
  seo_home_keywords: string
  seo_home_desc: string
  quote_default_days: string
  banner: { image_url?: string; url?: string; title?: string; subtitle?: string }[]
}

export interface QuoteItem {
  trademark_id: number
  serial_no?: string
  trademark_no?: string
  name: string
  category: number | null
  original_price: number | null
  quote_price: number | null
  image: string | null
}

export interface Quote {
  id: number
  quote_no: string
  token: string
  title: string
  customer_name: string | null
  contact_phone: string | null
  remark: string | null
  total_original: number
  total_quote: number
  has_password: boolean
  expire_at: string | null
  status: string
  view_count: number
  created_at: string | null
  item_count: number
  items?: QuoteItem[]
}

// --------------------------------------------------------------------------- //
// 通用
// --------------------------------------------------------------------------- //
function get<T>(url: string, params?: Record<string, unknown>, cfg?: AxiosRequestConfig) {
  return http.get<T>(url, { params, ...cfg }).then((r) => r.data)
}
function post<T>(url: string, data?: unknown) {
  return http.post<T>(url, data).then((r) => r.data)
}
function put<T>(url: string, data?: unknown) {
  return http.put<T>(url, data).then((r) => r.data)
}
function del<T>(url: string, params?: Record<string, unknown>) {
  return http.delete<T>(url, { params }).then((r) => r.data)
}

export function download(url: string, params?: Record<string, unknown>, method: 'get' | 'post' = 'get',
                         body?: unknown, filename?: string) {
  const req = method === 'post' ? http.post(url, body, { responseType: 'blob' }) : http.get(url, { params, responseType: 'blob' })
  return req.then((r) => {
    const disp = String(r.headers['content-disposition'] || '')
    let name = filename || 'download.xlsx'
    const m = disp.match(/filename\*=UTF-8''([^;]+)/)
    if (m) name = decodeURIComponent(m[1])
    const blobUrl = URL.createObjectURL(r.data as Blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = name
    a.click()
    URL.revokeObjectURL(blobUrl)
  })
}

// --------------------------------------------------------------------------- //
// 认证
// --------------------------------------------------------------------------- //
export const authApi = {
  adminLogin: (username: string, password: string) =>
    post<{ token: string; admin: { id: number; username: string; name: string; role: string } }>(
      '/api/admin/auth/login', { username, password }),
  adminMe: () => get<{ id: number; username: string; name: string; role: string }>('/api/admin/auth/me'),
  userLogin: (phone: string, password: string) =>
    post<{ token: string; user: { id: number; phone: string; nickname: string } }>(
      '/api/auth/login', { phone, password }),
  userRegister: (payload: Record<string, unknown>) =>
    post<{ token: string; user: { id: number; phone: string; nickname: string } }>(
      '/api/auth/register', payload),
  userMe: () => get<{ id: number; phone: string; email: string; nickname: string }>('/api/auth/me'),
}

// --------------------------------------------------------------------------- //
// 后台 · 商标
// --------------------------------------------------------------------------- //
export const adminTrademarkApi = {
  list: (params: Record<string, unknown>) => get<Page<TrademarkRow>>('/api/admin/trademarks', params),
  detail: (id: number) => get<TrademarkRow>(`/api/admin/trademarks/${id}`),
  create: (payload: Record<string, unknown>) => post<TrademarkRow>('/api/admin/trademarks', payload),
  update: (id: number, payload: Record<string, unknown>) => put<TrademarkRow>(`/api/admin/trademarks/${id}`, payload),
  remove: (id: number) => del(`/api/admin/trademarks/${id}`),
  batch: (payload: Record<string, unknown>) =>
    post<{ ok: boolean; affected: number; detail: Record<string, unknown> }>('/api/admin/trademarks/batch', payload),
  filterOptions: () => get<{
    categories: { value: number; count: number }[]
    statuses: { value: string; count: number }[]
    price_min: number | null
    price_max: number | null
    unpriced: number
  }>('/api/admin/trademarks/filter-options'),
  columns: () => get<{ items: ColumnDef[] }>('/api/admin/columns'),
  updateColumn: (key: string, payload: Record<string, unknown>) =>
    put(`/api/admin/trademarks/columns/${encodeURIComponent(key)}`, payload),
  export: (payload: Record<string, unknown>) =>
    download('/api/admin/trademarks/export', undefined, 'post', payload, '商标列表.xlsx'),
}

// --------------------------------------------------------------------------- //
// 后台 · 导入
// --------------------------------------------------------------------------- //
export const adminImportApi = {
  upload: (files: File[]) => {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return http.post<{ batches: ImportBatch[]; failed: { filename: string; reason: string }[] }>(
      '/api/admin/imports/upload', fd).then((r) => r.data)
  },
  preview: (batchId: number, limit = 20) =>
    get<ImportPreview>(`/api/admin/imports/${batchId}/preview`, { limit }),
  status: (batchId: number) => get<ImportBatch>(`/api/admin/imports/${batchId}/status`),
  commit: (payload: Record<string, unknown>) =>
    post<{ ok: boolean; batch_id: number }>('/api/admin/imports/commit', payload),
  history: (limit = 50) => get<{ items: ImportBatch[] }>('/api/admin/imports/history', { limit }),
  remove: (batchId: number, purgeData = false) =>
    del(`/api/admin/imports/${batchId}`, purgeData ? { purge_data: true } : undefined),
  template: () => download('/api/admin/imports/template', undefined, 'get', undefined, '商标导入模板.xlsx'),
}

// --------------------------------------------------------------------------- //
// 后台 · 杂项
// --------------------------------------------------------------------------- //
export const adminApi = {
  stats: () => get<Record<string, any>>('/api/admin/stats'),
  settings: () => get<{ values: Record<string, string> }>('/api/admin/settings'),
  saveSettings: (values: Record<string, unknown>) => put('/api/admin/settings', { values }),
  logs: (params: Record<string, unknown>) => get<Record<string, any>>('/api/admin/logs', params),
  expiring: (days = 90) => get<{ items: Record<string, any>[] }>('/api/admin/expiring', { days }),
  customers: (params: Record<string, unknown>) => get<Record<string, any>>('/api/admin/customers', params),
  updateCustomer: (id: number, payload: Record<string, unknown>) => put(`/api/admin/customers/${id}`, payload),
  quotes: (params: Record<string, unknown>) => get<Record<string, any>>('/api/admin/quotes', params),
  cancelQuote: (id: number) => post(`/api/admin/quotes/${id}/cancel`),
  admins: () => get<{ items: Record<string, any>[] }>('/api/admin/admins'),
  createAdmin: (payload: Record<string, unknown>) => post('/api/admin/admins', payload),
  updateAdmin: (id: number, payload: Record<string, unknown>) => put(`/api/admin/admins/${id}`, payload),
  deleteAdmin: (id: number) => del(`/api/admin/admins/${id}`),
  banners: () => get<{ items: Record<string, any>[] }>('/api/admin/banners'),
  createBanner: (payload: Record<string, unknown>) => post('/api/admin/banners', payload),
  updateBanner: (id: number, payload: Record<string, unknown>) => put(`/api/admin/banners/${id}`, payload),
  deleteBanner: (id: number) => del(`/api/admin/banners/${id}`),
  notifications: () => get<{ items: Record<string, any>[] }>('/api/admin/notifications'),
  upload: (file: File, scene = 'common') => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post<{ ok: boolean; url: string }>(`/api/admin/upload?scene=${scene}`, fd).then((r) => r.data)
  },
}

// --------------------------------------------------------------------------- //
// 前台
// --------------------------------------------------------------------------- //
export const siteApi = {
  config: () => get<SiteConfig>('/api/site/config'),
  home: () => get<{
    config: SiteConfig
    banners: SiteConfig['banner']
    featured: PublicCard[]
    latest: PublicCard[]
    categories: { value: number; count: number }[]
    stats: { on_sale: number; total: number; categories: number }
  }>('/api/site/home'),
  list: (params: Record<string, unknown>) => get<Page<PublicCard> & {
    facets: { categories: { value: number; count: number }[]; price_min: number | null; price_max: number | null }
  }>('/api/trademarks', params),
  detail: (id: number) => get<{
    trademark: PublicCard & Record<string, any>
    config: SiteConfig
    recommend: PublicCard[]
  }>(`/api/trademarks/${id}`),
  favoriteIds: () => get<{ ids: number[] }>('/api/favorites/ids'),
  favorites: () => get<{ items: PublicCard[] }>('/api/favorites'),
  addFavorite: (id: number) => post(`/api/favorites/${id}`),
  removeFavorite: (id: number) => del(`/api/favorites/${id}`),
}

export const quoteApi = {
  create: (payload: Record<string, unknown>) =>
    post<{ ok: boolean; quote: Quote; share_path: string }>('/api/quotes', payload),
  mine: () => get<{ items: Quote[] }>('/api/quotes'),
  remove: (id: number) => del(`/api/quotes/${id}`),
  share: (token: string, password?: string) =>
    get<{ need_password: boolean; expired?: boolean; title?: string; quote?: Quote; config?: SiteConfig }>(
      `/api/quotes/share/${token}`, password ? { password } : undefined),
  exportExcel: (token: string, password?: string) =>
    download(`/api/quotes/share/${token}/export`, password ? { password } : undefined, 'get',
      undefined, '商标报价单.xlsx'),
}

export function fileUrl(url?: string | null) {
  if (!url) return ''
  if (url.startsWith('http') || url.startsWith('data:')) return url
  return url
}
<template>
  <div class="site-container">
    <h1 class="page-title">个人中心</h1>

    <div v-if="!user.isLoggedIn" class="empty-state">
      <h3>请先登录</h3>
      <p>登录后可查看收藏的商标与已生成的报价单。</p>
      <el-button type="primary" size="large" @click="$router.push({ path: '/login', query: { redirect: '/user' } })">
        去登录
      </el-button>
    </div>

    <el-tabs v-else v-model="activeTab" class="uc-tabs">
      <!-- 我的收藏 -->
      <el-tab-pane label="我的收藏" name="favorites">
        <div v-loading="favLoading">
          <div v-if="favorites.length" class="fav-toolbar">
            <el-checkbox
              :model-value="allSelected"
              :indeterminate="someSelected"
              @change="(v: boolean | string | number) => toggleAll(!!v)"
            >
              全选（已选 {{ selected.length }} 件）
            </el-checkbox>
            <el-button type="primary" :icon="Tickets" :disabled="!selected.length" @click="batchAddToCart">
              批量加入报价单
            </el-button>
          </div>

          <div v-if="favorites.length" class="fav-list">
            <div v-for="card in favorites" :key="card.id" class="fav-row">
              <el-checkbox
                :model-value="selected.includes(card.id)"
                :aria-label="`选择 ${card.name}`"
                @change="(v: boolean | string | number) => toggleOne(card.id, !!v)"
              />
              <el-image
                v-if="card.image"
                :src="card.image"
                fit="contain"
                :alt="`${card.name} 图样`"
                class="fav-thumb"
                @click="$router.push(`/trademark/${card.id}`)"
              />
              <div v-else class="fav-thumb fav-thumb--empty">暂无图样</div>
              <div class="fav-main">
                <router-link :to="`/trademark/${card.id}`" class="fav-name">{{ card.name }}</router-link>
                <div class="fav-meta">
                  <span>{{ card.category ? `${card.category}类` : '类别待确认' }}</span>
                  <span>注册号 <span class="mono-id">{{ card.trademark_no || '—' }}</span></span>
                </div>
              </div>
              <span class="fav-price">
                <template v-if="card.price !== null">¥{{ card.price.toLocaleString() }}</template>
                <template v-else>面议</template>
              </span>
              <div class="fav-actions">
                <el-button link type="primary" @click="$router.push(`/trademark/${card.id}`)">查看</el-button>
                <el-button link type="danger" @click="cancelFavorite(card.id, card.name)">取消收藏</el-button>
              </div>
            </div>
          </div>

          <div v-else-if="!favLoading" class="empty-state">
            <h3>还没有收藏任何商标</h3>
            <p>在商标卡片右下角点击星标即可收藏。</p>
            <el-button type="primary" @click="$router.push('/trademarks')">去浏览商标</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 我的报价单 -->
      <el-tab-pane label="我的报价单" name="quotes">
        <div v-loading="quoteLoading">
          <div v-if="quotes.length" class="table-scroll">
            <table class="quote-table">
              <thead>
                <tr>
                  <th>报价单号</th>
                  <th>标题</th>
                  <th class="ta-right">商标数</th>
                  <th class="ta-right">报价合计</th>
                  <th>状态</th>
                  <th>有效期至</th>
                  <th class="ta-right">访问</th>
                  <th>生成时间</th>
                  <th class="ta-center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="q in quotes" :key="q.id">
                  <td class="mono-id">{{ q.quote_no }}</td>
                  <td>{{ q.title }}</td>
                  <td class="ta-right num">{{ q.item_count }}</td>
                  <td class="ta-right num">¥{{ q.total_quote.toLocaleString() }}</td>
                  <td>
                    <el-tag :type="statusType(q.status)" effect="light" size="small">{{ statusLabel(q.status) }}</el-tag>
                  </td>
                  <td>{{ q.expire_at || '长期' }}</td>
                  <td class="ta-right num">{{ q.view_count }}</td>
                  <td>{{ q.created_at }}</td>
                  <td class="ta-center quote-ops">
                    <el-button link type="primary" @click="$router.push(`/quote/${q.token}`)">查看</el-button>
                    <el-button link @click="copyShare(q.token)">复制链接</el-button>
                    <el-button link @click="exportQuote(q)">导出</el-button>
                    <el-button link type="danger" @click="removeQuote(q.id, q.quote_no)">删除</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="!quoteLoading" class="empty-state">
            <h3>还没有生成过报价单</h3>
            <p>在报价单中挑选商标后即可一键生成分享链接。</p>
            <el-button type="primary" @click="$router.push('/cart')">查看报价单</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 我的寄售 -->
      <el-tab-pane name="submissions">
        <template #label>
          <span class="tab-label">
            我的寄售
            <el-badge v-if="subCounts.pending" :value="subCounts.pending" class="tab-badge" />
          </span>
        </template>
        <div v-loading="subLoading">
          <template v-if="submissions.length">
            <div class="sub-stats">
              <span>共 <b class="num">{{ subCounts.total }}</b> 条</span>
              <span>待审核 <b class="num sub-stats--pending">{{ subCounts.pending }}</b></span>
              <span>已通过 <b class="num sub-stats--approved">{{ subCounts.approved }}</b></span>
              <span>已驳回 <b class="num sub-stats--rejected">{{ subCounts.rejected }}</b></span>
            </div>

            <div class="sub-list">
              <div
                v-for="row in submissions"
                :key="row.id"
                class="sub-row"
                :class="{ 'sub-row--rejected': row.review_status === 'rejected' }"
              >
                <el-image
                  v-if="row.designs[0]?.url"
                  :src="row.designs[0].url"
                  :preview-src-list="row.designs.map((d) => d.url)"
                  preview-teleported
                  fit="contain"
                  :alt="`${row.name} 图样`"
                  class="sub-thumb"
                />
                <div v-else class="sub-thumb sub-thumb--empty">暂无图样</div>

                <div class="sub-main">
                  <div class="sub-name-line">
                    <span class="sub-name">{{ row.name }}</span>
                    <el-tag :type="reviewType(row.review_status)" effect="light" size="small">
                      {{ row.review_label }}
                    </el-tag>
                  </div>
                  <div class="sub-meta">
                    <span>{{ row.category ? `${row.category}类` : '类别待确认' }}</span>
                    <span>期望售价 <span class="num">{{ row.price !== null ? `¥${row.price.toLocaleString()}` : '未定价' }}</span></span>
                    <span class="sub-id">
                      唯一编号 <span class="mono-id">{{ row.serial_no }}</span>
                      <span class="id-badge id-badge--serial">系统生成</span>
                    </span>
                    <span class="sub-id">
                      商标编号 <span class="mono-id">{{ row.trademark_no || '—' }}</span>
                      <span class="id-badge id-badge--official">官方注册号</span>
                    </span>
                    <span>提交于 {{ row.created_at || '—' }}</span>
                  </div>
                  <el-alert
                    v-if="row.review_status === 'rejected' && row.review_remark"
                    type="error"
                    :closable="false"
                    :title="`驳回原因：${row.review_remark}`"
                    class="sub-reject"
                  />
                </div>

                <div class="sub-actions">
                  <template v-if="row.review_status !== 'approved'">
                    <el-button link type="primary" @click="openEdit(row)">修改并重新提交</el-button>
                    <el-button link type="danger" @click="withdraw(row)">撤回</el-button>
                  </template>
                  <template v-else>
                    <span class="sub-approved-note">已通过 · 前台可见状态以平台为准</span>
                    <router-link v-if="row.status === 'on_sale'" class="sub-link" :to="`/trademark/${row.id}`">
                      查看前台页 →
                    </router-link>
                  </template>
                </div>
              </div>
            </div>
          </template>

          <div v-else-if="!subLoading" class="empty-state">
            <h3>还没有提交过商标</h3>
            <p>把闲置商标托管到平台，我们负责展示、撮合与过户。</p>
            <el-button type="primary" @click="$router.push('/sell')">去提交我的第一个商标</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 账户信息 -->
      <el-tab-pane label="账户信息" name="profile">
        <div class="panel-card profile-card">
          <div class="profile-row"><span class="profile-label">手机号</span><span>{{ me?.phone || user.profile?.phone || '—' }}</span></div>
          <div class="profile-row"><span class="profile-label">昵称</span><span>{{ me?.nickname || user.profile?.nickname || '—' }}</span></div>
          <div class="profile-row"><span class="profile-label">邮箱</span><span>{{ me?.email || '未填写' }}</span></div>
          <div class="profile-row"><span class="profile-label">注册时间</span><span>{{ me?.created_at || '—' }}</span></div>
          <el-button type="danger" plain class="logout-btn" @click="logout">退出登录</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 修改并重新提交 -->
    <el-dialog v-model="editVisible" title="修改并重新提交" width="560px" :close-on-click-modal="false">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top" @submit.prevent>
        <div class="edit-grid">
          <el-form-item label="商标名" prop="name" class="edit-grid__full">
            <el-input v-model="editForm.name" maxlength="60" placeholder="与注册证一致" />
          </el-form-item>
          <el-form-item label="类别" prop="category">
            <el-select v-model="editForm.category" placeholder="选择类别" filterable class="full">
              <el-option v-for="c in categoryOptions" :key="c" :label="`第 ${c} 类`" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item label="注册日期" prop="registration_date">
            <el-date-picker v-model="editForm.registration_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" class="full" />
          </el-form-item>
          <el-form-item label="商标编号 / 注册号" prop="trademark_no" class="edit-grid__full">
            <el-input v-model="editForm.trademark_no" placeholder="选填，如 711386408046645262" />
          </el-form-item>
          <el-form-item label="群组" prop="groups">
            <el-input v-model="editForm.groups" placeholder="选填，如 2901；2902" />
          </el-form-item>
          <el-form-item label="期望售价（元）" prop="price">
            <el-input-number v-model="editForm.price" :min="1" :step="100" :precision="2" :controls="false" class="full" />
          </el-form-item>
          <el-form-item label="联系人" prop="contact_name">
            <el-input v-model="editForm.contact_name" maxlength="30" placeholder="联系人" />
          </el-form-item>
          <el-form-item label="联系电话" prop="contact_phone">
            <el-input v-model="editForm.contact_phone" maxlength="20" placeholder="联系电话" />
          </el-form-item>
          <el-form-item label="产品 / 服务" prop="products" class="edit-grid__full">
            <el-input v-model="editForm.products" type="textarea" :rows="2" maxlength="500" placeholder="选填" />
          </el-form-item>
          <el-form-item label="备注" prop="remark" class="edit-grid__full">
            <el-input v-model="editForm.remark" type="textarea" :rows="2" maxlength="300" placeholder="选填" />
          </el-form-item>
        </div>

        <!-- 商标图样 -->
        <div class="edit-upload">
          <div class="edit-upload__head">商标图样 <span class="req">必传 · 至少 1 张</span></div>
          <p class="edit-upload__hint">用于前台展示，可多张。</p>
          <div class="edit-upload__grid">
            <div v-for="(url, i) in editDesigns" :key="url" class="edit-thumb">
              <el-image :src="url" :preview-src-list="editDesigns" :initial-index="i" preview-teleported fit="contain" class="edit-thumb__img" />
              <button type="button" class="edit-thumb__del" aria-label="删除该图样" @click="editDesigns.splice(i, 1)">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <el-upload :show-file-list="false" :http-request="uploadEditDesign" :accept="IMAGE_ACCEPT" :disabled="editUploadingDesign" class="upload-trigger">
              <div class="edit-box" :class="{ 'edit-box--loading': editUploadingDesign }">
                <el-icon><Plus /></el-icon>
                <span>{{ editUploadingDesign ? '上传中…' : '上传图样' }}</span>
              </div>
            </el-upload>
          </div>
        </div>

        <!-- 商标证 -->
        <div class="edit-upload">
          <div class="edit-upload__head">商标证 <span class="req">必传 · 至少 1 张</span></div>
          <p class="edit-upload__hint">注册证扫描件 / 照片，仅平台与你本人可见。</p>
          <div class="edit-upload__grid">
            <div v-for="(url, i) in editCerts" :key="url" class="edit-thumb">
              <el-image :src="url" :preview-src-list="editCerts" :initial-index="i" preview-teleported fit="contain" class="edit-thumb__img" />
              <button type="button" class="edit-thumb__del" aria-label="删除该商标证" @click="editCerts.splice(i, 1)">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <el-upload :show-file-list="false" :http-request="uploadEditCert" :accept="IMAGE_ACCEPT" :disabled="editUploadingCert" class="upload-trigger">
              <div class="edit-box edit-box--wide" :class="{ 'edit-box--loading': editUploadingCert }">
                <el-icon><UploadFilled /></el-icon>
                <span>{{ editUploadingCert ? '上传中…' : '上传注册证' }}</span>
              </div>
            </el-upload>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadRequestOptions } from 'element-plus'
import { Close, Plus, Tickets, UploadFilled } from '@element-plus/icons-vue'
import {
  authApi, quoteApi, siteApi, submissionApi,
  type PublicCard, type Quote, type SubmissionCounts, type SubmissionPayload, type TrademarkRow,
} from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const IMAGE_ACCEPT = '.png,.jpg,.jpeg,.gif,.webp,.svg'
const categoryOptions = Array.from({ length: 45 }, (_, i) => i + 1)
const TAB_NAMES = ['favorites', 'quotes', 'submissions', 'profile']
const initialTab = typeof route.query.tab === 'string' && TAB_NAMES.includes(route.query.tab) ? route.query.tab : 'favorites'

const activeTab = ref(initialTab)
const favLoading = ref(false)
const quoteLoading = ref(false)
const favorites = ref<PublicCard[]>([])
const quotes = ref<Quote[]>([])
const selected = ref<number[]>([])
const me = ref<{ id?: number; phone?: string; nickname?: string; email?: string; created_at?: string } | null>(null)

// 我的寄售
const subLoading = ref(false)
const submissions = ref<TrademarkRow[]>([])
const subCounts = ref<SubmissionCounts>({ total: 0, pending: 0, approved: 0, rejected: 0 })
const editVisible = ref(false)
const editSaving = ref(false)
const editFormRef = ref<FormInstance>()
const editingId = ref<number | null>(null)
const editDesigns = ref<string[]>([])
const editCerts = ref<string[]>([])
const editUploadingDesign = ref(false)
const editUploadingCert = ref(false)
const editForm = reactive({
  name: '',
  category: null as number | null,
  trademark_no: '',
  registration_date: '' as string,
  groups: '',
  products: '',
  price: null as number | null,
  contact_name: '',
  contact_phone: '',
  remark: '',
})
const editRules: FormRules = {
  name: [{ required: true, message: '请填写商标名', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
  price: [{ required: true, message: '请填写期望售价', trigger: 'change' }],
  contact_name: [{ required: true, message: '请填写联系人', trigger: 'blur' }],
  contact_phone: [{ required: true, message: '请填写联系电话', trigger: 'blur' }],
}

const allSelected = computed(() => favorites.value.length > 0 && selected.value.length === favorites.value.length)
const someSelected = computed(() => selected.value.length > 0 && !allSelected.value)

function statusLabel(s: string) {
  return ({ active: '有效', expired: '已过期', cancelled: '已作废' } as Record<string, string>)[s] || s
}
function statusType(s: string) {
  return ({ active: 'success', expired: 'warning', cancelled: 'info' } as const)[s as 'active' | 'expired' | 'cancelled'] || 'info'
}

function toggleAll(v: boolean) {
  selected.value = v ? favorites.value.map((c) => c.id) : []
}
function toggleOne(id: number, v: boolean) {
  if (v) selected.value = [...selected.value, id]
  else selected.value = selected.value.filter((x) => x !== id)
}

async function loadFavorites() {
  favLoading.value = true
  try {
    const res = await siteApi.favorites()
    favorites.value = res.items
    await user.loadFavorites()
    selected.value = selected.value.filter((id) => res.items.some((c) => c.id === id))
  } finally {
    favLoading.value = false
  }
}

async function cancelFavorite(id: number, name: string) {
  await ElMessageBox.confirm(`确定取消收藏「${name}」吗？`, '取消收藏', { type: 'warning' })
  try {
    await user.toggleFavorite(id)
    favorites.value = favorites.value.filter((c) => c.id !== id)
    selected.value = selected.value.filter((x) => x !== id)
    ElMessage.success('已取消收藏')
  } catch {
    /* 拦截器已提示 */
  }
}

function batchAddToCart() {
  const items = favorites.value.filter((c) => selected.value.includes(c.id))
  let added = 0
  items.forEach((c) => {
    if (user.addToCart(c)) added += 1
  })
  if (added) ElMessage.success(`已加入 ${added} 件到报价单`)
  if (added < items.length) ElMessage.info(`${items.length - added} 件已在报价单中`)
  if (added) selected.value = []
}

async function loadQuotes() {
  quoteLoading.value = true
  try {
    const res = await quoteApi.mine()
    quotes.value = res.items
  } finally {
    quoteLoading.value = false
  }
}

function copyShare(token: string) {
  const url = location.origin + `/quote/${token}`
  navigator.clipboard?.writeText(url)
  ElMessage.success('分享链接已复制')
}

async function exportQuote(q: Quote) {
  let password: string | undefined
  if (q.has_password) {
    try {
      const { value } = await ElMessageBox.prompt('该报价单设置了访问密码，请输入后导出', '访问密码', {
        inputType: 'password',
        confirmButtonText: '导出',
      })
      password = value
    } catch {
      return
    }
  }
  try {
    await quoteApi.exportExcel(q.token, password)
  } catch {
    /* 拦截器已提示 */
  }
}

async function removeQuote(id: number, no: string) {
  await ElMessageBox.confirm(`确定删除报价单「${no}」吗？删除后分享链接将失效。`, '删除确认', { type: 'warning' })
  await quoteApi.remove(id)
  quotes.value = quotes.value.filter((q) => q.id !== id)
  ElMessage.success('已删除')
}

function logout() {
  user.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}

async function loadMe() {
  try {
    me.value = await authApi.userMe()
  } catch {
    /* 拦截器已提示 */
  }
}

// ───────── 我的寄售 ─────────
function reviewType(s: TrademarkRow['review_status']) {
  return ({ pending: 'warning', approved: 'success', rejected: 'danger' } as const)[s] || 'info'
}

async function loadSubmissions() {
  subLoading.value = true
  try {
    const res = await submissionApi.mine()
    submissions.value = res.items
    subCounts.value = res.counts
  } finally {
    subLoading.value = false
  }
}

function openEdit(row: TrademarkRow) {
  editingId.value = row.id
  editForm.name = row.name || ''
  editForm.category = row.category
  editForm.trademark_no = row.trademark_no || ''
  editForm.registration_date = row.registration_date || ''
  editForm.groups = row.groups || ''
  editForm.products = row.products || ''
  editForm.price = row.price
  editForm.contact_name = row.contact_name || user.profile?.nickname || ''
  editForm.contact_phone = row.contact_phone || user.profile?.phone || ''
  editForm.remark = row.remark || ''
  editDesigns.value = (row.designs || []).map((d) => d.url)
  editCerts.value = (row.certificates || []).map((c) => c.url)
  editVisible.value = true
}

async function handleEditUpload(options: UploadRequestOptions, target: typeof editDesigns, flag: typeof editUploadingDesign) {
  flag.value = true
  try {
    const res = await submissionApi.upload(options.file as File)
    target.value.push(res.url)
    options.onSuccess?.(res)
  } catch (err) {
    options.onError?.(err as never)
  } finally {
    flag.value = false
  }
}
function uploadEditDesign(options: UploadRequestOptions) {
  return handleEditUpload(options, editDesigns, editUploadingDesign)
}
function uploadEditCert(options: UploadRequestOptions) {
  return handleEditUpload(options, editCerts, editUploadingCert)
}

async function saveEdit() {
  if (editingId.value === null) return
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!editDesigns.value.length) {
    ElMessage.warning('请至少保留 1 张商标图样')
    return
  }
  if (!editCerts.value.length) {
    ElMessage.warning('请至少保留 1 张商标证')
    return
  }
  const payload: SubmissionPayload = {
    name: editForm.name.trim(),
    category: editForm.category,
    trademark_no: editForm.trademark_no.trim() || null,
    registration_date: editForm.registration_date || null,
    expiry_date: null,
    groups: editForm.groups.trim() || null,
    products: editForm.products.trim() || null,
    legal_status: null,
    ai_description: null,
    remark: editForm.remark.trim() || null,
    price: editForm.price,
    contact_name: editForm.contact_name.trim(),
    contact_phone: editForm.contact_phone.trim(),
    design_images: [...editDesigns.value],
    certificates: [...editCerts.value],
  }
  editSaving.value = true
  try {
    await submissionApi.update(editingId.value, payload)
    editVisible.value = false
    ElMessage.success('已重新提交，等待平台审核')
    await loadSubmissions()
  } catch {
    /* 拦截器已提示 */
  } finally {
    editSaving.value = false
  }
}

async function withdraw(row: TrademarkRow) {
  await ElMessageBox.confirm(`确定撤回「${row.name}」的寄售申请吗？`, '撤回确认', { type: 'warning' })
  try {
    await submissionApi.withdraw(row.id)
    ElMessage.success('已撤回')
    await loadSubmissions()
  } catch {
    /* 拦截器已提示 */
  }
}

onMounted(() => {
  if (!user.isLoggedIn) return
  loadFavorites()
  loadQuotes()
  loadSubmissions()
  loadMe()
})
</script>

<style scoped>
.uc-tabs {
  margin-top: var(--space-4);
}
.fav-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.fav-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.fav-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-card);
}
.fav-thumb {
  width: 56px;
  height: 56px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  flex: none;
  cursor: pointer;
}
.fav-thumb--empty {
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--color-subtle-fg);
}
.fav-main {
  flex: 1;
  min-width: 0;
}
.fav-name {
  color: var(--color-fg);
  font-weight: 600;
}
.fav-name:hover {
  color: var(--color-accent);
}
.fav-meta {
  display: flex;
  gap: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
  margin-top: 2px;
}
.fav-price {
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: var(--color-primary);
  flex: none;
}
.fav-actions {
  display: flex;
  gap: var(--space-2);
  flex: none;
}
.table-scroll {
  overflow-x: auto;
}
.quote-table {
  min-width: 940px;
}
.ta-right {
  text-align: right;
}
.ta-center {
  text-align: center;
}
.quote-ops {
  white-space: nowrap;
}
.profile-card {
  max-width: 520px;
}
.profile-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border);
}
.profile-row:last-of-type {
  border-bottom: none;
}
.profile-label {
  color: var(--color-muted-fg);
}
.logout-btn {
  margin-top: var(--space-5);
  height: 44px;
}
@media (max-width: 820px) {
  .fav-row {
    flex-wrap: wrap;
  }
  .fav-main {
    flex-basis: calc(100% - 120px);
  }
}
</style>
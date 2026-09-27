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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { authApi, quoteApi, siteApi, type PublicCard, type Quote } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const user = useUserStore()

const activeTab = ref('favorites')
const favLoading = ref(false)
const quoteLoading = ref(false)
const favorites = ref<PublicCard[]>([])
const quotes = ref<Quote[]>([])
const selected = ref<number[]>([])
const me = ref<{ id?: number; phone?: string; nickname?: string; email?: string; created_at?: string } | null>(null)

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

onMounted(() => {
  if (!user.isLoggedIn) return
  loadFavorites()
  loadQuotes()
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
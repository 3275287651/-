<template>
  <div class="site-container">
    <h1 class="page-title">全部商标</h1>
    <p class="page-sub">共 <b class="num">{{ total }}</b> 件在售商标，均为自有货源，价格公开透明</p>

    <!-- 筛选 -->
    <section class="filter-panel">
      <div class="filter-row">
        <el-input
          v-model="query.q"
          class="filter-search"
          placeholder="搜索商标名 / 注册号"
          clearable
          @keyup.enter="applyFilters"
          @clear="applyFilters"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" :icon="Search" @click="applyFilters">搜索</el-button>
        <div class="filter-spacer" />
        <el-select v-model="sortValue" class="filter-sort" aria-label="排序方式" @change="applyFilters">
          <el-option v-for="s in SORTS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
      </div>

      <div class="filter-row">
        <span class="filter-row__label">类别</span>
        <button type="button" class="chip" :class="{ 'chip--active': query.category === null }" @click="setCategory(null)">
          全部
        </button>
        <button
          v-for="c in facets.categories"
          :key="c.value"
          type="button"
          class="chip"
          :class="{ 'chip--active': query.category === c.value }"
          @click="setCategory(c.value)"
        >
          {{ c.value }}类 <span class="chip__count num">{{ c.count }}</span>
        </button>
      </div>

      <div class="filter-row">
        <span class="filter-row__label">价格</span>
        <button
          v-for="p in PRICE_PRESETS"
          :key="p.key"
          type="button"
          class="chip"
          :class="{ 'chip--active': isPresetActive(p) }"
          @click="setPricePreset(p)"
        >
          {{ p.label }}
        </button>
        <el-checkbox v-model="query.featured" class="filter-featured" @change="applyFilters">只看精选</el-checkbox>
      </div>

      <div class="filter-row">
        <span class="filter-row__label">注册日期</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          unlink-panels
          class="filter-date"
          @change="applyFilters"
        />
      </div>
    </section>

    <!-- 结果 -->
    <div v-loading="loading" class="list-body">
      <div v-if="items.length" class="tm-grid">
        <TrademarkCard v-for="card in items" :key="card.id" :card="card" @click="openDetail(card.id)" />
      </div>

      <div v-else-if="!loading" class="empty-state">
        <h3>没有找到符合条件的商标</h3>
        <p>可以尝试放宽筛选条件，或让客服帮你定向找标。</p>
        <div class="empty-actions">
          <el-button @click="resetFilters">清空筛选条件</el-button>
          <el-button type="primary" :icon="ChatDotRound" @click="contactVisible = true">联系客服帮你找标</el-button>
        </div>
      </div>

      <div v-if="total > pageSize" class="pager">
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, jumper"
          background
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 客服 -->
    <el-dialog v-model="contactVisible" title="联系客服" width="420px">
      <div class="contact-box">
        <p class="contact-wechat">
          客服微信
          <span class="mono-id">{{ config?.service_wechat || '—' }}</span>
          <el-button v-if="config?.service_wechat" link type="primary" :icon="CopyDocument" @click="copyWechat">
            复制
          </el-button>
        </p>
        <img v-if="config?.service_qr" :src="config.service_qr" alt="客服微信二维码" class="contact-qr" />
        <p class="text-muted">{{ config?.service_text }}</p>
        <p class="text-muted">服务时间：{{ config?.service_hours || '—' }}</p>
      </div>
      <template #footer>
        <el-button @click="contactVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { ensureSiteConfig, siteConfig } from './SiteLayout.vue'
</script>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, CopyDocument, RefreshLeft, Search } from '@element-plus/icons-vue'
import { siteApi, type PublicCard } from '@/api'
import TrademarkCard from './components/TrademarkCard.vue'

const route = useRoute()
const router = useRouter()

const pageSize = 24
const SORTS = [
  { value: 'created_at:desc', label: '最新上架' },
  { value: 'price:asc', label: '价格从低到高' },
  { value: 'price:desc', label: '价格从高到低' },
  { value: 'registration_date:desc', label: '注册日期最新' },
  { value: 'application_count:desc', label: '申请量最多' },
]
const PRICE_PRESETS = [
  { key: 'all', label: '不限', min: null as number | null, max: null as number | null },
  { key: 'a', label: '2000 以下', min: null, max: 2000 },
  { key: 'b', label: '2000-5000', min: 2000, max: 5000 },
  { key: 'c', label: '5000-1万', min: 5000, max: 10000 },
  { key: 'd', label: '1万以上', min: 10000, max: null },
]

const loading = ref(false)
const items = ref<PublicCard[]>([])
const total = ref(0)
const page = ref(1)
const sortValue = ref('created_at:desc')
const dateRange = ref<[string, string] | null>(null)
const contactVisible = ref(false)
const config = siteConfig
const facets = reactive({ categories: [] as { value: number; count: number }[] })
const query = reactive({
  q: '',
  category: null as number | null,
  price_min: null as number | null,
  price_max: null as number | null,
  featured: false,
})

let lastSig = ''

function buildQuery(): Record<string, string> {
  const q: Record<string, string> = {}
  if (query.q.trim()) q.q = query.q.trim()
  if (query.category) q.category = String(query.category)
  if (query.price_min !== null) q.price_min = String(query.price_min)
  if (query.price_max !== null) q.price_max = String(query.price_max)
  if (dateRange.value) {
    q.date_from = dateRange.value[0]
    q.date_to = dateRange.value[1]
  }
  if (query.featured) q.featured = '1'
  if (sortValue.value !== 'created_at:desc') q.sort = sortValue.value
  if (page.value > 1) q.page = String(page.value)
  return q
}

function readQuery() {
  const rq = route.query
  query.q = typeof rq.q === 'string' ? rq.q : ''
  query.category = rq.category ? Number(rq.category) : null
  query.price_min = rq.price_min !== undefined && rq.price_min !== '' ? Number(rq.price_min) : null
  query.price_max = rq.price_max !== undefined && rq.price_max !== '' ? Number(rq.price_max) : null
  const df = typeof rq.date_from === 'string' ? rq.date_from : ''
  const dt = typeof rq.date_to === 'string' ? rq.date_to : ''
  dateRange.value = df && dt ? [df, dt] : null
  query.featured = rq.featured === '1'
  const s = typeof rq.sort === 'string' ? rq.sort : ''
  sortValue.value = SORTS.some((x) => x.value === s) ? s : 'created_at:desc'
  page.value = rq.page ? Math.max(1, Number(rq.page) || 1) : 1
}

async function syncAndLoad(resetPage = false) {
  if (resetPage) page.value = 1
  const next = buildQuery()
  const sig = JSON.stringify(next)
  if (sig !== JSON.stringify(route.query)) {
    lastSig = sig
    await router.replace({ query: next })
  }
  await load()
}

async function load() {
  loading.value = true
  try {
    const [sort_by, sort_dir] = sortValue.value.split(':')
    const res = await siteApi.list({
      q: query.q.trim() || undefined,
      category: query.category || undefined,
      price_min: query.price_min ?? undefined,
      price_max: query.price_max ?? undefined,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1],
      featured: query.featured || undefined,
      sort_by,
      sort_dir,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res.items
    total.value = res.total
    facets.categories = res.facets?.categories || []
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  syncAndLoad(true)
}
function onPageChange(p: number) {
  page.value = p
  syncAndLoad(false)
}
function setCategory(value: number | null) {
  query.category = value
  applyFilters()
}
function isPresetActive(p: { min: number | null; max: number | null }) {
  return query.price_min === p.min && query.price_max === p.max
}
function setPricePreset(p: { min: number | null; max: number | null }) {
  query.price_min = p.min
  query.price_max = p.max
  applyFilters()
}
function resetFilters() {
  query.q = ''
  query.category = null
  query.price_min = null
  query.price_max = null
  query.featured = false
  dateRange.value = null
  sortValue.value = 'created_at:desc'
  syncAndLoad(true)
}
function openDetail(id: number) {
  router.push(`/trademark/${id}`)
}
function copyWechat() {
  const wx = config.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

watch(
  () => route.query,
  (nq) => {
    if (JSON.stringify(nq) === lastSig) return
    readQuery()
    load()
  },
)

onMounted(() => {
  readQuery()
  load()
  ensureSiteConfig()
})
</script>

<style scoped>
.filter-search {
  width: 300px;
}
.filter-spacer {
  flex: 1;
}
.filter-sort {
  width: 170px;
}
.filter-date {
  width: 300px;
}
.filter-featured {
  margin-left: var(--space-2);
}
.chip__count {
  color: var(--color-subtle-fg);
  font-size: 11px;
}
.chip {
  font-family: inherit;
}
.chip--active .chip__count {
  color: rgba(255, 255, 255, 0.75);
}
.list-body {
  min-height: 320px;
}
.empty-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  margin-top: var(--space-5);
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: var(--space-8);
}
.contact-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.contact-wechat {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-md);
  margin: 0;
}
.contact-qr {
  width: 160px;
  height: 160px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.contact-box p {
  margin: 0;
}
@media (max-width: 820px) {
  .filter-search,
  .filter-date {
    width: 100%;
  }
  .filter-sort {
    width: 140px;
  }
}
</style>
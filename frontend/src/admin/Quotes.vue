<template>
  <div class="quote-page">
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <el-input
          v-model="q"
          placeholder="按报价单号搜索"
          clearable
          class="filter-search"
          :prefix-icon="Search"
          @keyup.enter="reload(1)"
          @clear="reload(1)"
        />
        <el-button type="primary" :icon="Search" @click="reload(1)">搜索</el-button>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ total }}</b> 份报价单</span>
        <span class="text-subtle">· 点击任意一行可查看明细与合计</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        size="small"
        border
        stripe
        class="clickable-table"
        @row-click="openDetail"
      >
        <el-table-column label="报价单号" width="150">
          <template #default="{ row }"><span class="mono-id">{{ row.quote_no }}</span></template>
        </el-table-column>
        <el-table-column label="标题" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.title || '—' }}</template>
        </el-table-column>
        <el-table-column label="客户名" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.customer_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="联系电话" width="140">
          <template #default="{ row }"><span class="mono-id">{{ row.contact_phone || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="商标数" width="88" align="right">
          <template #default="{ row }"><span class="num">{{ row.item_count }}</span></template>
        </el-table-column>
        <el-table-column label="原价合计" width="120" align="right">
          <template #default="{ row }"><span class="num">¥{{ money(row.total_original) }}</span></template>
        </el-table-column>
        <el-table-column label="报价合计" width="120" align="right">
          <template #default="{ row }"><span class="num price">¥{{ money(row.total_quote) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="访问次数" width="96" align="right">
          <template #default="{ row }"><span class="num">{{ row.view_count }}</span></template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="150">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="有效期至" width="120">
          <template #default="{ row }">{{ row.expire_at || '长期有效' }}</template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="copyLink(row)">复制链接</el-button>
            <el-button
              v-if="row.status !== 'cancelled'"
              link
              type="danger"
              size="small"
              @click.stop="cancel(row)"
            >
              作废
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="load"
          @size-change="reload(1)"
        />
      </div>
    </el-card>

    <!-- 明细抽屉 -->
    <el-drawer v-model="drawer" :title="current?.quote_no || '报价单明细'" size="720px">
      <div v-if="current" class="detail">
        <el-descriptions :column="2" border size="small" class="detail__meta">
          <el-descriptions-item label="标题">{{ current.title || '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(current.status)" size="small" effect="light">{{ statusLabel(current.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="客户名">{{ current.customer_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ current.contact_phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ current.created_at || '—' }}</el-descriptions-item>
          <el-descriptions-item label="有效期至">{{ current.expire_at || '长期有效' }}</el-descriptions-item>
          <el-descriptions-item label="访问次数"><span class="num">{{ current.view_count }}</span></el-descriptions-item>
          <el-descriptions-item label="访问密码">{{ current.has_password ? '已设置' : '无' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ current.remark || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">商标明细（{{ current.items?.length || 0 }} 项）</el-divider>
        <el-table :data="current.items || []" size="small" border>
          <el-table-column label="图样" width="70">
            <template #default="{ row }">
              <el-image v-if="row.image" :src="row.image" :preview-src-list="[row.image]" preview-teleported fit="cover" class="thumb" />
              <span v-else class="text-subtle">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="商标名" min-width="140" show-overflow-tooltip />
          <el-table-column label="类别" width="80">
            <template #default="{ row }"><span class="num">{{ row.category ? `${row.category}类` : '—' }}</span></template>
          </el-table-column>
          <el-table-column label="商标编号" width="160">
            <template #default="{ row }"><span class="mono-id">{{ row.trademark_no || '—' }}</span></template>
          </el-table-column>
          <el-table-column label="原价" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ row.original_price === null ? '面议' : `¥${money(row.original_price)}` }}</span></template>
          </el-table-column>
          <el-table-column label="报价" width="100" align="right">
            <template #default="{ row }"><span class="num price">{{ row.quote_price === null ? '面议' : `¥${money(row.quote_price)}` }}</span></template>
          </el-table-column>
        </el-table>

        <div class="detail__total">
          <span>原价合计 <b class="num">¥{{ money(current.total_original) }}</b></span>
          <span>报价合计 <b class="num price">¥{{ money(current.total_quote) }}</b></span>
        </div>

        <div class="detail__foot">
          <el-button :icon="Link" @click="copyLink(current)">复制分享链接</el-button>
          <el-button
            v-if="current.status !== 'cancelled'"
            type="danger"
            :icon="CircleClose"
            @click="cancel(current)"
          >
            作废报价单
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleClose, Link, Refresh, Search } from '@element-plus/icons-vue'
import { adminApi, type Quote } from '@/api'

const STATUS_LABEL: Record<string, string> = { active: '有效', expired: '过期', cancelled: '已作废' }
const STATUS_TYPE: Record<string, 'success' | 'info' | 'danger'> = {
  active: 'success', expired: 'info', cancelled: 'danger',
}

const loading = ref(false)
const rows = ref<Quote[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const q = ref('')
const drawer = ref(false)
const current = ref<Quote | null>(null)

function statusLabel(s: string) {
  return STATUS_LABEL[s] || s
}
function statusType(s: string) {
  return STATUS_TYPE[s] || 'info'
}
function money(v: unknown) {
  return Number(v || 0).toLocaleString()
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.quotes({ page: page.value, page_size: pageSize.value, q: q.value || undefined })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}
function reload(p = page.value) {
  page.value = p
  load()
}

function shareUrl(token: string) {
  return `${location.origin}/quote/${token}`
}
function copyLink(row: Quote) {
  const url = shareUrl(row.token)
  navigator.clipboard?.writeText(url)
  ElMessage.success(`已复制分享链接：${url}`)
}
function openDetail(row: Quote) {
  current.value = row
  drawer.value = true
}

async function cancel(row: Quote) {
  try {
    await ElMessageBox.confirm(
      `作废后「${row.quote_no}」的分享链接立即失效，客户无法再打开。确定作废吗？`,
      '作废确认',
      { type: 'warning', confirmButtonText: '确认作废', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  await adminApi.cancelQuote(row.id)
  ElMessage.success('报价单已作废')
  if (current.value?.id === row.id) current.value.status = 'cancelled'
  load()
}

onMounted(load)
</script>

<style scoped>
.quote-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.filter-search {
  width: 260px;
}
.filter-spacer {
  flex: 1;
}
.table-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.clickable-table :deep(.el-table__row) {
  cursor: pointer;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
}
.price {
  font-weight: 600;
  color: var(--color-primary);
}
.thumb {
  width: 46px;
  height: 46px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.detail__meta {
  margin-bottom: var(--space-2);
}
.detail__total {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-8);
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: var(--color-accent-050);
  border: 1px solid var(--color-accent-100);
  border-radius: var(--radius);
  font-size: var(--text-base);
}
.detail__total b {
  font-size: var(--text-lg);
  margin-left: var(--space-2);
}
.detail__foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-5);
}
</style>
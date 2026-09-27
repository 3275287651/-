<template>
  <div class="expire-page">
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <span class="filter-label">提醒范围</span>
        <el-radio-group v-model="days" @change="load">
          <el-radio-button :value="30">30 天内</el-radio-button>
          <el-radio-button :value="90">90 天内</el-radio-button>
          <el-radio-button :value="180">180 天内</el-radio-button>
          <el-radio-button :value="365">365 天内</el-radio-button>
        </el-radio-group>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
      <p class="filter-tip text-subtle">
        列出有效期至在未来 {{ days }} 天内（含已过期）的商标，按到期时间从早到晚排序，最多显示 300 条。
      </p>
    </el-card>

    <transition name="el-fade-in">
      <div v-if="selection.length" class="batch-bar">
        <div class="batch-bar__info">
          <el-icon><Select /></el-icon>
          已选 <b>{{ selection.length }}</b> 项
          <el-button link type="primary" @click="tableRef?.clearSelection()">清空</el-button>
        </div>
        <div class="batch-bar__actions">
          <el-button size="small" type="danger" :icon="Sell" @click="batchStatus('sold')">标记为已售出</el-button>
          <el-button size="small" type="warning" :icon="Clock" @click="batchStatus('reserved')">标记为预留中</el-button>
          <el-button size="small" :icon="Bottom" @click="batchStatus('off_shelf')">下架</el-button>
        </div>
      </div>
    </transition>

    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ rows.length }}</b> 个商标即将到期</span>
        <span class="text-subtle">· 点击商标名可进入编辑页续展或调整信息</span>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="rows"
        size="small"
        border
        stripe
        row-key="id"
        @selection-change="(v: Row[]) => (selection = v)"
      >
        <el-table-column type="selection" width="42" fixed />
        <el-table-column label="唯一编号" width="180">
          <template #default="{ row }">
            <span class="id-badge id-badge--serial">唯一</span>
            <span class="mono-id">{{ row.serial_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="商标编号" width="180">
          <template #default="{ row }"><span class="mono-id">{{ row.trademark_no || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="商标名" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" underline="never" @click="$router.push(`/admin/trademarks/${row.id}/edit`)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="80">
          <template #default="{ row }"><span class="num">{{ row.category ? `${row.category}类` : '—' }}</span></template>
        </el-table-column>
        <el-table-column label="有效期至" width="120">
          <template #default="{ row }"><span class="num">{{ row.expiry_date }}</span></template>
        </el-table-column>
        <el-table-column label="剩余天数" width="130">
          <template #default="{ row }">
            <span v-if="row.days_left < 0" class="left left--expired">
              <el-icon><CircleCloseFilled /></el-icon>已过期 {{ Math.abs(row.days_left) }} 天
            </span>
            <span v-else-if="row.days_left <= 30" class="left left--soon">仅剩 {{ row.days_left }} 天</span>
            <span v-else class="left num">剩 {{ row.days_left }} 天</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">{{ STATUS_LABEL[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !rows.length" description="该时间范围内没有即将到期的商标" :image-size="80" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Bottom, CircleCloseFilled, Clock, Refresh, Select, Sell,
} from '@element-plus/icons-vue'
import { adminApi, adminTrademarkApi } from '@/api'

interface Row {
  id: number
  serial_no: string
  trademark_no: string | null
  name: string
  category: number | null
  expiry_date: string
  days_left: number
  status: string
}

const STATUS_LABEL: Record<string, string> = {
  on_sale: '在售', off_shelf: '已下架', sold: '已售出', reserved: '预留中',
}

const loading = ref(false)
const rows = ref<Row[]>([])
const days = ref(90)
const selection = ref<Row[]>([])
const tableRef = ref()

function statusType(s: string) {
  return ({ on_sale: 'success', off_shelf: 'info', sold: 'danger', reserved: 'warning' } as const)[s] || 'info'
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.expiring(days.value)
    rows.value = res.items as Row[]
    tableRef.value?.clearSelection()
  } finally {
    loading.value = false
  }
}

async function batchStatus(status: 'sold' | 'reserved' | 'off_shelf') {
  const ids = selection.value.map((r) => r.id)
  if (!ids.length) return
  const action = status === 'off_shelf' ? 'off_shelf' : 'set_status'
  const res = await adminTrademarkApi.batch(
    action === 'set_status' ? { action, ids, status } : { action, ids },
  )
  const label = status === 'sold' ? '已售出' : status === 'reserved' ? '预留中' : '已下架'
  ElMessage.success(`已将 ${res.affected} 个商标标记为「${label}」`)
  load()
}

onMounted(load)
</script>

<style scoped>
.expire-page {
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
.filter-label {
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.filter-spacer {
  flex: 1;
}
.filter-tip {
  margin: var(--space-3) 0 0;
  font-size: var(--text-xs);
}
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: var(--color-accent-050);
  border: 1px solid var(--color-accent-100);
  border-radius: var(--radius-lg);
}
.batch-bar__info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-accent-600);
  font-size: var(--text-base);
}
.batch-bar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.table-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.left {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
}
.left--expired {
  color: var(--color-destructive);
  font-weight: 600;
}
.left--soon {
  color: var(--color-warning);
  font-weight: 600;
}
</style>
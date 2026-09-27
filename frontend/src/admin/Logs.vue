<template>
  <div class="log-page">
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <span class="filter-label">操作类型</span>
        <el-select v-model="action" placeholder="全部类型" clearable class="filter-select" @change="reload(1)">
          <el-option v-for="o in ACTION_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="reload(1)">查询</el-button>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ total }}</b> 条操作记录</span>
        <span class="text-subtle">· 记录最近的操作，仅超级管理员可见</span>
      </div>

      <el-table v-loading="loading" :data="rows" size="small" border stripe>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }"><span class="num">{{ row.created_at || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="操作人" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.admin_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作类型" width="150">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目标" width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.target_type" class="target">
              {{ TARGET_LABEL[row.target_type] || row.target_type }}
              <span v-if="row.target_id" class="num">#{{ row.target_id }}</span>
            </span>
            <span v-else class="text-subtle">—</span>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="320">
          <template #default="{ row }">
            <div v-if="row._detail" class="detail">
              <span v-for="(v, k) in row._detail" :key="k" class="detail__item">
                <b>{{ DETAIL_LABEL[k] || k }}</b>{{ detailVal(v) }}
              </span>
            </div>
            <span v-else-if="row.detail" class="raw">{{ row.detail }}</span>
            <span v-else class="text-subtle">—</span>
          </template>
        </el-table-column>
        <el-table-column label="IP" width="140">
          <template #default="{ row }"><span class="mono-id">{{ row.ip || '—' }}</span></template>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const ACTION_LABEL: Record<string, string> = {
  trademark_create: '新增商标',
  trademark_update: '编辑商标',
  trademark_delete: '删除商标',
  import_commit: '执行导入',
  trademark_export: '导出',
  settings_update: '修改配置',
  customer_update: '修改客户',
  admin_create: '新增账户',
  admin_update: '编辑账户',
  admin_delete: '删除账户',
}
const ACTION_OPTIONS = [
  { value: 'trademark_create', label: '新增商标' },
  { value: 'trademark_update', label: '编辑商标' },
  { value: 'trademark_delete', label: '删除商标' },
  { value: 'batch', label: '批量操作' },
  { value: 'import_commit', label: '执行导入' },
  { value: 'trademark_export', label: '导出' },
  { value: 'settings_update', label: '修改配置' },
]
const TARGET_LABEL: Record<string, string> = {
  trademark: '商标',
  settings: '站点配置',
  import: '导入批次',
  customer: '客户',
  admin: '运营账户',
  quote: '报价单',
}
const DETAIL_LABEL: Record<string, string> = {
  serial_no: '唯一编号',
  name: '商标名',
  ids: 'ID 列表',
  count: '数量',
  status: '状态',
  price: '金额',
  featured: '精选',
  category: '类别',
  adjust_mode: '调价方式',
  adjust_value: '调价数值',
  skipped_unpriced: '跳过未定价',
  keys: '配置项',
  batch_id: '批次ID',
  filename: '文件名',
  rows: '数据行',
}

const loading = ref(false)
const rows = ref<Record<string, any>[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const action = ref<string>('')

function actionLabel(a: string) {
  if (!a) return '—'
  if (a.startsWith('batch_')) return '批量操作'
  return ACTION_LABEL[a] || a
}
function parseDetail(raw: unknown): Record<string, any> | null {
  if (!raw || typeof raw !== 'string') return null
  try {
    const obj = JSON.parse(raw)
    if (obj && typeof obj === 'object' && !Array.isArray(obj)) return obj
    return null
  } catch {
    return null
  }
}
function detailVal(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (Array.isArray(v)) return v.join('、')
  if (typeof v === 'object') return JSON.stringify(v)
  if (typeof v === 'boolean') return v ? '是' : '否'
  return String(v)
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.logs({
      page: page.value,
      page_size: pageSize.value,
      action: action.value || undefined,
    })
    rows.value = (res.items as Record<string, any>[]).map((r) => ({ ...r, _detail: parseDetail(r.detail) }))
    total.value = res.total
  } finally {
    loading.value = false
  }
}
function reload(p = page.value) {
  page.value = p
  load()
}

onMounted(load)
</script>

<style scoped>
.log-page {
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
.filter-select {
  width: 180px;
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
.target .num {
  color: var(--color-subtle-fg);
  margin-left: 2px;
}
.detail {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
}
.detail__item {
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.detail__item b {
  color: var(--color-fg);
  margin-right: 4px;
}
.raw {
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
  word-break: break-all;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
}
</style>
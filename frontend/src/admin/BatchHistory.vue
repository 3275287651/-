<template>
  <div class="batch-page">
    <el-card shadow="never" class="panel">
      <div class="toolbar">
        <div>
          <h3>导入批次记录</h3>
          <p class="text-subtle">每次执行导入都会生成一条批次，可查看列结构、失败明细，也可回退删除。</p>
        </div>
        <div class="toolbar__actions">
          <el-button :icon="Refresh" @click="load">刷新</el-button>
          <el-button type="primary" :icon="Upload" @click="$router.push('/admin/trademarks/import')">去批量导入</el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="panel">
      <el-table v-loading="loading" :data="rows" size="small" border stripe row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand">
              <div class="expand__head">
                <b>列结构（{{ row.columns?.length || 0 }} 列）</b>
                <el-button
                  v-if="row.errors?.length"
                  size="small"
                  :icon="Download"
                  @click="downloadErrors(row)"
                >
                  下载失败明细 CSV（{{ row.errors.length }} 条）
                </el-button>
              </div>
              <el-table :data="row.columns || []" size="small" border max-height="240" class="expand__table">
                <el-table-column prop="header" label="Excel 列名" min-width="150" show-overflow-tooltip />
                <el-table-column label="映射字段" width="150">
                  <template #default="{ row: c }">
                    <el-tag v-if="c.mapped_field === 'image'" size="small" type="success" effect="plain">图片列</el-tag>
                    <el-tag v-else-if="c.mapped_field === 'extra'" size="small" type="warning" effect="plain">自定义列</el-tag>
                    <span v-else-if="c.mapped_field">{{ c.mapped_field }}</span>
                    <span v-else class="text-subtle">未映射</span>
                  </template>
                </el-table-column>
                <el-table-column prop="data_type" label="类型" width="90" />
                <el-table-column label="非空/总行" width="110" align="right">
                  <template #default="{ row: c }"><span class="num">{{ c.non_empty }} / {{ row.total_rows }}</span></template>
                </el-table-column>
                <el-table-column label="样例" min-width="220">
                  <template #default="{ row: c }">
                    <span v-if="c.samples?.length" class="text-subtle">{{ c.samples.join(' · ') }}</span>
                    <span v-else class="text-subtle">—</span>
                  </template>
                </el-table-column>
              </el-table>

              <template v-if="row.errors?.length">
                <div class="expand__head expand__head--errors">
                  <b>跳过 / 失败明细（{{ row.errors.length }} 条）</b>
                </div>
                <el-table :data="row.errors" size="small" border max-height="220" class="expand__table">
                  <el-table-column prop="row" label="源表行" width="100" align="center" />
                  <el-table-column prop="reason" label="原因" min-width="260" show-overflow-tooltip />
                </el-table>
              </template>
              <el-empty v-else-if="!row.errors?.length" description="该批次没有任何失败或跳过的记录" :image-size="56" />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="sheet_name" label="工作表" width="150" show-overflow-tooltip />
        <el-table-column label="数据行" width="90" align="right">
          <template #default="{ row }"><span class="num">{{ row.total_rows }}</span></template>
        </el-table-column>
        <el-table-column label="图片数" width="90" align="right">
          <template #default="{ row }"><span class="num">{{ row.image_count }}</span></template>
        </el-table-column>
        <el-table-column label="识别列数" width="100" align="right">
          <template #default="{ row }"><span class="num">{{ row.column_count }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="140">
          <template #default="{ row }">
            <el-progress
              :percentage="progressOf(row)"
              :status="row.status === 'failed' ? 'exception' : row.status === 'done' ? 'success' : undefined"
              :stroke-width="10"
              :show-text="false"
            />
            <span class="num progress-text">{{ progressOf(row) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="新增 / 更新 / 跳过 / 失败" width="180" align="center">
          <template #default="{ row }">
            <span class="num stat stat--ok">{{ row.success_count }}</span> /
            <span class="num stat">{{ row.updated_count }}</span> /
            <span class="num stat">{{ row.skipped_count }}</span> /
            <span class="num stat stat--bad">{{ row.failed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150" show-overflow-tooltip />
        <el-table-column prop="finished_at" label="完成时间" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.finished_at || '—' }}</template>
        </el-table-column>

        <el-table-column label="操作" width="210" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/admin/trademarks?batch_id=${row.id}`)">
              查看该批商标
            </el-button>
            <el-button link type="danger" size="small" @click="openDelete(row)">删除批次</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 删除批次 -->
    <el-dialog v-model="deleteDialog" title="删除导入批次" width="480px" append-to-body>
      <p class="dialog-text">
        批次：<b>{{ current?.filename }}</b>（源表 {{ current?.total_rows }} 行）
      </p>
      <el-alert type="info" :closable="false" class="dialog-alert">
        仅删除批次记录不会影响已导入的商标数据；删除商标数据不可恢复。
      </el-alert>
      <p class="dialog-text">
        当前仍关联到该批次的商标：
        <b class="num">{{ linkedCount < 0 ? '统计中…' : linkedCount }}</b> 条
        <span v-if="linkedCount === 0" class="text-subtle">
          （该批商标已不在库中，或已被其它操作解除批次关联，无需再删除数据）
        </span>
      </p>
      <template #footer>
        <el-button @click="deleteDialog = false">取消</el-button>
        <el-button @click="doDelete(false)">仅删除批次记录</el-button>
        <el-button type="danger" :disabled="linkedCount <= 0" @click="doDelete(true)">
          同时删除该批 {{ linkedCount > 0 ? linkedCount : '' }} 条商标数据
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Refresh, Upload } from '@element-plus/icons-vue'
import { adminImportApi, adminTrademarkApi, type ImportBatch } from '@/api'

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中', running: '进行中', analyzing: '分析中', done: '已完成', failed: '失败',
}
const STATUS_TYPE: Record<string, 'success' | 'info' | 'warning' | 'danger' | 'primary'> = {
  pending: 'info', running: 'primary', analyzing: 'warning', done: 'success', failed: 'danger',
}

const loading = ref(false)
const rows = ref<ImportBatch[]>([])
const deleteDialog = ref(false)
const current = ref<ImportBatch | null>(null)
/** 当前仍关联到该批次的商标数；-1 表示统计中。批次历史计数（新增/更新）会随时间失真，必须以库中实际关联为准 */
const linkedCount = ref(-1)

function statusLabel(s: string) {
  return STATUS_LABEL[s] || s
}
function statusType(s: string) {
  return STATUS_TYPE[s] || 'info'
}
function progressOf(row: ImportBatch) {
  if (row.status === 'done') return 100
  return Math.max(0, Math.min(100, Math.round(row.progress || 0)))
}

async function load() {
  loading.value = true
  try {
    const res = await adminImportApi.history()
    rows.value = res.items
  } finally {
    loading.value = false
  }
}

function downloadErrors(batch: ImportBatch) {
  const list = [['源表行', '原因'], ...(batch.errors || []).map((e) => [e.row, e.reason])]
  const csv = '\uFEFF' + list
    .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `导入失败明细_${batch.filename || batch.id}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

async function openDelete(row: ImportBatch) {
  current.value = row
  deleteDialog.value = true
  linkedCount.value = -1
  try {
    // 以库中实际关联数为准，避免拿批次历史计数当删除依据（历史计数会因后续更新而失真）
    const res = await adminTrademarkApi.list({ batch_id: row.id, page_size: 1 })
    linkedCount.value = res.total
  } catch {
    linkedCount.value = -1
  }
}

async function doDelete(purge: boolean) {
  const batch = current.value
  if (!batch || linkedCount.value < 0) return
  if (purge) {
    try {
      await ElMessageBox.confirm(
        `将同时删除仍关联到该批次的 ${linkedCount.value} 条商标数据（含图样），且不可恢复。确认继续吗？`,
        '危险操作二次确认',
        { type: 'error', confirmButtonText: '确认删除商标数据', confirmButtonClass: 'el-button--danger' },
      )
    } catch {
      return
    }
  }
  try {
    await adminImportApi.remove(batch.id, purge)
    ElMessage.success(purge ? `批次与 ${linkedCount.value} 条商标数据已删除` : '批次记录已删除')
    deleteDialog.value = false
    load()
  } catch {
    // 错误提示由请求拦截器统一给出；失败时保留弹窗，便于重试
  }
}

onMounted(load)
</script>

<style scoped>
.batch-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.toolbar h3 {
  margin: 0 0 4px;
  font-size: var(--text-md);
}
.toolbar p {
  margin: 0;
  font-size: var(--text-xs);
}
.toolbar__actions {
  display: flex;
  gap: var(--space-2);
}
.expand {
  padding: var(--space-3) var(--space-5);
  background: var(--color-bg);
}
.expand__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
}
.expand__head--errors {
  margin-top: var(--space-4);
}
.expand__table {
  margin-bottom: var(--space-2);
}
.progress-text {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-subtle-fg);
  text-align: center;
}
.stat {
  font-weight: 600;
}
.stat--ok {
  color: var(--color-success);
}
.stat--bad {
  color: var(--color-destructive);
}
.dialog-text {
  margin: 0 0 var(--space-3);
  font-size: var(--text-base);
}
.dialog-alert {
  margin-bottom: 0;
}
@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
  }
}
</style>
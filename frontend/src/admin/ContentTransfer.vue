<template>
  <div class="content-page">
    <el-alert type="info" :closable="false" class="intro">
      <template #title>内容与镜像分开迁移</template>
      <p class="intro__text">
        本页负责「内容」——数据库业务数据与上传的图样 / 商标证 / Logo / 轮播图等文件。
        它与 Docker 镜像升级互不影响：换服务器或换镜像时，先用内容包导出，在新实例上原样导入即可完成内容搬迁。
      </p>
    </el-alert>

    <!-- A. 导出内容包 -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>导出内容包</h3>
          <p class="text-subtle">打包当前实例的全部业务数据与上传文件，生成一个 ZIP 内容包。</p>
        </div>
        <el-button :icon="Refresh" @click="loadSummary">刷新概览</el-button>
      </div>

      <div v-loading="loadingSummary" class="overview">
        <el-descriptions :column="3" border size="small" class="tables">
          <el-descriptions-item v-for="t in countRows" :key="t.key" :label="t.label">
            <span class="num">{{ n(t.value) }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="upload-stat">
          <div class="upload-stat__item">
            <div class="upload-stat__label">上传文件</div>
            <div class="upload-stat__value num">{{ n(uploads?.files) }} 个</div>
          </div>
          <div class="upload-stat__item">
            <div class="upload-stat__label">文件体积</div>
            <div class="upload-stat__value num">{{ uploads?.megabytes ?? 0 }} MB</div>
          </div>
          <div class="upload-stat__item">
            <div class="upload-stat__label">内容包格式版本</div>
            <div class="upload-stat__value num">v{{ formatVersion }}</div>
          </div>
        </div>
      </div>

      <el-alert type="warning" :closable="false" class="excluded">
        <template #title>内容包不包含以下内容（迁移时各自独立处理）</template>
        <ul class="excluded__list">
          <li v-for="(t, i) in excludedTables" :key="i"><b>{{ t }}</b> 不进入内容包，避免导入后覆盖新实例的登录凭据 / 审计记录。</li>
          <li v-if="excludedPaths.length">
            <b>{{ excludedPaths.join('、') }}</b> 为导入解析的中间产物，未完成的导入批次不随内容包迁移。
          </li>
        </ul>
      </el-alert>

      <div class="actions">
        <el-button type="primary" size="large" :icon="Download" :loading="exporting" @click="doExport">
          导出内容包
        </el-button>
        <span class="text-subtle">导出的是完整内容快照，可在另一个实例上用下方「导入」原样恢复。</span>
      </div>
    </el-card>

    <!-- B. 导入内容包 -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>
            导入内容包
            <el-tag size="small" type="danger" effect="plain">危险操作</el-tag>
          </h3>
          <p class="text-subtle">用一个内容包整体替换当前实例的业务数据，实现内容搬迁或回滚到某个快照。</p>
        </div>
      </div>

      <el-alert type="error" :closable="false" class="danger-note">
        <template #title>导入会清空并整体替换当前全部业务数据</template>
        <p class="danger-note__text">
          包含商标、客户、报价单、站点配置等在内的业务数据将被<strong>全部清空并替换为内容包中的数据，且不可恢复</strong>。
          运营账户与操作日志不受影响，导入端仍沿用自身账户登录。
        </p>
      </el-alert>

      <el-upload
        drag
        action="#"
        :auto-upload="false"
        :show-file-list="false"
        :limit="1"
        accept=".zip"
        :on-change="onFileChange"
        class="uploader"
      >
        <el-icon class="uploader__icon"><UploadFilled /></el-icon>
        <div class="uploader__title">把内容包 ZIP 拖到这里，或点击选择文件</div>
        <div class="uploader__sub">仅支持由本系统「导出内容包」生成的 .zip 文件</div>
      </el-upload>

      <div v-if="file" class="file-chip">
        <el-icon><Document /></el-icon>
        <span class="file-chip__name">{{ file.name }}</span>
        <span class="num text-subtle">{{ fileSizeText }}</span>
        <el-button link type="danger" @click="clearFile">移除</el-button>
      </div>

      <el-checkbox v-model="includeUploads" class="include-uploads">
        同时恢复上传文件（图样、商标证、Logo 等）
      </el-checkbox>

      <div class="actions">
        <el-button
          type="danger"
          size="large"
          :icon="Upload"
          :disabled="!file"
          :loading="importing"
          @click="doImport"
        >
          {{ importing ? '正在导入，请勿关闭页面…' : '导入内容包' }}
        </el-button>
        <span class="text-subtle">导入过程可能需要十几秒，请耐心等待。</span>
      </div>

      <el-alert v-if="importError" type="error" :closable="false" class="result-alert">
        <template #title>导入失败，数据未变更</template>
        <p class="result-alert__text">{{ importError }}</p>
        <p class="result-alert__text text-subtle">后端已保证失败回滚，当前数据保持不变，可修正内容包后重试。</p>
      </el-alert>

      <template v-if="result">
        <el-divider content-position="left">导入结果</el-divider>
        <div class="result-summary">
          <span class="result-summary__ok">
            <el-icon><CircleCheckFilled /></el-icon>
            {{ result.message }}
          </span>
        </div>

        <el-descriptions :column="2" border size="small" class="result-meta">
          <el-descriptions-item label="来源站点">{{ result.source?.site || '—' }}</el-descriptions-item>
          <el-descriptions-item label="导出时间">{{ result.source?.exported_at || '—' }}</el-descriptions-item>
          <el-descriptions-item label="恢复文件">{{ n(result.upload_files) }} 个</el-descriptions-item>
          <el-descriptions-item label="恢复表数量">{{ resultTableRows.length }} 张</el-descriptions-item>
        </el-descriptions>

        <el-table :data="resultTableRows" size="small" border stripe class="result-table">
          <el-table-column label="数据表" min-width="180">
            <template #default="{ row }">{{ row.label }}</template>
          </el-table-column>
          <el-table-column prop="key" label="表名" min-width="180" show-overflow-tooltip />
          <el-table-column label="恢复行数" width="140" align="right">
            <template #default="{ row }"><span class="num">{{ n(row.value) }}</span></template>
          </el-table-column>
        </el-table>

        <el-alert type="info" :closable="false" class="result-alert">
          导入已完成。如浏览器仍显示旧内容，请按 Ctrl+F5 强制刷新一次。
        </el-alert>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCheckFilled, Document, Download, Refresh, Upload, UploadFilled,
} from '@element-plus/icons-vue'
import { adminContentApi } from '@/api'

/** 英文表名 → 中文名 */
const TABLE_LABEL: Record<string, string> = {
  trademarks: '商标',
  trademark_images: '图样附件',
  import_batches: '导入批次',
  users: '客户',
  quotes: '报价单',
  quote_items: '报价单明细',
  favorites: '收藏',
  site_settings: '站点配置',
  banners: '轮播图',
  trademark_columns: '列定义',
  notifications: '通知',
  visit_logs: '访问日志',
  admins: '运营账户',
  operation_logs: '操作日志',
}
/** 导出概览里按固定顺序展示的表 */
const TABLE_ORDER = [
  'trademarks', 'trademark_images', 'import_batches', 'users', 'quotes',
  'quote_items', 'favorites', 'site_settings', 'banners', 'trademark_columns',
  'notifications', 'visit_logs',
]

const loadingSummary = ref(false)
const exporting = ref(false)
const importing = ref(false)
const counts = ref<Record<string, number>>({})
const uploads = ref<{ files: number; bytes: number; megabytes: number } | null>(null)
const formatVersion = ref(1)
const excludedTablesRaw = ref<string[]>([])
const excludedPaths = ref<string[]>([])

const file = ref<File | null>(null)
const includeUploads = ref(true)
const importError = ref('')
const result = ref<{
  tables: Record<string, number>
  upload_files: number
  source?: { site?: string; exported_at?: string }
  message: string
} | null>(null)

const countRows = computed(() => {
  const keys = Object.keys(counts.value || {})
  const ordered = [
    ...TABLE_ORDER.filter((k) => keys.includes(k)),
    ...keys.filter((k) => !TABLE_ORDER.includes(k)),
  ]
  return ordered.map((k) => ({ key: k, label: TABLE_LABEL[k] || k, value: counts.value[k] || 0 }))
})
const excludedTables = computed(() =>
  excludedTablesRaw.value.map((t) => TABLE_LABEL[t] || t),
)
const resultTableRows = computed(() => {
  const tables = result.value?.tables || {}
  const keys = Object.keys(tables)
  const ordered = [
    ...TABLE_ORDER.filter((k) => keys.includes(k)),
    ...keys.filter((k) => !TABLE_ORDER.includes(k)),
  ]
  return ordered.map((k) => ({ key: k, label: TABLE_LABEL[k] || k, value: tables[k] || 0 }))
})
const fileSizeText = computed(() => {
  if (!file.value) return ''
  const mb = file.value.size / 1024 / 1024
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${(file.value.size / 1024).toFixed(1)} KB`
})

function n(v: unknown) {
  return Number(v || 0).toLocaleString()
}

async function loadSummary() {
  loadingSummary.value = true
  try {
    const res = await adminContentApi.summary()
    counts.value = res.counts || {}
    uploads.value = res.uploads
    formatVersion.value = res.format_version
    excludedTablesRaw.value = res.excluded?.tables || []
    excludedPaths.value = res.excluded?.paths || []
  } finally {
    loadingSummary.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    await adminContentApi.exportZip()
    ElMessage.success('内容包导出已开始，请查看浏览器下载')
  } catch {
    /* 错误提示由拦截器统一给出 */
  } finally {
    exporting.value = false
  }
}

function onFileChange(f: { raw?: File }) {
  if (!f.raw) return
  if (!f.raw.name.toLowerCase().endsWith('.zip')) {
    ElMessage.warning('请选择 .zip 内容包')
    return
  }
  file.value = f.raw
  importError.value = ''
  result.value = null
}
function clearFile() {
  file.value = null
  importError.value = ''
  result.value = null
}

async function doImport() {
  if (!file.value) return
  try {
    await ElMessageBox.confirm(
      '导入将【清空并整体替换】当前全部业务数据（商标、客户、报价单、站点配置等），且不可恢复；运营账户与操作日志不受影响。确定继续吗？',
      '危险操作二次确认',
      { type: 'error', confirmButtonText: '确认导入并替换数据', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  importing.value = true
  importError.value = ''
  result.value = null
  try {
    const res = await adminContentApi.importZip(file.value, includeUploads.value)
    result.value = res
    ElMessage.success('内容包导入完成')
    loadSummary()
  } catch (err: any) {
    importError.value = err?.response?.data?.detail || err?.message || '导入失败，请查看后端日志'
  } finally {
    importing.value = false
  }
}

onMounted(loadSummary)
</script>

<style scoped>
.content-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.intro__text {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  line-height: 1.8;
}
.sec-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.sec-head h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 4px;
  font-size: var(--text-md);
}
.sec-head p {
  margin: 0;
  font-size: var(--text-xs);
}
.overview {
  margin-bottom: var(--space-4);
}
.tables {
  margin-bottom: var(--space-4);
}
.upload-stat {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
.upload-stat__item {
  padding: var(--space-3) var(--space-4);
  background: var(--color-accent-050);
  border: 1px solid var(--color-accent-100);
  border-radius: var(--radius);
}
.upload-stat__label {
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.upload-stat__value {
  margin-top: 4px;
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
}
.excluded {
  margin-bottom: var(--space-4);
}
.excluded__list {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-5);
  font-size: var(--text-sm);
  line-height: 1.9;
}
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}
.uploader {
  width: 100%;
}
.uploader :deep(.el-upload-dragger) {
  padding: var(--space-8) var(--space-6);
  border: 1.5px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: #fff;
  transition: var(--transition);
}
.uploader :deep(.el-upload-dragger:hover) {
  border-color: var(--color-accent);
  background: var(--color-accent-050);
}
.uploader__icon {
  font-size: 42px;
  color: var(--color-accent);
}
.uploader__title {
  margin-top: var(--space-3);
  font-size: var(--text-md);
  font-weight: 600;
}
.uploader__sub {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
.file-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-2) var(--space-4);
  background: var(--color-muted);
  border-radius: var(--radius);
  font-size: var(--text-sm);
}
.file-chip__name {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.include-uploads {
  display: block;
  margin: var(--space-4) 0;
}
.danger-note {
  margin-bottom: var(--space-4);
}
.danger-note__text,
.result-alert__text {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  line-height: 1.8;
}
.result-alert {
  margin-top: var(--space-4);
}
.result-summary {
  margin-bottom: var(--space-3);
}
.result-summary__ok {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-success);
  font-weight: 600;
}
.result-meta {
  margin-bottom: var(--space-4);
}
.result-table {
  margin-bottom: var(--space-4);
}
@media (max-width: 900px) {
  .upload-stat {
    grid-template-columns: 1fr;
  }
}
</style>
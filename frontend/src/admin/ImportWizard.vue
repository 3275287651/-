<template>
  <div class="import-page">
    <el-card shadow="never" class="panel">
      <el-steps :active="step" align-center finish-status="success" class="steps">
        <el-step title="上传文件" description="支持 .xlsx / .csv，可多选" />
        <el-step title="列映射与预览" description="自动识别，可手动调整" />
        <el-step title="导入设置与执行" description="金额、状态、去重策略" />
      </el-steps>
    </el-card>

    <!-- ─────────── 步骤一：上传 ─────────── -->
    <el-card v-if="step === 0" shadow="never" class="panel">
      <el-upload
        drag
        multiple
        action="#"
        :auto-upload="false"
        :show-file-list="false"
        accept=".xlsx,.xlsm,.csv"
        :on-change="onFileChange"
        class="uploader"
      >
        <el-icon class="uploader__icon"><UploadFilled /></el-icon>
        <div class="uploader__title">把 Excel 拖到这里，或点击选择文件</div>
        <div class="uploader__sub">
          支持一次选择多个文件 · 单文件最大 {{ 100 }}MB · 系统会读取表头、按行提取「图样」列中的图片
        </div>
      </el-upload>

      <div class="upload-actions">
        <el-button :icon="Download" @click="downloadTemplate">下载标准导入模板</el-button>
        <el-button link @click="$router.push('/admin/trademarks/batches')">查看历史导入批次 →</el-button>
      </div>

      <el-alert type="info" :closable="false" class="tips">
        <template #title>关于两类编号（不会混淆）</template>
        <div class="tips__body">
          <p>
            <span class="id-badge id-badge--serial">唯一</span>
            <b>唯一编号</b>：由系统在导入时自动生成，格式 <code>TM-日期-流水号</code>，例如
            <code>TM-20260927-0001</code>。它是系统内部识别号，永不变更、不参与去重。
          </p>
          <p>
            <span class="id-badge id-badge--official">注册号</span>
            <b>商标编号</b>：你 Excel 里的官方注册号（如 <code>711386408046645262</code>），
            原样保存、用作去重与更新依据。
          </p>
        </div>
      </el-alert>

      <div v-if="uploading" class="analyzing">
        <el-icon class="is-loading"><Loading /></el-icon>
        正在解析文件，提取图片与表头结构…
      </div>

      <div v-if="batches.length" class="queue">
        <div class="queue__head">
          <b>已解析 {{ batches.length }} 个文件</b>
          <span class="text-subtle">选择一个继续配置导入</span>
        </div>
        <el-table :data="batches" size="small" border>
          <el-table-column prop="filename" label="文件名" min-width="240" show-overflow-tooltip />
          <el-table-column prop="sheet_name" label="工作表" width="180" show-overflow-tooltip />
          <el-table-column label="数据行" width="90" align="right">
            <template #default="{ row }"><span class="num">{{ row.total_rows }}</span></template>
          </el-table-column>
          <el-table-column label="图片" width="80" align="right">
            <template #default="{ row }"><span class="num">{{ row.image_count }}</span></template>
          </el-table-column>
          <el-table-column label="识别列数" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ row.column_count }}</span></template>
          </el-table-column>
          <el-table-column label="金额列" width="110">
            <template #default="{ row }">
              <el-tag v-if="hasPriceColumn(row)" size="small" type="success" effect="plain">有</el-tag>
              <el-tag v-else size="small" type="info" effect="plain">无</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="startConfigure(row)">配置导入</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- ─────────── 步骤二：列映射 + 预览 ─────────── -->
    <template v-if="step === 1 && preview">
      <el-card shadow="never" class="panel">
        <div class="sec-head">
          <div>
            <h3>列映射：把 Excel 的列对应到系统字段</h3>
            <p class="text-subtle">
              {{ preview.filename }} · {{ preview.sheet_name }} ·
              <span class="num">{{ preview.total_rows }}</span> 行 ·
              <span class="num">{{ preview.image_count }}</span> 张图片
            </p>
          </div>
          <div class="sec-head__actions">
            <el-button size="small" @click="resetMapping">恢复自动识别</el-button>
            <el-button size="small" type="primary" @click="goOptions">下一步：导入设置</el-button>
          </div>
        </div>

        <el-alert v-if="preview.warnings?.length" type="warning" :closable="false" class="warn">
          <p v-for="(w, i) in preview.warnings" :key="i">{{ w }}</p>
        </el-alert>
        <el-alert v-if="mappingError" type="error" :closable="false" class="warn">{{ mappingError }}</el-alert>

        <el-table :data="preview.columns" size="small" border class="map-table">
          <el-table-column label="Excel 列名" width="170">
            <template #default="{ row }"><b>{{ row.header }}</b></template>
          </el-table-column>
          <el-table-column label="系统字段" width="260">
            <template #default="{ row }">
              <el-select v-model="mapping[row.key]" size="small" class="full">
                <el-option v-for="t in MAP_TARGETS" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="识别结果" width="150">
            <template #default="{ row }">
              <el-tag v-if="row.mapped_field === 'image'" size="small" type="success" effect="plain">图片列</el-tag>
              <el-tag v-else-if="mapping[row.key] === 'extra'" size="small" type="warning" effect="plain">自定义列</el-tag>
              <el-tag v-else-if="mapping[row.key] === 'ignore'" size="small" type="info" effect="plain">忽略</el-tag>
              <el-tag v-else size="small" effect="plain">已匹配</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据形态" width="100">
            <template #default="{ row }">
              <span class="text-subtle">{{ TYPE_LABEL[row.data_type] || row.data_type }}</span>
            </template>
          </el-table-column>
          <el-table-column label="非空 / 总行" width="120" align="right">
            <template #default="{ row }">
              <span class="num">{{ row.non_empty }} / {{ preview.total_rows }}</span>
            </template>
          </el-table-column>
          <el-table-column label="样例数据（前3条）" min-width="280">
            <template #default="{ row }">
              <div class="samples">
                <span v-for="(s, i) in row.samples" :key="i" class="sample">{{ s }}</span>
                <span v-if="!row.samples.length" class="text-subtle">
                  {{ row.data_type === 'image' ? '图片为浮动对象，按行自动关联' : '该列无文本数据' }}
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="panel">
        <div class="sec-head">
          <div>
            <h3>数据预览（前 {{ preview.preview_rows.length }} 行）</h3>
            <p class="text-subtle">图片已按 Excel 行号自动关联到对应记录</p>
          </div>
        </div>
        <el-table :data="preview.preview_rows" size="small" border height="360">
          <el-table-column label="源表行" width="76" align="center" prop="excel_row" />
          <el-table-column label="图样" width="88">
            <template #default="{ row }">
              <el-image
                v-if="row.images[0]"
                :src="row.images[0]"
                :preview-src-list="row.images"
                preview-teleported
                fit="cover"
                class="thumb"
              />
              <span v-else class="text-subtle">—</span>
            </template>
          </el-table-column>
          <el-table-column
            v-for="col in mappedPreviewCols"
            :key="col.key"
            :label="col.label"
            min-width="150"
            show-overflow-tooltip
          >
            <template #default="{ row }">{{ displayCell(row.cells, col) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- ─────────── 步骤三：导入设置 ─────────── -->
    <template v-if="step === 2 && preview">
      <el-card shadow="never" class="panel">
        <div class="sec-head">
          <div>
            <h3>导入设置</h3>
            <p class="text-subtle">{{ preview.filename }} · {{ preview.total_rows }} 行待导入</p>
          </div>
          <el-button size="small" @click="step = 1">← 返回列映射</el-button>
        </div>

        <el-form label-width="130px" class="opt-form">
          <el-divider content-position="left">金额处理</el-divider>
          <el-form-item label="金额来源">
            <el-radio-group v-model="options.price_mode">
              <el-radio value="from_file" :disabled="!priceColumnKey">跟随源表列（{{ priceColumnKey || '未映射金额列' }}）</el-radio>
              <el-radio value="fixed">统一设为</el-radio>
              <el-radio value="none">不设金额（留空）</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="options.price_mode === 'fixed'" label="统一金额">
            <el-input-number v-model="options.fixed_price" :min="0" :precision="2" :step="100" />
            <span class="hint">元 / 每个商标</span>
          </el-form-item>
          <el-alert v-if="options.price_mode === 'none'" type="info" :closable="false" class="mb-4">
            导入后金额为空，前台显示「面议」，后台可用「批量改价」随时补充。
          </el-alert>

          <el-divider content-position="left">记录处理</el-divider>
          <el-form-item label="重复商标编号">
            <el-radio-group v-model="options.import_mode">
              <el-radio value="insert_only">跳过已存在（只新增）</el-radio>
              <el-radio value="upsert">覆盖更新已存在</el-radio>
            </el-radio-group>
            <div class="hint block">
              以「商标编号」为准判重；覆盖更新时<b>唯一编号保持不变</b>，不会被重写。
            </div>
          </el-form-item>
          <el-form-item v-if="options.import_mode === 'upsert'" label="图样处理">
            <el-checkbox v-model="options.overwrite_images">用新表格中的图片替换原有图样</el-checkbox>
          </el-form-item>

          <el-divider content-position="left">导入后的状态</el-divider>
          <el-form-item label="状态">
            <el-select v-model="options.status" class="w-200">
              <el-option label="下架（推荐，核对后再上架）" value="off_shelf" />
              <el-option label="直接上架（前台可见）" value="on_sale" />
              <el-option label="已售出" value="sold" />
              <el-option label="预留中" value="reserved" />
            </el-select>
            <span class="hint">仅对新增记录生效，已有记录保留其当前状态</span>
          </el-form-item>
          <el-form-item v-if="!hasCategoryColumn" label="默认类别">
            <el-input-number v-model="options.default_category" :min="1" :max="45" />
            <span class="hint">源表没有类别列，统一按此类别入库</span>
          </el-form-item>
          <el-form-item label="设为精选">
            <el-switch v-model="options.is_featured" />
          </el-form-item>
        </el-form>

        <div class="run-bar">
          <div class="run-bar__summary">
            将导入 <b class="num">{{ preview.total_rows }}</b> 行 ·
            图片 <b class="num">{{ preview.image_count }}</b> 张 ·
            新增记录自动生成唯一编号 <code>{{ serialPreview }}</code>
          </div>
          <el-button type="primary" size="large" :loading="running" @click="doImport">
            {{ running ? '正在导入…' : '确认导入' }}
          </el-button>
        </div>

        <div v-if="running || result" class="progress-box">
          <el-progress
            :percentage="result?.progress ?? current?.progress ?? 0"
            :status="result?.status === 'failed' ? 'exception' : result?.status === 'done' ? 'success' : undefined"
            :stroke-width="14"
          />
          <div class="progress-stats">
            <span>新增 <b class="num">{{ result?.success_count ?? current?.success_count ?? 0 }}</b></span>
            <span>更新 <b class="num">{{ result?.updated_count ?? current?.updated_count ?? 0 }}</b></span>
            <span>跳过 <b class="num">{{ result?.skipped_count ?? current?.skipped_count ?? 0 }}</b></span>
            <span>失败 <b class="num">{{ result?.failed_count ?? current?.failed_count ?? 0 }}</b></span>
          </div>
        </div>

        <el-result
          v-if="result?.status === 'done'"
          icon="success"
          title="导入完成"
          :sub-title="result.message || ''"
          class="result"
        >
          <template #extra>
            <el-button type="primary" @click="finishAndGoList">查看商标列表</el-button>
            <el-button @click="finishAndReset">继续导入下一个文件</el-button>
            <el-button v-if="result.errors?.length" @click="downloadErrors">下载失败清单</el-button>
          </template>
        </el-result>

        <el-result
          v-if="result?.status === 'failed'"
          icon="error"
          title="导入失败"
          :sub-title="result.message || ''"
          class="result"
        >
          <template #extra>
            <el-button type="primary" @click="finishAndReset">重新开始</el-button>
          </template>
        </el-result>

        <div v-if="result?.errors?.length" class="errors">
          <el-divider content-position="left">跳过 / 失败明细（前 200 条）</el-divider>
          <el-table :data="result.errors" size="small" border max-height="280">
            <el-table-column prop="row" label="源表行" width="90" />
            <el-table-column prop="reason" label="原因" />
          </el-table>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, Loading, UploadFilled } from '@element-plus/icons-vue'
import {
  adminImportApi, type ImportBatch, type ImportPreview,
} from '@/api'

const router = useRouter()
const step = ref(0)
const batches = ref<ImportBatch[]>([])
const uploading = ref(false)
const current = ref<ImportBatch | null>(null)
const preview = ref<ImportPreview | null>(null)
const mapping = reactive<Record<string, string>>({})
const running = ref(false)
const result = ref<ImportBatch | null>(null)
let timer: number | undefined

const MAP_TARGETS = [
  { value: 'ignore', label: '忽略（不导入此列）' },
  { value: 'images', label: '图样（图片）' },
  { value: 'name', label: '商标名（必填）' },
  { value: 'category', label: '类别' },
  { value: 'trademark_no', label: '商标编号（官方注册号）' },
  { value: 'price', label: '金额 / 价格' },
  { value: 'products', label: '产品/服务' },
  { value: 'groups', label: '群组' },
  { value: 'registration_date', label: '注册日期' },
  { value: 'expiry_date', label: '有效期至' },
  { value: 'application_count', label: '申请量' },
  { value: 'ai_description', label: 'AI释义' },
  { value: 'legal_status', label: '法律状态' },
  { value: 'remark', label: '备注' },
  { value: 'extra', label: '★ 作为自定义列保留' },
]
const TYPE_LABEL: Record<string, string> = {
  text: '文本', number: '数字', date: '日期', price: '金额', image: '图片',
}

const options = reactive({
  price_mode: 'from_file' as 'from_file' | 'fixed' | 'none',
  fixed_price: 1980,
  status: 'off_shelf' as string,
  import_mode: 'insert_only' as 'insert_only' | 'upsert',
  overwrite_images: true,
  is_featured: false,
  default_category: undefined as number | undefined,
})

const serialPreview = computed(() => {
  const d = new Date()
  const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
  return `TM-${ymd}-0001`
})
const priceColumnKey = computed(
  () => Object.entries(mapping).find(([, v]) => v === 'price')?.[0] || '',
)
const hasCategoryColumn = computed(
  () => Object.values(mapping).includes('category'),
)
const mappingError = computed(() => {
  const targets = Object.values(mapping)
  if (!targets.includes('name')) return '必须把一个列映射为「商标名」，否则整批数据无法入库。'
  if (targets.filter((t) => t === 'name').length > 1) return '「商标名」只能映射一个列。'
  if (targets.filter((t) => t === 'trademark_no').length > 1) return '「商标编号」只能映射一个列（它是去重依据）。'
  if (targets.filter((t) => t === 'price').length > 1) return '「金额」只能映射一个列。'
  const tmNo = targets.includes('trademark_no')
  if (!tmNo) return ''
  return ''
})
const mappedPreviewCols = computed(() => {
  if (!preview.value) return []
  const order = ['name', 'category', 'price', 'trademark_no', 'groups', 'registration_date', 'application_count']
  return preview.value.columns
    .filter((c) => mapping[c.key] && mapping[c.key] !== 'ignore' && mapping[c.key] !== 'images')
    .map((c) => ({ ...c, label: `${c.header}` }))
    .sort((a, b) => {
      const ia = order.indexOf(mapping[a.key])
      const ib = order.indexOf(mapping[b.key])
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib)
    })
})

function hasPriceColumn(b: ImportBatch) {
  return b.columns.some((c) => c.mapped_field === 'price')
}
function displayCell(cells: Record<string, unknown>, col: { key: string }) {
  const v = cells[col.key]
  return v === null || v === undefined || v === '' ? '—' : v
}

async function onFileChange(file: { raw?: File }) {
  if (!file.raw) return
  await doUpload([file.raw])
}

async function doUpload(files: File[]) {
  uploading.value = true
  try {
    const res = await adminImportApi.upload(files)
    batches.value = [...batches.value, ...res.batches]
    if (res.failed?.length) {
      res.failed.forEach((f) => ElMessage.error(`${f.filename}：${f.reason}`))
    }
    if (res.batches.length) {
      ElMessage.success(`已解析 ${res.batches.length} 个文件，请点击「配置导入」继续`)
    }
  } finally {
    uploading.value = false
  }
}

async function startConfigure(batch: ImportBatch) {
  current.value = batch
  preview.value = await adminImportApi.preview(batch.id, 20)
  Object.keys(mapping).forEach((k) => delete mapping[k])
  Object.assign(mapping, preview.value.auto_mapping)
  options.price_mode = hasPriceColumn(batch) ? 'from_file' : 'none'
  options.status = 'off_shelf'
  options.import_mode = 'insert_only'
  result.value = null
  step.value = 1
}
function resetMapping() {
  if (!preview.value) return
  Object.keys(mapping).forEach((k) => delete mapping[k])
  Object.assign(mapping, preview.value.auto_mapping)
  ElMessage.success('已恢复为系统自动识别结果')
}
function goOptions() {
  if (mappingError.value) {
    ElMessage.error(mappingError.value)
    return
  }
  step.value = 2
}

async function doImport() {
  if (!preview.value) return
  if (options.price_mode === 'from_file' && !priceColumnKey.value) {
    ElMessage.warning('未映射金额列，请改选「统一设为」或「不设金额」')
    return
  }
  if (options.price_mode === 'fixed' && !options.fixed_price) {
    ElMessage.warning('请输入统一金额')
    return
  }
  running.value = true
  try {
    await adminImportApi.commit({
      batch_id: preview.value.batch_id,
      mapping,
      price_mode: options.price_mode,
      fixed_price: options.price_mode === 'fixed' ? options.fixed_price : undefined,
      status: options.status,
      import_mode: options.import_mode,
      overwrite_images: options.overwrite_images,
      is_featured: options.is_featured,
      default_category: options.default_category,
    })
    poll()
  } catch {
    running.value = false
  }
}

function poll() {
  if (!preview.value) return
  window.clearInterval(timer)
  timer = window.setInterval(async () => {
    const st = await adminImportApi.status(preview.value!.batch_id)
    current.value = st
    if (st.status === 'done' || st.status === 'failed') {
      window.clearInterval(timer)
      running.value = false
      result.value = st
      if (st.status === 'done') ElMessage.success(st.message || '导入完成')
    }
  }, 800)
}

function finishAndGoList() {
  router.push('/admin/trademarks')
}
function finishAndReset() {
  window.clearInterval(timer)
  batches.value = batches.value.filter((b) => b.id !== preview.value?.batch_id)
  step.value = 0
  preview.value = null
  current.value = null
  result.value = null
}
function downloadErrors() {
  const rows = [['源表行', '原因'], ...(result.value?.errors || []).map((e) => [e.row, e.reason])]
  const csv = '\uFEFF' + rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `导入失败明细_${preview.value?.filename || ''}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
function downloadTemplate() {
  adminImportApi.template()
  ElMessage.success('模板已开始下载')
}

onMounted(() => {
  window.addEventListener('beforeunload', () => window.clearInterval(timer))
})
</script>

<style scoped>
.import-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.steps {
  padding: var(--space-2) 0;
}
.uploader {
  width: 100%;
}
.uploader :deep(.el-upload-dragger) {
  padding: var(--space-10) var(--space-6);
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
  font-size: 46px;
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
.upload-actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-top: var(--space-4);
}
.tips {
  margin-top: var(--space-5);
}
.tips__body p {
  margin: var(--space-2) 0;
  line-height: 1.8;
  font-size: var(--text-sm);
}
.tips__body code {
  font-family: var(--font-mono);
  background: rgba(15, 23, 42, 0.06);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
}
.analyzing {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  color: var(--color-accent-600);
}
.queue {
  margin-top: var(--space-5);
}
.queue__head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.sec-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.sec-head h3 {
  margin: 0 0 4px;
  font-size: var(--text-md);
}
.sec-head p {
  margin: 0;
  font-size: var(--text-xs);
}
.sec-head__actions {
  display: flex;
  gap: var(--space-2);
}
.warn {
  margin-bottom: var(--space-3);
}
.warn p {
  margin: 2px 0;
}
.map-table {
  margin-top: var(--space-2);
}
.full {
  width: 100%;
}
.samples {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.sample {
  background: var(--color-muted);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  font-size: 11px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.thumb {
  width: 52px;
  height: 52px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.opt-form {
  max-width: 780px;
}
.hint {
  margin-left: var(--space-3);
  color: var(--color-subtle-fg);
  font-size: var(--text-xs);
}
.hint.block {
  display: block;
  margin: var(--space-2) 0 0;
  line-height: 1.7;
}
.w-200 {
  width: 260px;
}
.mb-4 {
  margin-bottom: var(--space-4);
  max-width: 560px;
}
.run-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: var(--color-accent-050);
  border: 1px solid var(--color-accent-100);
  border-radius: var(--radius-lg);
  margin-top: var(--space-4);
}
.run-bar__summary {
  font-size: var(--text-sm);
  color: var(--color-accent-600);
}
.run-bar__summary code {
  font-family: var(--font-mono);
  background: #fff;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-accent-100);
}
.progress-box {
  margin-top: var(--space-5);
}
.progress-stats {
  display: flex;
  gap: var(--space-6);
  margin-top: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.result {
  padding: var(--space-4) 0 0;
}
.errors {
  margin-top: var(--space-4);
}
</style>
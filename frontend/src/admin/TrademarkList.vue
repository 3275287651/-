<template>
  <div class="tm-page">
    <!-- 筛选 -->
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <el-input
          v-model="query.q"
          placeholder="搜索：商标名 / 商标编号 / 唯一编号（TM-…）"
          clearable
          class="filter-search"
          @keyup.enter="reload(1)"
          @clear="reload(1)"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="query.category" placeholder="全部类别" clearable class="filter-w" @change="reload(1)">
          <el-option v-for="c in options.categories" :key="c.value" :label="`${c.value}类 (${c.count})`" :value="c.value" />
        </el-select>
        <el-select v-model="query.status" placeholder="全部状态" clearable class="filter-w" @change="reload(1)">
          <el-option label="在售" value="on_sale" />
          <el-option label="已下架" value="off_shelf" />
          <el-option label="已售出" value="sold" />
          <el-option label="预留中" value="reserved" />
        </el-select>
        <el-select v-model="query.price_state" placeholder="金额" clearable class="filter-w-sm" @change="reload(1)">
          <el-option label="已定价" value="set" />
          <el-option label="未定价" value="unset" />
        </el-select>
        <el-button :icon="Filter" @click="advanced = !advanced">
          {{ advanced ? '收起' : '更多筛选' }}
        </el-button>
        <div class="filter-spacer" />
        <el-button type="primary" :icon="Upload" @click="$router.push('/admin/trademarks/import')">
          批量导入
        </el-button>
        <el-button :icon="Download" @click="exportExcel">导出</el-button>
        <el-button :icon="Setting" @click="columnDrawer = true">列设置</el-button>
      </div>

      <el-collapse-transition>
        <div v-show="advanced" class="filter-advanced">
          <div class="filter-item">
            <span class="filter-label">金额区间</span>
            <el-input-number v-model="query.price_min" :min="0" :controls="false" placeholder="最低" class="num-input" />
            <span class="dash">—</span>
            <el-input-number v-model="query.price_max" :min="0" :controls="false" placeholder="最高" class="num-input" />
            <el-button link type="primary" @click="reload(1)">应用</el-button>
          </div>
          <div class="filter-item">
            <span class="filter-label">注册日期</span>
            <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" class="date-range" @change="onDateChange" />
          </div>
          <div class="filter-item">
            <el-checkbox v-model="query.featured" @change="reload(1)">只看精选</el-checkbox>
            <el-button link @click="resetFilters">重置全部</el-button>
          </div>
          <el-alert v-if="hints.length" type="info" :closable="false" class="hint-alert">
            <template #default>
              <span v-for="(h, i) in hints" :key="i">{{ h }}<br v-if="i < hints.length - 1" /></span>
            </template>
          </el-alert>
        </div>
      </el-collapse-transition>
    </el-card>

    <!-- 批量操作条 -->
    <transition name="el-fade-in">
      <div v-if="selection.length" class="batch-bar">
        <div class="batch-bar__info">
          <el-icon><Select /></el-icon>
          已选 <b>{{ selection.length }}</b> 项
          <el-button link type="primary" @click="tableRef?.clearSelection()">清空</el-button>
        </div>
        <div class="batch-bar__actions">
          <el-button size="small" :icon="Top" @click="batch('on_shelf')">批量上架</el-button>
          <el-button size="small" :icon="Bottom" @click="batch('off_shelf')">批量下架</el-button>
          <el-button size="small" type="primary" :icon="Money" @click="priceDialog = true">批量改价</el-button>
          <el-dropdown size="small" @command="onMoreCommand">
            <el-button size="small">
              更多<el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="sold">标记为已售出</el-dropdown-item>
                <el-dropdown-item command="reserved">标记为预留中</el-dropdown-item>
                <el-dropdown-item command="featured">设为精选</el-dropdown-item>
                <el-dropdown-item command="unfeatured">取消精选</el-dropdown-item>
                <el-dropdown-item command="category">批量改类别</el-dropdown-item>
                <el-dropdown-item command="export" divided>导出选中项</el-dropdown-item>
                <el-dropdown-item command="delete" divided style="color: #dc2626">批量删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </transition>

    <!-- 列表 -->
    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ total }}</b> 条记录</span>
        <el-tag v-if="query.batch_id" size="small" type="warning" closable @close="clearBatchFilter">
          正在查看导入批次 #{{ query.batch_id }} 的数据
        </el-tag>
        <span class="text-subtle">
          · 列结构来自导入的 Excel（{{ columns.filter((c) => c.kind === 'extra').length }} 个自定义列）
          · 金额为空表示源表无价格，可批量补价
        </span>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="rows"
        size="small"
        border
        stripe
        height="calc(100vh - 340px)"
        row-key="id"
        @selection-change="(v: TrademarkRow[]) => (selection = v)"
        @sort-change="onSortChange"
      >
        <el-table-column type="selection" width="42" fixed />
        <el-table-column label="序号" width="62" fixed align="center">
          <template #default="{ $index }">
            <span class="num text-subtle">{{ (page - 1) * pageSize + $index + 1 }}</span>
          </template>
        </el-table-column>

        <el-table-column
          v-for="col in visibleColumns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
          :width="colWidth(col)"
          :min-width="colMinWidth(col)"
          :sortable="sortable(col) ? 'custom' : false"
          :fixed="col.key === 'images' ? 'left' : false"
          :show-overflow-tooltip="col.data_type === 'text' && !['serial_no', 'trademark_no'].includes(col.key)"
        >
          <template #header>
            <span class="col-head">
              {{ col.label }}
              <el-tooltip v-if="col.key === 'serial_no'" content="系统自动生成，内部识别用，永不重复（导入时产生）" placement="top">
                <el-icon class="col-head__hint"><QuestionFilled /></el-icon>
              </el-tooltip>
              <el-tooltip v-else-if="col.key === 'trademark_no'" content="官方注册号，来自你的 Excel，用于去重与更新" placement="top">
                <el-icon class="col-head__hint"><QuestionFilled /></el-icon>
              </el-tooltip>
              <el-tag v-if="col.kind === 'extra'" size="small" effect="plain" class="col-head__tag">自定义</el-tag>
            </span>
          </template>
          <template #default="{ row }">
            <!-- 唯一编号 -->
            <span v-if="col.key === 'serial_no'" class="id-cell">
              <span class="id-badge id-badge--serial">唯一</span>
              <span class="mono-id">{{ row.serial_no }}</span>
              <el-icon class="copy-btn" @click="copy(row.serial_no)"><CopyDocument /></el-icon>
            </span>
            <!-- 商标编号 -->
            <span v-else-if="col.key === 'trademark_no'" class="id-cell">
              <span class="id-badge id-badge--official">注册号</span>
              <span class="mono-id">{{ row.trademark_no || '—' }}</span>
              <el-icon v-if="row.trademark_no" class="copy-btn" @click="copy(row.trademark_no)"><CopyDocument /></el-icon>
            </span>
            <!-- 图样 -->
            <div v-else-if="col.key === 'images'" class="img-cell">
              <el-image
                v-if="row.images?.[0]"
                :src="row.images[0].url"
                :preview-src-list="imageUrls(row)"
                preview-teleported
                fit="cover"
                class="thumb"
              />
              <div v-else class="thumb thumb--empty">无图</div>
            </div>
            <!-- 商标名 -->
            <span
              v-else-if="col.key === 'name'"
              class="name-link"
              role="button"
              tabindex="0"
              @click.stop="openDetail(row)"
              @keyup.enter="openDetail(row)"
            >{{ row.name }}</span>
            <!-- 类别 -->
            <span v-else-if="col.key === 'category'" class="num">{{ row.category ? `${row.category}类` : '—' }}</span>
            <!-- 金额 -->
            <template v-else-if="col.key === 'price'">
              <span v-if="row.price !== null" class="price num">¥{{ row.price.toLocaleString() }}</span>
              <el-tooltip v-else content="该商标在源 Excel 中没有价格，可在前台显示为「面议」，也可用批量改价补上" placement="top">
                <el-tag size="small" type="info" effect="plain">未定价</el-tag>
              </el-tooltip>
            </template>
            <!-- 状态 -->
            <el-tag v-else-if="col.key === 'status'" :type="statusType(row.status)" size="small" effect="light">
              {{ STATUS_LABEL[row.status] }}
            </el-tag>
            <span v-else-if="col.key === 'is_featured'">
              <el-icon v-if="row.is_featured" color="#b45309"><StarFilled /></el-icon>
              <span v-else class="text-subtle">—</span>
            </span>
            <!-- 其它核心列 -->
            <span v-else-if="col.data_type === 'price'" class="num">¥{{ fmt(row[col.key]) }}</span>
            <span v-else-if="col.data_type === 'number'" class="num">{{ row[col.key] ?? '—' }}</span>
            <!-- 动态列（Excel 带进来的自定义列） -->
            <span v-else-if="col.kind === 'extra'" :class="{ num: isNumericCol(col) }">
              {{ row.extra?.[col.key] ?? row.extra?.[col.label] ?? '—' }}
            </span>
            <span v-else>{{ row[col.key] ?? '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/admin/trademarks/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button
              link
              size="small"
              :type="row.status === 'on_sale' ? 'warning' : 'success'"
              @click="toggleShelf(row)"
            >
              {{ row.status === 'on_sale' ? '下架' : '上架' }}
            </el-button>
            <el-button link type="danger" size="small" @click="removeOne(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="load"
          @size-change="reload(1)"
        />
      </div>
    </el-card>

    <!-- 批量改价 -->
    <el-dialog v-model="priceDialog" title="批量改价" width="440px" append-to-body>
      <el-form label-width="92px">
        <el-form-item label="调整方式">
          <el-radio-group v-model="priceForm.mode">
            <el-radio value="set">统一设为</el-radio>
            <el-radio value="percent">按比例调整</el-radio>
            <el-radio value="fixed">统一加减</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="priceForm.mode === 'percent' ? '比例(%)' : '金额(元)'">
          <el-input-number v-model="priceForm.value" :precision="2" :step="10" class="full" />
        </el-form-item>
        <el-alert v-if="priceForm.mode !== 'set'" type="warning" :closable="false" class="mb-0">
          未定价的商标会被跳过（比例/加减需要已有金额作为基准），如需补价请用「统一设为」。
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="priceDialog = false">取消</el-button>
        <el-button type="primary" @click="applyPrice">确定改价</el-button>
      </template>
    </el-dialog>

    <!-- 批量改类别 -->
    <el-dialog v-model="catDialog" title="批量修改类别" width="380px" append-to-body>
      <el-input-number v-model="catValue" :min="1" :max="45" class="full" placeholder="输入类别号，如 29" />
      <template #footer>
        <el-button @click="catDialog = false">取消</el-button>
        <el-button type="primary" @click="applyCategory">确定</el-button>
      </template>
    </el-dialog>

    <!-- 列设置 -->
    <el-drawer v-model="columnDrawer" title="表格列设置" size="440px" append-to-body>
      <p class="drawer-tip">
        系统列可按需隐藏；<b>自定义列</b>来自你上传的 Excel —— 新导入一个带新列的表格，这里就会自动多出一列。
      </p>
      <el-divider content-position="left">系统列</el-divider>
      <div v-for="c in coreAllColumns" :key="c.key" class="col-row">
        <el-checkbox v-model="columnVisible[c.key]" @change="saveColumnPref">
          {{ c.label }}
          <span class="text-subtle">（{{ c.filled_count }} 条有值）</span>
        </el-checkbox>
      </div>
      <el-divider content-position="left">自定义列（来自 Excel）</el-divider>
      <el-empty v-if="!extraAllColumns.length" description="还没有自定义列，导入带额外列的 Excel 后会自动出现" :image-size="70" />
      <div v-for="c in extraAllColumns" :key="c.key" class="col-row">
        <el-checkbox v-model="columnVisible[c.key]" @change="saveColumnPref">
          {{ c.label }}
          <el-tag size="small" effect="plain">{{ c.data_type }}</el-tag>
          <span class="text-subtle">（{{ c.filled_count }} 条）</span>
        </el-checkbox>
        <span class="col-row__src text-subtle">{{ c.first_seen_file || '' }}</span>
      </div>
    </el-drawer>

    <!-- 详情抽屉：先打开再补数据，保证点击必定有反馈 -->
    <el-drawer v-model="detailDrawer" :title="detail?.name || '商标详情'" size="620px" append-to-body>
      <div v-if="detail" v-loading="detailLoading" class="detail">
        <div class="detail__ids">
          <div class="detail__id">
            <span class="id-badge id-badge--serial">唯一编号</span>
            <span class="mono-id">{{ detail.serial_no }}</span>
            <el-icon class="copy-btn" @click="copy(detail.serial_no)"><CopyDocument /></el-icon>
          </div>
          <div class="detail__id">
            <span class="id-badge id-badge--official">商标编号</span>
            <span class="mono-id">{{ detail.trademark_no || '—' }}</span>
            <el-icon v-if="detail.trademark_no" class="copy-btn" @click="copy(detail.trademark_no)"><CopyDocument /></el-icon>
          </div>
        </div>
        <div class="detail__gallery">
          <el-image
            v-for="(img, i) in detail.images"
            :key="i"
            :src="img.url"
            :preview-src-list="detail.images.map((x) => x.url)"
            preview-teleported
            fit="contain"
            class="detail__img"
          />
          <el-empty v-if="!detail.images.length" description="无图样" :image-size="60" />
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="类别">{{ detail.category ? `${detail.category}类` : '—' }}</el-descriptions-item>
          <el-descriptions-item label="金额">
            <span v-if="detail.price !== null" class="price">¥{{ detail.price.toLocaleString() }}</span>
            <el-tag v-else size="small" type="info" effect="plain">未定价</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ STATUS_LABEL[detail.status] }}</el-descriptions-item>
          <el-descriptions-item label="精选">{{ detail.is_featured ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="注册日期">{{ detail.registration_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="有效期至">{{ detail.expiry_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="申请量">{{ detail.application_count ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="法律状态">{{ detail.legal_status || '—' }}</el-descriptions-item>
          <el-descriptions-item label="群组" :span="2">{{ detail.groups || '—' }}</el-descriptions-item>
          <el-descriptions-item label="产品/服务" :span="2">
            <div class="long-text">{{ detail.products || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="AI释义" :span="2">
            <div class="long-text">{{ detail.ai_description || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
          <el-descriptions-item label="来源" :span="2">
            {{ detail.source_file || '手工新增' }} · 第 {{ detail.source_row ?? '—' }} 行
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="extraEntries.length">
          <el-divider content-position="left">Excel 自定义列</el-divider>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item v-for="[k, v] in extraEntries" :key="k" :label="k">{{ v }}</el-descriptions-item>
          </el-descriptions>
        </template>

        <div class="detail__foot">
          <el-button type="primary" @click="$router.push(`/admin/trademarks/${detail.id}/edit`)">编辑</el-button>
          <el-button @click="toggleShelf(detail)">
            {{ detail.status === 'on_sale' ? '下架' : '上架' }}
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown, Bottom, CopyDocument, Download, Filter, Money, QuestionFilled, Search, Select,
  Setting, StarFilled, Top, Upload,
} from '@element-plus/icons-vue'
import { adminTrademarkApi, type ColumnDef, type TrademarkRow } from '@/api'

const STATUS_LABEL: Record<string, string> = {
  on_sale: '在售', off_shelf: '已下架', sold: '已售出', reserved: '预留中',
}

const loading = ref(false)
const route = useRoute()
const rows = ref<TrademarkRow[]>([])
const columns = ref<ColumnDef[]>([])
const allColumns = ref<ColumnDef[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const hints = ref<string[]>([])
const advanced = ref(false)
const selection = ref<TrademarkRow[]>([])
const tableRef = ref()
const columnDrawer = ref(false)
const detailDrawer = ref(false)
const detailLoading = ref(false)
const detail = ref<TrademarkRow | null>(null)
const priceDialog = ref(false)
const catDialog = ref(false)
const catValue = ref<number | null>(null)
const dateRange = ref<[string, string] | null>(null)

const query = reactive({
  q: '', category: undefined as number | undefined, status: undefined as string | undefined,
  price_state: undefined as string | undefined, price_min: undefined as number | undefined,
  price_max: undefined as number | undefined, featured: false, batch_id: undefined as number | undefined,
})

/** 支持从看板 / 导入批次页带参跳转过来（如 ?price_state=unset&batch_id=3） */
function applyRouteQuery() {
  const qq = route.query
  if (qq.q) query.q = String(qq.q)
  if (qq.category) query.category = Number(qq.category)
  if (qq.status) query.status = String(qq.status)
  if (qq.price_state) query.price_state = String(qq.price_state)
  if (qq.batch_id) query.batch_id = Number(qq.batch_id)
  if (qq.featured === 'true') query.featured = true
}
const sort = reactive({ sort_by: 'created_at', sort_dir: 'desc' })
const priceForm = reactive({ mode: 'set', value: 0 })
const options = reactive({
  categories: [] as { value: number; count: number }[],
  price_min: null as number | null, price_max: null as number | null, unpriced: 0,
})

const PREF_KEY = 'tm_column_prefs'
const columnVisible = ref<Record<string, boolean>>(
  JSON.parse(localStorage.getItem(PREF_KEY) || '{}'),
)

const visibleColumns = computed(() =>
  columns.value.filter((c) => columnVisible.value[c.key] !== false),
)
const coreAllColumns = computed(() => allColumns.value.filter((c) => c.kind !== 'extra'))
const extraAllColumns = computed(() => allColumns.value.filter((c) => c.kind === 'extra'))
const extraEntries = computed(() => Object.entries(detail.value?.extra || {}))

function sortable(col: ColumnDef) {
  return ['serial_no', 'trademark_no', 'name', 'category', 'price', 'registration_date', 'application_count'].includes(col.key)
}
function colWidth(col: ColumnDef) {
  const w: Record<string, number> = {
    images: 74, serial_no: 196, trademark_no: 220, name: 130, category: 76, price: 108,
    status: 92, registration_date: 112, expiry_date: 112, application_count: 84,
  }
  return w[col.key] ?? undefined
}
function colMinWidth(col: ColumnDef) {
  if (colWidth(col)) return undefined
  return col.kind === 'extra' ? 120 : 140
}
function isNumericCol(col: ColumnDef) {
  return col.data_type === 'number'
}
function imageUrls(row: TrademarkRow) {
  return (row.images || []).map((i) => i.url)
}
function statusType(s: string) {
  return ({ on_sale: 'success', off_shelf: 'info', sold: 'danger', reserved: 'warning' } as const)[s] || 'info'
}
function fmt(v: unknown) {
  return v === null || v === undefined || v === '' ? '—' : v
}
function copy(text?: string | null) {
  if (!text) return
  navigator.clipboard?.writeText(text)
  ElMessage.success(`已复制：${text}`)
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  sort.sort_by = order ? prop : 'created_at'
  sort.sort_dir = order === 'ascending' ? 'asc' : 'desc'
  reload(1)
}
function onDateChange() {
  reload(1)
}
function resetFilters() {
  Object.assign(query, {
    q: '', category: undefined, status: undefined, price_state: undefined,
    price_min: undefined, price_max: undefined, featured: false, batch_id: undefined,
  })
  dateRange.value = null
  reload(1)
}
function saveColumnPref() {
  localStorage.setItem(PREF_KEY, JSON.stringify(columnVisible.value))
}
function clearBatchFilter() {
  query.batch_id = undefined
  reload(1)
}

async function load() {
  loading.value = true
  try {
    const res = await adminTrademarkApi.list({
      ...query,
      ...sort,
      featured: query.featured || undefined,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1],
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items
    columns.value = res.columns || []
    total.value = res.total
    hints.value = res.hints || []
  } finally {
    loading.value = false
  }
}
function reload(p = page.value) {
  page.value = p
  load()
}

async function loadColumns() {
  const res = await adminTrademarkApi.columns()
  allColumns.value = res.items
}
async function loadOptions() {
  const res = await adminTrademarkApi.filterOptions()
  Object.assign(options, res)
}
async function openDetail(row: TrademarkRow) {
  // 先用列表行数据即时渲染，再异步补全「产品/服务、AI释义」等详情字段
  detail.value = row
  detailLoading.value = true
  detailDrawer.value = true
  try {
    detail.value = await adminTrademarkApi.detail(row.id)
  } finally {
    detailLoading.value = false
  }
}

async function batch(action: string, extra: Record<string, unknown> = {}) {
  const ids = selection.value.map((r) => r.id)
  if (!ids.length) return
  if (action === 'delete') {
    await ElMessageBox.confirm(
      `将删除 ${ids.length} 个商标（含其图样与关联数据），且不可恢复。确定继续吗？`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger' },
    )
  }
  const res = await adminTrademarkApi.batch({ action, ids, ...extra })
  ElMessage.success(`操作完成，影响 ${res.affected} 条`)
  if (extra.skipped_unpriced) {
    ElMessage.warning(`其中 ${extra.skipped_unpriced} 条未定价，已跳过（比例/加减需要基准金额）`)
  }
  tableRef.value?.clearSelection()
  load()
  loadOptions()
}

async function applyPrice() {
  const mode = priceForm.mode
  if (mode === 'set') {
    if (!priceForm.value || priceForm.value <= 0) return ElMessage.warning('请输入大于 0 的金额')
    await batch('set_price', { price: priceForm.value })
  } else {
    const v = mode === 'percent' ? priceForm.value : priceForm.value
    if (!v) return ElMessage.warning('请输入调整值')
    await batch('adjust_price', { adjust_mode: mode, adjust_value: v })
  }
  priceDialog.value = false
}
async function applyCategory() {
  if (!catValue.value) return ElMessage.warning('请输入类别号')
  await batch('set_category', { category: catValue.value })
  catDialog.value = false
}
async function toggleShelf(row: TrademarkRow) {
  const action = row.status === 'on_sale' ? 'off_shelf' : 'on_shelf'
  const res = await adminTrademarkApi.batch({ action, ids: [row.id] })
  ElMessage.success(action === 'on_shelf' ? '已上架' : '已下架')
  if (detail.value?.id === row.id) detail.value.status = action === 'on_shelf' ? 'on_sale' : 'off_shelf'
  load()
}
async function removeOne(row: TrademarkRow) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  await adminTrademarkApi.remove(row.id)
  ElMessage.success('已删除')
  load()
}
async function onMoreCommand(cmd: string) {
  if (cmd === 'sold') return batch('set_status', { status: 'sold' })
  if (cmd === 'reserved') return batch('set_status', { status: 'reserved' })
  if (cmd === 'featured') return batch('set_featured', { featured: true })
  if (cmd === 'unfeatured') return batch('set_featured', { featured: false })
  if (cmd === 'category') { catDialog.value = true; return }
  if (cmd === 'delete') return batch('delete')
  if (cmd === 'export') {
    await adminTrademarkApi.export({ ids: selection.value.map((r) => r.id), include_images: 'url' })
    ElMessage.success('导出已开始')
  }
}
async function exportExcel() {
  await adminTrademarkApi.export({
    ...query, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], include_images: 'url',
  })
  ElMessage.success('导出已开始，请查看浏览器下载')
}

onMounted(() => {
  applyRouteQuery()
  if (query.batch_id || query.price_state || query.q) advanced.value = true
  load()
  loadColumns()
  loadOptions()
})
</script>

<style scoped>
.tm-page {
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
  width: 320px;
}
.filter-w {
  width: 150px;
}
.filter-w-sm {
  width: 120px;
}
.filter-spacer {
  flex: 1;
}
.filter-advanced {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px dashed var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.filter-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.filter-label {
  color: var(--color-muted-fg);
  font-size: var(--text-sm);
  min-width: 56px;
}
.num-input {
  width: 120px;
}
.date-range {
  width: 300px;
}
.dash {
  color: var(--color-subtle-fg);
}
.hint-alert {
  max-width: 720px;
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
.id-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.name-link {
  color: var(--color-accent);
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: var(--transition);
}
.name-link:hover,
.name-link:focus-visible {
  border-bottom-color: var(--color-accent);
}
.copy-btn {
  cursor: pointer;
  color: var(--color-subtle-fg);
  font-size: 13px;
}
.copy-btn:hover {
  color: var(--color-accent);
}
.img-cell .thumb {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: #fff;
}
.thumb--empty {
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--color-subtle-fg);
  height: 44px;
}
.price {
  font-weight: 600;
  color: var(--color-primary);
}
.col-head {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.col-head__hint {
  color: var(--color-subtle-fg);
  font-size: 12px;
}
.col-head__tag {
  transform: scale(0.82);
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
}
.full {
  width: 100%;
}
.mb-0 {
  margin-bottom: 0;
}
.drawer-tip {
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
  line-height: 1.7;
}
.col-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
}
.col-row__src {
  font-size: 11px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail__ids {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.detail__id {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.detail__gallery {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.detail__img {
  width: 120px;
  height: 120px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: #fff;
}
.long-text {
  max-height: 120px;
  overflow: auto;
  line-height: 1.7;
}
.detail__foot {
  margin-top: var(--space-5);
  display: flex;
  gap: var(--space-3);
}
</style>
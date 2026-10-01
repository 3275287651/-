<template>
  <div class="sub-page">
    <!-- 统计卡 -->
    <section class="metrics" aria-label="寄售审核概览">
      <div class="metric metric--warning">
        <div class="metric__icon metric__icon--warning"><el-icon><BellFilled /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">
            待审核
            <el-tag v-if="counts.pending > 0" size="small" type="warning" effect="plain" class="metric__hint">
              {{ counts.pending }} 条待处理
            </el-tag>
          </div>
          <div class="metric__value num">{{ n(counts.pending) }}</div>
          <div class="metric__sub">需要尽快给出审核结论</div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon metric__icon--success"><el-icon><CircleCheck /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">已通过</div>
          <div class="metric__value num">{{ n(counts.approved) }}</div>
          <div class="metric__sub">已转为正式在售商品</div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon metric__icon--danger"><el-icon><CircleClose /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">已驳回</div>
          <div class="metric__value num">{{ n(counts.rejected) }}</div>
          <div class="metric__sub">驳回原因客户可见</div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon"><el-icon><Stamp /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">累计提交</div>
          <div class="metric__value num">{{ n(counts.total) }}</div>
          <div class="metric__sub">全部客户寄售申请</div>
        </div>
      </div>
    </section>

    <!-- 筛选 -->
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <el-radio-group v-model="query.status" @change="reload(1)">
          <el-radio-button value="pending">待审核</el-radio-button>
          <el-radio-button value="approved">已通过</el-radio-button>
          <el-radio-button value="rejected">已驳回</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
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
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
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
          <el-button size="small" type="success" :icon="Check" @click="openBatchApprove">批量通过</el-button>
          <el-button size="small" type="danger" :icon="Close" @click="openBatchReject">批量驳回</el-button>
        </div>
      </div>
    </transition>

    <!-- 列表 -->
    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ total }}</b> 条寄售申请</span>
        <span class="text-subtle">· 客户提交的商标经审核通过后，才会成为前台可见的在售商品</span>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="rows"
        size="small"
        border
        stripe
        height="calc(100vh - 430px)"
        row-key="id"
        @selection-change="(v: TrademarkRow[]) => (selection = v)"
      >
        <el-table-column type="selection" width="42" fixed />
        <el-table-column label="图样" width="72" fixed>
          <template #default="{ row }">
            <el-image
              v-if="row.designs?.[0]"
              :src="row.designs[0].url"
              :preview-src-list="designUrls(row)"
              preview-teleported
              fit="cover"
              class="thumb"
            />
            <div v-else class="thumb thumb--empty">无图</div>
          </template>
        </el-table-column>
        <el-table-column label="商标证" width="88" align="center">
          <template #default="{ row }">
            <div v-if="row.certificates?.length" class="cert-cell">
              <el-image
                :src="row.certificates[0].url"
                :preview-src-list="certUrls(row)"
                preview-teleported
                fit="cover"
                class="thumb thumb--cert"
              />
              <span class="cert-cell__count num">{{ row.certificates.length }} 张</span>
            </div>
            <el-tag v-else size="small" type="info" effect="plain">未提供</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商标名" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="name-link" role="button" tabindex="0" @click="openDetail(row)" @keyup.enter="openDetail(row)">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="76" align="center">
          <template #default="{ row }"><span class="num">{{ row.category ? `${row.category}类` : '—' }}</span></template>
        </el-table-column>
        <el-table-column label="唯一编号" width="210">
          <template #default="{ row }">
            <span class="id-cell">
              <span class="id-badge id-badge--serial">唯一</span>
              <span class="mono-id">{{ row.serial_no }}</span>
              <el-icon class="copy-btn" @click="copy(row.serial_no)"><CopyDocument /></el-icon>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="商标编号 / 注册号" width="224">
          <template #default="{ row }">
            <span class="id-cell">
              <span class="id-badge id-badge--official">注册号</span>
              <span class="mono-id">{{ row.trademark_no || '—' }}</span>
              <el-icon v-if="row.trademark_no" class="copy-btn" @click="copy(row.trademark_no)"><CopyDocument /></el-icon>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="期望售价" width="112" align="right">
          <template #default="{ row }">
            <span v-if="row.price !== null" class="price num">¥{{ row.price.toLocaleString() }}</span>
            <span v-else class="text-subtle">未定价</span>
          </template>
        </el-table-column>
        <el-table-column label="提交人" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="submitter">
              <span>{{ submitterName(row) }}</span>
              <span class="text-subtle num">{{ submitterPhone(row) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center">
          <template #default="{ row }">
            <el-tag :type="reviewType(row.review_status)" size="small" effect="light">
              {{ row.review_label || REVIEW_LABEL[row.review_status] }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="176" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button
              link
              type="success"
              size="small"
              :disabled="row.review_status === 'approved'"
              @click="openApprove(row)"
            >通过</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.review_status === 'rejected'"
              @click="openReject(row)"
            >驳回</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty :description="emptyText" :image-size="80" />
        </template>
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

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailDrawer" :title="detail?.name || '寄售申请详情'" size="640px" append-to-body>
      <div v-if="detail" class="detail">
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

        <div class="detail__section">
          <div class="detail__section-head">商标图样（前台展示）</div>
          <div class="detail__gallery">
            <el-image
              v-for="(img, i) in detail.designs"
              :key="i"
              :src="img.url"
              :preview-src-list="detail.designs.map((x) => x.url)"
              preview-teleported
              fit="contain"
              class="detail__img"
            />
            <el-empty v-if="!detail.designs?.length" description="客户未提供图样" :image-size="60" />
          </div>
        </div>

        <div class="detail__section detail__section--cert">
          <div class="detail__section-head">
            <el-icon><DocumentChecked /></el-icon>
            商标证（审核关键材料，点击可放大查看）
          </div>
          <div class="detail__gallery">
            <el-image
              v-for="(c, i) in detail.certificates"
              :key="i"
              :src="c.url"
              :preview-src-list="detail.certificates.map((x) => x.url)"
              preview-teleported
              fit="contain"
              class="detail__img detail__img--cert"
            />
            <el-alert
              v-if="!detail.certificates?.length"
              type="warning"
              :closable="false"
              class="mb-0"
              title="客户未上传商标证"
              description="注册证是审核的关键依据，请要求客户补充后再通过。"
            />
          </div>
        </div>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="类别">{{ detail.category ? `${detail.category}类` : '—' }}</el-descriptions-item>
          <el-descriptions-item label="期望售价">
            <span v-if="detail.price !== null" class="price num">¥{{ detail.price.toLocaleString() }}</span>
            <span v-else class="text-subtle">客户未定价</span>
          </el-descriptions-item>
          <el-descriptions-item label="注册日期">{{ detail.registration_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="有效期至">{{ detail.expiry_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="法律状态">{{ detail.legal_status || '—' }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="reviewType(detail.review_status)" size="small" effect="light">
              {{ detail.review_label || REVIEW_LABEL[detail.review_status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="群组" :span="2">{{ detail.groups || '—' }}</el-descriptions-item>
          <el-descriptions-item label="产品/服务" :span="2">
            <div class="long-text">{{ detail.products || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="AI释义" :span="2">
            <div class="long-text">{{ detail.ai_description || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="客户备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">客户联系方式</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="提交人">{{ submitterName(detail) }}</el-descriptions-item>
          <el-descriptions-item label="账号手机号">{{ submitterPhone(detail) }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ detail.contact_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ detail.contact_phone || '—' }}</el-descriptions-item>
        </el-descriptions>

        <template v-if="detail.reviewed_at || detail.review_remark">
          <el-divider content-position="left">审核历史</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="审核时间">{{ detail.reviewed_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="审核说明">
              <div class="long-text">{{ detail.review_remark || '—' }}</div>
            </el-descriptions-item>
          </el-descriptions>
        </template>

        <div class="detail__foot">
          <el-button type="success" :disabled="detail.review_status === 'approved'" @click="openApprove(detail)">通过</el-button>
          <el-button type="danger" :disabled="detail.review_status === 'rejected'" @click="openReject(detail)">驳回</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 通过 -->
    <el-dialog v-model="approveDialog" :title="approveTargets.length > 1 ? `批量通过（${approveTargets.length} 条）` : '通过寄售申请'" width="480px" append-to-body>
      <el-form label-width="92px">
        <el-form-item label="调整售价">
          <el-input-number
            v-model="approveForm.price"
            :min="0"
            :precision="2"
            :step="100"
            controls-position="right"
            class="full"
            placeholder="留空则沿用客户期望价"
          />
        </el-form-item>
        <el-form-item label="上架状态">
          <el-radio-group v-model="approveForm.status">
            <el-radio value="on_sale">直接上架（前台可见）</el-radio>
            <el-radio value="off_shelf">先不上架</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-alert v-if="approveTargets.length === 1" type="info" :closable="false" class="mb-0">
          客户期望价：
          <b v-if="approveTargets[0].price !== null" class="num">¥{{ approveTargets[0].price.toLocaleString() }}</b>
          <span v-else>未填写</span>
        </el-alert>
        <el-alert v-else type="info" :closable="false" class="mb-0">
          批量通过时若填写售价，将统一覆盖所选申请的售价；留空则各自沿用客户期望价。
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="approveDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <!-- 驳回 -->
    <el-dialog v-model="rejectDialog" :title="rejectTargets.length > 1 ? `批量驳回（${rejectTargets.length} 条）` : '驳回寄售申请'" width="520px" append-to-body>
      <el-form label-width="92px">
        <el-form-item label="驳回原因" required>
          <el-input
            v-model="rejectForm.remark"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
            placeholder="请写清缺什么材料或哪里不符合要求"
          />
        </el-form-item>
      </el-form>
      <el-alert type="warning" :closable="false" class="mb-0">
        这段说明客户会在个人中心看到，请写清缺什么材料或哪里不符合要求。
      </el-alert>
      <template #footer>
        <el-button @click="rejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="submitReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  BellFilled, Check, CircleCheck, CircleClose, Close, CopyDocument, DocumentChecked,
  Refresh, Search, Select, Stamp,
} from '@element-plus/icons-vue'
import { adminSubmissionApi, type TrademarkRow } from '@/api'

const REVIEW_LABEL: Record<string, string> = {
  pending: '待审核', approved: '已通过', rejected: '已驳回',
}
const REVIEW_TYPE: Record<string, 'warning' | 'success' | 'danger'> = {
  pending: 'warning', approved: 'success', rejected: 'danger',
}

const loading = ref(false)
const submitting = ref(false)
const rows = ref<TrademarkRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const selection = ref<TrademarkRow[]>([])
const tableRef = ref()
const counts = reactive({ pending: 0, approved: 0, rejected: 0, total: 0 })

const query = reactive({ status: 'pending', q: '' })

const detailDrawer = ref(false)
const detail = ref<TrademarkRow | null>(null)

const approveDialog = ref(false)
const rejectDialog = ref(false)
const approveTargets = ref<TrademarkRow[]>([])
const rejectTargets = ref<TrademarkRow[]>([])
const approveForm = reactive<{ price: number | null; status: string }>({ price: null, status: 'on_sale' })
const rejectForm = reactive({ remark: '' })

const emptyText = computed(() =>
  query.status === 'pending' ? '暂无待审核的寄售申请' : '没有符合条件的寄售申请',
)

function n(v: unknown) {
  return Number(v || 0).toLocaleString()
}
function reviewType(s: string) {
  return REVIEW_TYPE[s] || 'info'
}
function submitterName(row: TrademarkRow) {
  return row.submitter?.nickname || row.contact_name || '—'
}
function submitterPhone(row: TrademarkRow) {
  return row.submitter?.phone || row.contact_phone || '—'
}
/** 图样/商标证的大图预览地址列表（模板里不能写 TS 类型标注，故抽成函数） */
function designUrls(row: TrademarkRow) {
  return (row.designs || []).map((d) => d.url)
}
function certUrls(row: TrademarkRow) {
  return (row.certificates || []).map((c) => c.url)
}
function copy(text?: string | null) {
  if (!text) return
  navigator.clipboard?.writeText(text)
  ElMessage.success(`已复制：${text}`)
}

async function load() {
  loading.value = true
  try {
    const res = await adminSubmissionApi.list({
      status: query.status,
      q: query.q || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
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
async function loadSummary() {
  const res = await adminSubmissionApi.summary()
  Object.assign(counts, {
    pending: res.pending, approved: res.approved, rejected: res.rejected, total: res.total,
  })
}
function refreshAll() {
  load()
  loadSummary()
}

function openDetail(row: TrademarkRow) {
  detail.value = row
  detailDrawer.value = true
}

function openApprove(row: TrademarkRow) {
  approveTargets.value = [row]
  approveForm.price = row.price
  approveForm.status = 'on_sale'
  approveDialog.value = true
}
function openReject(row: TrademarkRow) {
  rejectTargets.value = [row]
  rejectForm.remark = ''
  rejectDialog.value = true
}
function openBatchApprove() {
  if (!selection.value.length) return
  approveTargets.value = [...selection.value]
  approveForm.price = null
  approveForm.status = 'on_sale'
  approveDialog.value = true
}
function openBatchReject() {
  if (!selection.value.length) return
  rejectTargets.value = [...selection.value]
  rejectForm.remark = ''
  rejectDialog.value = true
}

async function submitApprove() {
  const targets = approveTargets.value
  if (!targets.length) return
  const price = approveForm.price === null || approveForm.price === undefined ? undefined : approveForm.price
  const ids = targets.map((t) => t.id)
  submitting.value = true
  try {
    if (ids.length === 1) {
      await adminSubmissionApi.review(ids[0], { action: 'approve', price, status: approveForm.status })
    } else {
      await ElMessageBox.confirm(
        `将通过所选 ${ids.length} 条寄售申请${price !== undefined ? `，并统一设为 ¥${price}` : ''}，通过后即成为正式在售商品。确定继续吗？`,
        '批量通过确认',
        { type: 'warning', confirmButtonText: '确认通过' },
      )
      await adminSubmissionApi.batchReview({ ids, action: 'approve', price })
    }
    ElMessage.success(ids.length === 1 ? '已通过该寄售申请' : `已通过 ${ids.length} 条寄售申请`)
    approveDialog.value = false
    tableRef.value?.clearSelection()
    refreshAll()
  } catch {
    /* 取消或请求失败：错误提示由拦截器给出，弹窗保留便于重试 */
  } finally {
    submitting.value = false
  }
}

async function submitReject() {
  const targets = rejectTargets.value
  if (!targets.length) return
  const remark = rejectForm.remark.trim()
  if (!remark) {
    ElMessage.warning('请填写驳回原因，客户会在个人中心看到这段说明')
    return
  }
  const ids = targets.map((t) => t.id)
  submitting.value = true
  try {
    if (ids.length === 1) {
      await adminSubmissionApi.review(ids[0], { action: 'reject', remark })
    } else {
      await ElMessageBox.confirm(
        `将驳回所选 ${ids.length} 条寄售申请，驳回原因会展示给客户。确定继续吗？`,
        '批量驳回确认',
        { type: 'warning', confirmButtonText: '确认驳回', confirmButtonClass: 'el-button--danger' },
      )
      await adminSubmissionApi.batchReview({ ids, action: 'reject', remark })
    }
    ElMessage.success(ids.length === 1 ? '已驳回该寄售申请' : `已驳回 ${ids.length} 条寄售申请`)
    rejectDialog.value = false
    tableRef.value?.clearSelection()
    refreshAll()
  } catch {
    /* 取消或请求失败 */
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  load()
  loadSummary()
})
</script>

<style scoped>
.sub-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}
.metric {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: var(--transition);
}
.metric--warning {
  border-color: var(--color-warning);
  background: var(--color-warning-bg);
}
.metric__icon {
  flex: none;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--radius);
  background: var(--color-primary);
  color: var(--color-on-primary);
  font-size: 17px;
}
.metric__icon--warning {
  background: var(--color-warning);
}
.metric__icon--success {
  background: var(--color-success);
}
.metric__icon--danger {
  background: var(--color-destructive);
}
.metric__body {
  min-width: 0;
}
.metric__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.metric__hint {
  transform: scale(0.9);
}
.metric__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.25;
  color: var(--color-primary);
}
.metric__sub {
  font-size: 11px;
  color: var(--color-subtle-fg);
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.filter-search {
  width: 340px;
}
.filter-spacer {
  flex: 1;
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
.thumb {
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
.thumb--cert {
  border-color: var(--color-accent-100);
}
.cert-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.cert-cell__count {
  font-size: 10px;
  color: var(--color-accent-600);
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
.price {
  font-weight: 600;
  color: var(--color-primary);
}
.submitter {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
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
.detail__section {
  margin-bottom: var(--space-4);
}
.detail__section-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary);
}
.detail__gallery {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.detail__img {
  width: 120px;
  height: 120px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: #fff;
}
.detail__img--cert {
  width: 160px;
  height: 160px;
  border-color: var(--color-accent-100);
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
@media (max-width: 1200px) {
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
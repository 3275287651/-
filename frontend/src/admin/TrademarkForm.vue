<template>
  <div v-loading="loading" class="tm-form">
    <!-- 编辑模式：唯一编号醒目区 -->
    <el-card v-if="isEdit" shadow="never" class="panel serial-panel">
      <div class="serial">
        <div class="serial__left">
          <span class="id-badge id-badge--serial">唯一编号</span>
          <span class="serial__value mono-id">{{ detail?.serial_no || '—' }}</span>
          <el-icon v-if="detail?.serial_no" class="copy-btn" title="复制唯一编号" @click="copy(detail.serial_no)">
            <CopyDocument />
          </el-icon>
        </div>
        <p class="serial__tip">
          <el-icon><InfoFilled /></el-icon>
          系统自动生成，不可修改，与商标编号无关（用于内部识别，永不重复）。
        </p>
      </div>
    </el-card>

    <!-- 基本信息 -->
    <el-card shadow="never" class="panel">
      <template #header>
        <div class="card-head">
          <h3>{{ isEdit ? '编辑商标信息' : '新增商标' }}</h3>
          <span class="text-subtle">{{ isEdit ? '修改后立即生效' : '保存后系统会自动生成唯一编号' }}</span>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="112px" label-position="right">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form-item label="商标名" prop="name">
              <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="例如：尚标易" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="类别">
              <el-input-number v-model="form.category" :min="1" :max="45" :controls="false" placeholder="1-45" class="full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="商标编号" prop="trademark_no">
          <div class="field-block">
            <el-input
              v-model="form.trademark_no"
              placeholder="官方注册号，如 711386408046645262"
              class="mono-input"
              @blur="checkTrademarkNo"
            />
            <p class="hint">来自商标注册证 / Excel，用于去重与更新（可为空，留空则不去重）。</p>
            <p v-if="dupError" class="field-error">
              <el-icon><WarningFilled /></el-icon>{{ dupError }}
            </p>
          </div>
        </el-form-item>

        <el-form-item label="产品/服务">
          <el-input v-model="form.products" type="textarea" :rows="3" placeholder="核定使用的商品或服务项目" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form-item label="群组">
              <el-input v-model="form.groups" placeholder="例如：2901;2902" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="法律状态">
              <el-input v-model="form.legal_status" placeholder="例如：有效 / 已注册" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form-item label="注册日期">
              <el-date-picker
                v-model="form.registration_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择注册日期"
                class="full"
                @change="onRegistrationChange"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="有效期至">
              <el-date-picker
                v-model="form.expiry_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择注册日期后自动 +10 年"
                class="full"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form-item label="申请量">
              <el-input-number v-model="form.application_count" :min="0" :controls="false" placeholder="申请数量" class="full" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" class="full">
                <el-option label="在售" value="on_sale" />
                <el-option label="已下架" value="off_shelf" />
                <el-option label="已售出" value="sold" />
                <el-option label="预留中" value="reserved" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="金额">
          <div class="price-field">
            <el-input-number
              v-model="form.price"
              :min="0"
              :precision="2"
              :controls="false"
              placeholder="留空表示未定价"
              class="price-input"
            />
            <el-button v-if="form.price !== null && form.price !== undefined" link type="primary" @click="form.price = null">
              清空金额
            </el-button>
            <span v-if="form.price === null || form.price === undefined" class="hint hint--inline">留空则前台显示「面议」</span>
          </div>
        </el-form-item>

        <el-form-item label="AI释义">
          <el-input v-model="form.ai_description" type="textarea" :rows="3" placeholder="对商标含义、适用场景的智能解读" />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="内部备注，仅后台可见" />
        </el-form-item>

        <el-form-item label="是否精选">
          <el-switch v-model="form.is_featured" />
          <span class="hint hint--inline">精选商标会出现在前台首页推荐位</span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 图样管理 -->
    <el-card shadow="never" class="panel">
      <template #header>
        <div class="card-head">
          <h3>图样管理</h3>
          <span class="text-subtle">支持多张，第一张即主图（前台列表展示用）</span>
        </div>
      </template>
      <div class="gallery">
        <div v-for="(img, i) in images" :key="img.url" class="img-box" :class="{ 'img-box--primary': i === 0 }">
          <el-image :src="img.url" :preview-src-list="images.map((x) => x.url)" preview-teleported fit="contain" class="img-box__img" />
          <span v-if="i === 0" class="img-box__badge">主图</span>
          <div class="img-box__ops">
            <el-button v-if="i !== 0" link size="small" @click="setPrimary(i)">设为主图</el-button>
            <el-button link type="danger" size="small" @click="removeImage(i)">删除</el-button>
          </div>
        </div>
        <el-upload :show-file-list="false" :http-request="handleUpload" accept=".png,.jpg,.jpeg,.gif,.webp,.svg" class="upload-box">
          <div class="upload-box__inner">
            <el-icon><Plus /></el-icon>
            <span>上传图样</span>
          </div>
        </el-upload>
      </div>
      <p class="hint">单张不超过 5MB，支持 png / jpg / jpeg / gif / webp / svg。</p>
    </el-card>

    <!-- Excel 自定义列 -->
    <el-card shadow="never" class="panel">
      <template #header>
        <div class="card-head">
          <h3>Excel 自定义列</h3>
          <span class="text-subtle">列名 = Excel 表头，内容 = 该单元格的值；随商标一起保存</span>
        </div>
      </template>
      <div v-if="extraRows.length" class="extra-list">
        <div v-for="(row, i) in extraRows" :key="i" class="extra-row">
          <el-input v-model="row.key" placeholder="列名（如：代理机构）" class="extra-key" />
          <el-input v-model="row.value" placeholder="内容" class="extra-value" />
          <el-button link type="danger" :icon="Delete" @click="extraRows.splice(i, 1)">删除</el-button>
        </div>
      </div>
      <el-empty v-else description="暂无自定义列，可手工添加" :image-size="60" />
      <el-button :icon="Plus" class="add-extra" @click="extraRows.push({ key: '', value: '' })">添加一列</el-button>
    </el-card>

    <!-- 操作 -->
    <div class="actions">
      <el-button @click="$router.push('/admin/trademarks')">取消返回</el-button>
      <el-button type="primary" :loading="saving" @click="submit">{{ isEdit ? '保存修改' : '创建商标' }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type UploadRequestOptions } from 'element-plus'
import {
  CopyDocument, Delete, InfoFilled, Plus, WarningFilled,
} from '@element-plus/icons-vue'
import { adminApi, adminTrademarkApi, type TrademarkRow } from '@/api'

const route = useRoute()
const router = useRouter()

const editingId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isEdit = computed(() => editingId.value !== null)

const loading = ref(false)
const saving = ref(false)
const detail = ref<TrademarkRow | null>(null)
const dupError = ref('')
const formRef = ref<FormInstance>()
const images = ref<{ url: string }[]>([])
const extraRows = ref<{ key: string; value: string }[]>([])

const form = reactive({
  name: '',
  trademark_no: '',
  category: null as number | null,
  products: '',
  groups: '',
  registration_date: '' as string,
  expiry_date: '' as string,
  legal_status: '',
  application_count: null as number | null,
  price: null as number | null,
  ai_description: '',
  remark: '',
  status: 'off_shelf',
  is_featured: false,
})

const rules = {
  name: [{ required: true, message: '请填写商标名', trigger: 'blur' }],
}

function copy(text?: string | null) {
  if (!text) return
  navigator.clipboard?.writeText(text)
  ElMessage.success(`已复制：${text}`)
}
function toYmd(d: Date) {
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}
function onRegistrationChange(v: string | null) {
  if (!v) return
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return
  d.setFullYear(d.getFullYear() + 10)
  form.expiry_date = toYmd(d)
}

async function checkTrademarkNo() {
  dupError.value = ''
  const v = form.trademark_no?.trim()
  if (!v) return
  try {
    const res = await adminTrademarkApi.list({ q: v, page: 1, page_size: 5 })
    const hit = res.items.find((it) => (it.trademark_no || '') === v && it.id !== editingId.value)
    if (hit) dupError.value = `商标编号 ${v} 已被占用（唯一编号 ${hit.serial_no}），提交会被拒绝。`
  } catch {
    /* 校验失败不阻塞填写，提交时后端会再次校验 */
  }
}

function setPrimary(i: number) {
  const [img] = images.value.splice(i, 1)
  images.value.unshift(img)
}
function removeImage(i: number) {
  images.value.splice(i, 1)
}
async function handleUpload(options: UploadRequestOptions) {
  try {
    const res = await adminApi.upload(options.file as File, 'trademark')
    images.value.push({ url: res.url })
    options.onSuccess?.(res)
    ElMessage.success('图样上传成功')
  } catch (err) {
    options.onError?.(err as never)
  }
}

function buildExtra(): Record<string, string> {
  const out: Record<string, string> = {}
  for (const row of extraRows.value) {
    const k = row.key.trim()
    if (k) out[k] = row.value
  }
  return out
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      trademark_no: form.trademark_no?.trim() || null,
      category: form.category ?? null,
      products: form.products || null,
      groups: form.groups || null,
      registration_date: form.registration_date || null,
      expiry_date: form.expiry_date || null,
      legal_status: form.legal_status || null,
      application_count: form.application_count ?? null,
      price: form.price === undefined || form.price === null ? null : form.price,
      ai_description: form.ai_description || null,
      remark: form.remark || null,
      status: form.status,
      is_featured: form.is_featured,
      images: images.value.map((i) => i.url),
      extra: buildExtra(),
    }
    if (isEdit.value && editingId.value !== null) {
      await adminTrademarkApi.update(editingId.value, payload)
      ElMessage.success('商标信息已保存')
    } else {
      await adminTrademarkApi.create(payload)
      ElMessage.success('商标已创建')
    }
    router.push('/admin/trademarks')
  } catch {
    /* 错误提示已由请求拦截器统一弹出（例如商标编号重复的 400） */
  } finally {
    saving.value = false
  }
}

async function loadDetail() {
  if (editingId.value === null) return
  loading.value = true
  try {
    const d = await adminTrademarkApi.detail(editingId.value)
    detail.value = d
    Object.assign(form, {
      name: d.name || '',
      trademark_no: d.trademark_no || '',
      category: d.category ?? null,
      products: d.products || '',
      groups: d.groups || '',
      registration_date: d.registration_date || '',
      expiry_date: d.expiry_date || '',
      legal_status: d.legal_status || '',
      application_count: d.application_count ?? null,
      price: d.price ?? null,
      ai_description: d.ai_description || '',
      remark: d.remark || '',
      status: d.status || 'off_shelf',
      is_featured: !!d.is_featured,
    })
    images.value = (d.images || []).map((i) => ({ url: i.url }))
    extraRows.value = Object.entries(d.extra || {}).map(([key, value]) => ({
      key,
      value: value === null || value === undefined ? '' : String(value),
    }))
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.tm-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 1080px;
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.serial-panel {
  border-color: var(--color-primary-600);
}
.serial {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.serial__left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.serial__value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
}
.serial__tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.copy-btn {
  cursor: pointer;
  color: var(--color-subtle-fg);
}
.copy-btn:hover {
  color: var(--color-accent);
}
.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.card-head h3 {
  margin: 0;
  font-size: var(--text-md);
}
.full {
  width: 100%;
}
.field-block {
  width: 100%;
}
.mono-input :deep(.el-input__inner) {
  font-family: var(--font-mono);
}
.hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--color-subtle-fg);
}
.hint--inline {
  margin-left: var(--space-3);
}
.field-error {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 4px 0 0;
  font-size: var(--text-xs);
  color: var(--color-destructive);
}
.price-field {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
}
.price-input {
  width: 220px;
}
.gallery {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}
.img-box {
  position: relative;
  width: 132px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
  background: #fff;
}
.img-box--primary {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-accent-100);
}
.img-box__img {
  display: block;
  width: 100%;
  height: 118px;
}
.img-box__badge {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  color: var(--color-on-accent);
  background: var(--color-accent);
}
.img-box__ops {
  display: flex;
  justify-content: center;
  gap: var(--space-1);
  border-top: 1px solid var(--color-border);
  padding: 2px 0;
}
.upload-box {
  width: 132px;
}
.upload-box__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 152px;
  border: 1.5px dashed var(--color-border-strong);
  border-radius: var(--radius);
  color: var(--color-subtle-fg);
  font-size: var(--text-xs);
  transition: var(--transition);
}
.upload-box__inner:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-050);
}
.extra-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.extra-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.extra-key {
  width: 260px;
}
.extra-value {
  flex: 1;
}
.add-extra {
  margin-top: var(--space-2);
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-2) 0 var(--space-4);
}
@media (max-width: 900px) {
  .extra-row {
    flex-wrap: wrap;
  }
  .extra-key,
  .extra-value {
    width: 100%;
    flex: auto;
  }
  .price-field {
    flex-wrap: wrap;
  }
}
</style>
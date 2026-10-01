<template>
  <div class="site-container">
    <!-- 引导区 -->
    <section class="sell-hero">
      <el-icon class="sell-hero__icon"><Shop /></el-icon>
      <div>
        <h1 class="page-title sell-hero__title">我要卖标</h1>
        <p class="sell-hero__sub">把闲置商标托管到平台，我们负责展示、撮合与过户，成交后结算。</p>
      </div>
    </section>

    <!-- 未登录门槛 -->
    <div v-if="!user.isLoggedIn" class="panel-card login-gate">
      <el-icon class="login-gate__icon"><Lock /></el-icon>
      <h3 class="login-gate__title">登录后即可提交商标</h3>
      <p class="login-gate__desc">提交需要核对你的身份与联系方式，登录后即可填写托管信息。</p>
      <el-button type="primary" size="large" class="login-gate__btn" @click="goLogin">
        登录后即可提交商标
      </el-button>
    </div>

    <template v-else>
      <!-- 三步说明 -->
      <div class="steps-grid sell-steps">
        <div class="step-card">
          <div class="step-card__no">01</div>
          <h4>填写商标信息</h4>
          <p>填写商标名、类别与联系方式，建议一并填写注册号，方便平台核验。</p>
        </div>
        <div class="step-card">
          <div class="step-card__no">02</div>
          <h4>上传图样与商标证</h4>
          <p>商标图样用于前台展示；注册证仅平台核验权属，不对公众公开。</p>
        </div>
        <div class="step-card">
          <div class="step-card__no">03</div>
          <h4>平台审核后上架</h4>
          <p>提交后 1 个工作日内完成审核，通过后进入平台展示与撮合。</p>
        </div>
      </div>

      <!-- 提交表单 -->
      <div class="panel-card sell-form-card">
        <h2 class="sell-form__title">托管信息</h2>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
          <div class="form-grid">
            <el-form-item label="商标名" prop="name" class="form-grid__full">
              <el-input v-model="form.name" maxlength="60" show-word-limit placeholder="如：尚标易（与注册证一致）" />
            </el-form-item>

            <el-form-item label="类别" prop="category">
              <el-select v-model="form.category" placeholder="请选择第几类" filterable class="full">
                <el-option v-for="c in categoryOptions" :key="c" :label="`第 ${c} 类`" :value="c" />
              </el-select>
            </el-form-item>

            <el-form-item label="注册日期" prop="registration_date">
              <el-date-picker
                v-model="form.registration_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择注册日期"
                class="full"
              />
            </el-form-item>

            <el-form-item label="商标编号 / 注册号" prop="trademark_no" class="form-grid__full">
              <el-input v-model="form.trademark_no" placeholder="选填，如 711386408046645262" />
              <p class="field-hint">填了可以加快审核；如果该注册号平台已收录，会提示你无需重复提交。</p>
            </el-form-item>

            <el-form-item label="群组" prop="groups" class="form-grid__full">
              <el-input v-model="form.groups" placeholder="选填，多个群组用分号隔开，如 2901；2902" />
            </el-form-item>

            <el-form-item label="产品 / 服务" prop="products" class="form-grid__full">
              <el-input
                v-model="form.products"
                type="textarea"
                :rows="3"
                maxlength="500"
                show-word-limit
                placeholder="选填，填写该商标核定使用的商品或服务项目"
              />
            </el-form-item>

            <el-form-item label="期望售价（元）" prop="price" class="form-grid__full">
              <el-input-number
                v-model="form.price"
                :min="1"
                :step="100"
                :precision="2"
                :controls="false"
                class="price-input"
                placeholder="请输入你希望卖给买家的价格"
              />
              <p class="field-hint">这是你希望卖给买家的价格，平台可协助议价。</p>
            </el-form-item>

            <el-form-item label="联系人" prop="contact_name">
              <el-input v-model="form.contact_name" maxlength="30" placeholder="真实姓名或公司联系人" />
            </el-form-item>

            <el-form-item label="联系电话" prop="contact_phone">
              <el-input v-model="form.contact_phone" maxlength="20" placeholder="用于平台与你核对信息" />
            </el-form-item>

            <el-form-item label="备注" prop="remark" class="form-grid__full">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="3"
                maxlength="300"
                show-word-limit
                placeholder="选填，可写明「同名多类」、共有商标等信息"
              />
            </el-form-item>
          </div>
        </el-form>

        <!-- 商标图样 -->
        <section class="upload-section">
          <div class="upload-section__head">
            <h3 class="upload-section__title">
              商标图样
              <span class="required-mark">必传 · 至少 1 张</span>
            </h3>
            <p class="upload-section__hint">商标本身的图形（logo 图片），用于前台展示，可上传多张。</p>
          </div>
          <div class="upload-grid">
            <div v-for="(url, i) in designs" :key="url" class="upload-thumb">
              <el-image :src="url" :preview-src-list="designs" :initial-index="i" preview-teleported fit="contain" class="upload-thumb__img" />
              <button type="button" class="upload-thumb__del" aria-label="删除该图样" @click="designs.splice(i, 1)">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <el-upload
              :show-file-list="false"
              :http-request="uploadDesign"
              :accept="IMAGE_ACCEPT"
              :disabled="uploadingDesign"
              class="upload-trigger"
            >
              <div class="upload-box" :class="{ 'upload-box--loading': uploadingDesign }">
                <el-icon><Plus /></el-icon>
                <span>{{ uploadingDesign ? '上传中…' : '上传图样' }}</span>
              </div>
            </el-upload>
          </div>
        </section>

        <!-- 商标证 -->
        <section class="upload-section">
          <div class="upload-section__head">
            <h3 class="upload-section__title">
              商标证
              <span class="required-mark">必传 · 至少 1 张</span>
            </h3>
            <p class="upload-section__hint">
              商标注册证的扫描件或照片，用于核实权属，仅平台后台与你本人可见、不对公众公开。
            </p>
          </div>
          <div class="upload-grid">
            <div v-for="(url, i) in certificates" :key="url" class="upload-thumb">
              <el-image :src="url" :preview-src-list="certificates" :initial-index="i" preview-teleported fit="contain" class="upload-thumb__img" />
              <button type="button" class="upload-thumb__del" aria-label="删除该商标证" @click="certificates.splice(i, 1)">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <el-upload
              :show-file-list="false"
              :http-request="uploadCert"
              :accept="IMAGE_ACCEPT"
              :disabled="uploadingCert"
              class="upload-trigger"
            >
              <div class="upload-box upload-drop" :class="{ 'upload-box--loading': uploadingCert }">
                <el-icon><UploadFilled /></el-icon>
                <span>{{ uploadingCert ? '上传中…' : '点击上传注册证照片 / 扫描件' }}</span>
              </div>
            </el-upload>
          </div>
        </section>

        <div class="submit-bar">
          <el-checkbox v-model="agreed" class="commit-check">
            我确认该商标为本人 / 本公司合法持有，信息真实有效
          </el-checkbox>
          <el-button type="primary" size="large" :loading="submitting" class="submit-btn" @click="submit">
            提交审核
          </el-button>
        </div>
      </div>
    </template>

    <!-- 提交结果 -->
    <el-dialog v-model="resultVisible" title="提交成功" width="480px" :close-on-click-modal="false">
      <div v-if="result" class="result-box">
        <div class="result-id">
          <div class="result-id__head">
            <span>唯一编号</span>
            <span class="id-badge id-badge--serial">系统生成</span>
          </div>
          <span class="mono-id result-id__value">{{ result.serial_no }}</span>
          <p class="result-id__hint">平台内部识别用，提交与查询时以它为准。</p>
        </div>
        <div class="result-id">
          <div class="result-id__head">
            <span>商标编号</span>
            <span class="id-badge id-badge--official">官方注册号</span>
          </div>
          <span class="mono-id result-id__value">{{ result.trademark_no || '未填写' }}</span>
          <p class="result-id__hint">国家商标局颁发的注册号，用于权属核实；未填写时审核可能变慢。</p>
        </div>
        <div class="result-state">
          <span>当前状态</span>
          <el-tag type="warning" effect="light">待审核</el-tag>
        </div>
        <el-alert
          type="info"
          :closable="false"
          title="平台将在 1 个工作日内完成审核，结果可在个人中心查看。"
        />
      </div>
      <template #footer>
        <el-button @click="continueSubmit">继续提交下一个</el-button>
        <el-button type="primary" @click="goMySubmissions">个人中心 · 我的寄售</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules, type UploadRequestOptions } from 'element-plus'
import { Close, Lock, Plus, Shop, UploadFilled } from '@element-plus/icons-vue'
import { submissionApi, type SubmissionPayload, type TrademarkRow } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const user = useUserStore()

const IMAGE_ACCEPT = '.png,.jpg,.jpeg,.gif,.webp,.svg'
const categoryOptions = Array.from({ length: 45 }, (_, i) => i + 1)

const formRef = ref<FormInstance>()
const submitting = ref(false)
const resultVisible = ref(false)
const result = ref<TrademarkRow | null>(null)
const agreed = ref(false)

const designs = ref<string[]>([])
const certificates = ref<string[]>([])
const uploadingDesign = ref(false)
const uploadingCert = ref(false)

const form = reactive({
  name: '',
  category: null as number | null,
  trademark_no: '',
  registration_date: '' as string,
  groups: '',
  products: '',
  price: null as number | null,
  contact_name: user.profile?.nickname || '',
  contact_phone: user.profile?.phone || '',
  remark: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请填写商标名', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
  price: [{ required: true, message: '请填写期望售价', trigger: 'change' }],
  contact_name: [{ required: true, message: '请填写联系人', trigger: 'blur' }],
  contact_phone: [
    { required: true, message: '请填写联系电话', trigger: 'blur' },
    { pattern: /^[0-9+\-\s]{6,20}$/, message: '联系电话格式不正确', trigger: 'blur' },
  ],
}

async function handleUpload(options: UploadRequestOptions, target: typeof designs, flag: typeof uploadingDesign) {
  flag.value = true
  try {
    const res = await submissionApi.upload(options.file as File)
    target.value.push(res.url)
    options.onSuccess?.(res)
  } catch (err) {
    options.onError?.(err as never)
  } finally {
    flag.value = false
  }
}
function uploadDesign(options: UploadRequestOptions) {
  return handleUpload(options, designs, uploadingDesign)
}
function uploadCert(options: UploadRequestOptions) {
  return handleUpload(options, certificates, uploadingCert)
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: '/sell' } })
}

function buildPayload(): SubmissionPayload {
  return {
    name: form.name.trim(),
    category: form.category,
    trademark_no: form.trademark_no.trim() || null,
    registration_date: form.registration_date || null,
    expiry_date: null,
    groups: form.groups.trim() || null,
    products: form.products.trim() || null,
    legal_status: null,
    ai_description: null,
    remark: form.remark.trim() || null,
    price: form.price,
    contact_name: form.contact_name.trim(),
    contact_phone: form.contact_phone.trim(),
    design_images: [...designs.value],
    certificates: [...certificates.value],
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!designs.value.length) {
    ElMessage.warning('请至少上传 1 张商标图样')
    return
  }
  if (!certificates.value.length) {
    ElMessage.warning('请至少上传 1 张商标证')
    return
  }
  if (!agreed.value) {
    ElMessage.warning('请先勾选权属承诺')
    return
  }
  submitting.value = true
  try {
    const res = await submissionApi.create(buildPayload())
    result.value = res.submission
    resultVisible.value = true
  } catch {
    /* 拦截器已提示 */
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  formRef.value?.resetFields()
  form.registration_date = ''
  form.price = null
  agreed.value = false
  designs.value = []
  certificates.value = []
}

function continueSubmit() {
  resultVisible.value = false
  result.value = null
  resetForm()
}

function goMySubmissions() {
  resultVisible.value = false
  router.push({ path: '/user', query: { tab: 'submissions' } })
}
</script>

<style scoped>
/* 引导区 */
.sell-hero {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-6) var(--space-6);
  background: var(--color-accent-050);
  border: 1px solid var(--color-accent-100);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
}
.sell-hero__icon {
  font-size: 34px;
  color: var(--color-accent);
  flex: none;
}
.sell-hero__title {
  margin: 0 0 var(--space-1);
}
.sell-hero__sub {
  margin: 0;
  color: var(--color-muted-fg);
  font-size: var(--text-md);
  line-height: 1.7;
}

/* 登录门槛 */
.login-gate {
  text-align: center;
  padding: var(--space-16) var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.login-gate__icon {
  font-size: 38px;
  color: var(--color-muted-fg);
}
.login-gate__title {
  margin: var(--space-4) 0 var(--space-2);
}
.login-gate__desc {
  margin: 0 0 var(--space-5);
  color: var(--color-muted-fg);
}
.login-gate__btn {
  min-height: 46px;
}

/* 三步 */
.sell-steps {
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: var(--space-6);
}

/* 表单 */
.sell-form-card {
  max-width: 860px;
}
.sell-form__title {
  margin: 0 0 var(--space-5);
  font-size: var(--text-lg);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2) var(--space-6);
}
.form-grid__full {
  grid-column: 1 / -1;
}
.full {
  width: 100%;
}
.price-input {
  width: 100%;
  max-width: 320px;
}
.field-hint {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
  line-height: 1.6;
}

/* 上传区 */
.upload-section {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-5);
  margin-top: var(--space-4);
}
.upload-section__head {
  margin-bottom: var(--space-4);
}
.upload-section__title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-md);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.required-mark {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--color-warning);
  background: var(--color-warning-bg);
  border: 1px solid #fde68a;
  border-radius: 999px;
  padding: 1px 10px;
}
.upload-section__hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
  line-height: 1.7;
}
.upload-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: flex-start;
}
.upload-thumb {
  position: relative;
  width: 104px;
  height: 104px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: #fff;
  overflow: hidden;
}
.upload-thumb__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.upload-thumb__del {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}
.upload-thumb__del:hover {
  background: var(--color-destructive);
}
.upload-trigger :deep(.el-upload) {
  display: block;
}
.upload-box {
  width: 104px;
  height: 104px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius);
  background: #fbfcfe;
  color: var(--color-subtle-fg);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: var(--transition);
}
.upload-box .el-icon {
  font-size: 22px;
}
.upload-box:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.upload-drop {
  width: 208px;
  height: 104px;
  padding: 0 var(--space-4);
  text-align: center;
  line-height: 1.5;
}
.upload-box--loading {
  cursor: progress;
  opacity: 0.7;
}

/* 提交栏 */
.submit-bar {
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}
.commit-check {
  flex: 1;
  min-width: 240px;
  height: auto;
  white-space: normal;
}
.commit-check :deep(.el-checkbox__label) {
  white-space: normal;
  line-height: 1.6;
}
.submit-btn {
  min-height: 46px;
  min-width: 160px;
}

/* 结果 */
.result-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.result-id {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: #fbfcfe;
}
.result-id__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
  margin-bottom: var(--space-1);
}
.result-id__value {
  font-size: var(--text-md);
  color: var(--color-fg);
  word-break: break-all;
}
.result-id__hint {
  margin: var(--space-2) 0 0;
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
  line-height: 1.6;
}
.result-state {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}

@media (max-width: 820px) {
  .sell-steps {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .price-input {
    max-width: none;
  }
  .upload-thumb,
  .upload-box {
    width: 92px;
    height: 92px;
  }
  .upload-drop {
    width: 100%;
    min-width: 200px;
  }
  .submit-btn {
    width: 100%;
  }
}
</style>
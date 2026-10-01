<template>
  <div class="settings-page">
    <!-- 非超级管理员 -->
    <el-card v-if="!admin.isSuper" shadow="never" class="panel">
      <el-empty description="仅超级管理员可访问本站点配置">
        <el-button @click="$router.push('/admin/dashboard')">返回数据看板</el-button>
      </el-empty>
    </el-card>

    <template v-else>
      <el-card v-loading="loading" shadow="never" class="panel">
        <div class="toolbar">
          <div>
            <h3>网站配置</h3>
            <p class="text-subtle">这些内容会显示在前台首页、详情页与报价单中，修改后立即生效。</p>
          </div>
          <el-button type="primary" :icon="Check" :loading="saving" @click="save">保存全部配置</el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="panel">
        <el-tabs v-model="tab">
          <!-- 基础信息 -->
          <el-tab-pane label="基础信息" name="base">
            <el-form label-width="120px" class="cfg-form">
              <el-form-item label="网站名称">
                <el-input v-model="values.site_name" maxlength="60" show-word-limit />
              </el-form-item>
              <el-form-item label="网站副标题">
                <el-input v-model="values.site_subtitle" maxlength="80" show-word-limit />
              </el-form-item>
              <el-form-item label="网站 Logo">
                <div class="img-field">
                  <img v-if="values.logo_url" :src="values.logo_url" alt="网站 Logo" class="img-field__preview" />
                  <div v-else class="img-field__empty">暂无 Logo</div>
                  <div class="img-field__ops">
                    <el-upload :show-file-list="false" :http-request="uploadLogo" accept=".png,.jpg,.jpeg,.gif,.webp,.svg">
                      <el-button :icon="Upload">上传 Logo</el-button>
                    </el-upload>
                    <el-button v-if="values.logo_url" link type="danger" @click="values.logo_url = ''">移除</el-button>
                    <span class="hint">建议高度 40px 左右的透明 PNG</span>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="浏览器图标（favicon）">
                <div class="img-field">
                  <img v-if="values.favicon_url" :src="values.favicon_url" alt="浏览器图标" class="img-field__favicon" />
                  <div v-else class="img-field__empty">暂无图标</div>
                  <div class="img-field__ops">
                    <el-upload :show-file-list="false" :http-request="uploadFavicon" accept=".png,.jpg,.jpeg,.gif,.webp,.svg,.ico">
                      <el-button :icon="Upload">上传图标</el-button>
                    </el-upload>
                    <el-button v-if="values.favicon_url" link type="danger" @click="values.favicon_url = ''">移除</el-button>
                    <span class="hint">显示在浏览器标签页；建议 32×32 或 64×64 的方形图（PNG/SVG/ICO）。留空则使用 Logo</span>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="备案号">
                <el-input v-model="values.icp" placeholder="如 京ICP备00000000号" />
              </el-form-item>
              <el-form-item label="版权信息">
                <el-input v-model="values.copyright" />
              </el-form-item>
              <el-form-item label="联系电话">
                <el-input v-model="values.contact_phone" />
              </el-form-item>
              <el-form-item label="公司地址">
                <el-input v-model="values.address" />
              </el-form-item>
              <el-form-item label="公司简介">
                <el-input v-model="values.company_intro" type="textarea" :rows="5" />
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 客服配置 -->
          <el-tab-pane label="客服配置" name="service">
            <el-form label-width="120px" class="cfg-form">
              <el-form-item label="客服微信">
                <el-input v-model="values.service_wechat" />
              </el-form-item>
              <el-form-item label="客服二维码">
                <div class="img-field">
                  <img v-if="values.service_qr" :src="values.service_qr" alt="客服二维码" class="img-field__preview img-field__preview--qr" />
                  <div v-else class="img-field__empty img-field__empty--qr">暂无二维码</div>
                  <div class="img-field__ops">
                    <el-upload :show-file-list="false" :http-request="uploadQr" accept=".png,.jpg,.jpeg,.gif,.webp,.svg">
                      <el-button :icon="Upload">上传二维码</el-button>
                    </el-upload>
                    <el-button v-if="values.service_qr" link type="danger" @click="values.service_qr = ''">移除</el-button>
                    <span class="hint">建议 400×400 正方形图片</span>
                  </div>
                </div>
              </el-form-item>
              <el-form-item label="服务时间">
                <el-input v-model="values.service_hours" placeholder="如 周一至周六 09:00-18:00" />
              </el-form-item>
              <el-form-item label="客服文案">
                <el-input v-model="values.service_text" type="textarea" :rows="3" />
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 首页与流程 -->
          <el-tab-pane label="首页与流程" name="home">
            <section class="sub">
              <div class="sub__head">
                <div>
                  <h4>交易流程步骤</h4>
                  <p class="text-subtle">展示在前台「关于 / 流程」区域，建议 4 个步骤。</p>
                </div>
                <el-button size="small" :icon="Plus" @click="steps.push({ title: '', desc: '' })">添加步骤</el-button>
              </div>
              <div v-if="steps.length" class="steps-editor">
                <div v-for="(s, i) in steps" :key="i" class="step-row">
                  <span class="step-row__no num">{{ i + 1 }}</span>
                  <el-input v-model="s.title" placeholder="步骤标题，如：挑选商标" class="step-row__title" />
                  <el-input v-model="s.desc" placeholder="步骤描述" class="step-row__desc" />
                  <el-button link type="danger" :icon="Delete" @click="steps.splice(i, 1)">删除</el-button>
                </div>
              </div>
              <el-empty v-else description="暂无流程步骤" :image-size="60" />
            </section>

            <el-divider />

            <section class="sub">
              <div class="sub__head">
                <div>
                  <h4>首页轮播图</h4>
                  <p class="text-subtle">最多 5 张；可只填写标题与副标题，图片可为空。</p>
                </div>
                <el-button size="small" :icon="Plus" :disabled="banners.length >= 5" @click="addBanner">添加轮播图</el-button>
              </div>
              <div v-if="banners.length" class="banner-list">
                <div v-for="(b, i) in banners" :key="i" class="banner-row">
                  <div class="banner-row__img">
                    <img v-if="b.image_url" :src="b.image_url" alt="轮播图" />
                    <span v-else class="text-subtle">无图</span>
                  </div>
                  <div class="banner-row__fields">
                    <el-input v-model="b.title" placeholder="主标题" />
                    <el-input v-model="b.subtitle" placeholder="副标题" />
                    <div class="banner-row__ops">
                      <el-upload :show-file-list="false" :http-request="bannerUploader(i)" accept=".png,.jpg,.jpeg,.gif,.webp,.svg">
                        <el-button size="small" :icon="Upload">上传图片</el-button>
                      </el-upload>
                      <el-button size="small" link type="danger" :icon="Delete" @click="banners.splice(i, 1)">删除</el-button>
                    </div>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无轮播图" :image-size="60" />
            </section>
          </el-tab-pane>

          <!-- 详情页字段开关 -->
          <el-tab-pane label="详情页字段开关" name="detail">
            <p class="tab-tip text-subtle">控制前台商标详情页显示哪些字段（关闭后对应信息不在前台展示，后台仍可见）。</p>
            <div class="switch-grid">
              <div v-for="f in DISPLAY_FIELDS" :key="f.key" class="switch-row">
                <span class="switch-row__label">{{ f.label }}</span>
                <el-switch v-model="displayFields[f.key]" />
              </div>
            </div>
          </el-tab-pane>

          <!-- SEO -->
          <el-tab-pane label="SEO" name="seo">
            <el-form label-width="120px" class="cfg-form">
              <el-form-item label="首页标题">
                <el-input v-model="values.seo_home_title" maxlength="120" show-word-limit />
              </el-form-item>
              <el-form-item label="首页关键词">
                <el-input v-model="values.seo_home_keywords" type="textarea" :rows="2" placeholder="多个关键词用英文逗号分隔" />
              </el-form-item>
              <el-form-item label="首页描述">
                <el-input v-model="values.seo_home_desc" type="textarea" :rows="3" />
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 系统设置 -->
          <el-tab-pane label="系统设置" name="system">
            <el-form label-width="140px" class="cfg-form">
              <el-form-item label="报价单默认有效期">
                <el-input-number v-model="quoteDays" :min="1" :max="30" />
                <span class="hint">天（生成报价单时默认有效期，1-30 天）</span>
              </el-form-item>
              <el-form-item label="图片大小上限">
                <el-input-number v-model="imageMaxMb" :min="1" :max="20" />
                <span class="hint">MB</span>
              </el-form-item>
              <el-form-item label="导出图片水印">
                <el-switch v-model="exportWatermark" />
                <span class="hint">开启后导出/前台展示的图样会叠加水印文字</span>
              </el-form-item>
              <el-form-item label="水印文字">
                <el-input v-model="values.watermark_text" :disabled="!exportWatermark" placeholder="如：尚标易" />
              </el-form-item>
              <el-form-item label="密码最小长度">
                <el-input-number v-model="passwordMinLen" :min="6" :max="32" />
                <span class="hint">位（前台注册密码校验）</span>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>

        <div class="actions">
          <el-button type="primary" :icon="Check" :loading="saving" @click="save">保存全部配置</el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { Check, Delete, Plus, Upload } from '@element-plus/icons-vue'
import { adminApi } from '@/api'
import { useAdminStore } from '@/stores/auth'
import { applyBranding } from '@/utils/branding'

const admin = useAdminStore()

const DISPLAY_FIELDS = [
  { key: 'trademark_no', label: '商标编号' },
  { key: 'category', label: '类别' },
  { key: 'products', label: '产品/服务' },
  { key: 'groups', label: '群组' },
  { key: 'registration_date', label: '注册日期' },
  { key: 'expiry_date', label: '有效期至' },
  { key: 'legal_status', label: '法律状态' },
  { key: 'application_count', label: '申请量' },
  { key: 'ai_description', label: 'AI释义' },
  { key: 'remark', label: '备注' },
  { key: 'source_file', label: '来源文件' },
  { key: 'serial_no', label: '唯一编号' },
]

const loading = ref(false)
const saving = ref(false)
const tab = ref('base')
const values = reactive<Record<string, string>>({})
const steps = ref<{ title: string; desc: string }[]>([])
const banners = ref<{ image_url: string; title: string; subtitle: string }[]>([])
const displayFields = reactive<Record<string, boolean>>({})

const quoteDays = computed({
  get: () => toNum(values.quote_default_days, 7),
  set: (v: number | null | undefined) => { values.quote_default_days = v === undefined || v === null ? '7' : String(v) },
})
const imageMaxMb = computed({
  get: () => toNum(values.image_max_mb, 5),
  set: (v: number | null | undefined) => { values.image_max_mb = v === undefined || v === null ? '5' : String(v) },
})
const passwordMinLen = computed({
  get: () => toNum(values.password_min_len, 8),
  set: (v: number | null | undefined) => { values.password_min_len = v === undefined || v === null ? '8' : String(v) },
})
const exportWatermark = computed({
  get: () => values.export_watermark === 'true',
  set: (v: boolean) => { values.export_watermark = v ? 'true' : 'false' },
})

function toNum(v: string | undefined, fallback: number) {
  const n = Number(v)
  return Number.isFinite(n) && v !== '' && v !== undefined ? n : fallback
}

function parseArray(raw: string | undefined): any[] {
  try {
    const arr = JSON.parse(raw || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}
function parseObject(raw: string | undefined): Record<string, any> {
  try {
    const obj = JSON.parse(raw || '{}')
    return obj && typeof obj === 'object' && !Array.isArray(obj) ? obj : {}
  } catch {
    return {}
  }
}

function addBanner() {
  if (banners.value.length >= 5) {
    ElMessage.warning('首页轮播图最多 5 张')
    return
  }
  banners.value.push({ image_url: '', title: '', subtitle: '' })
}

async function uploadLogo(options: UploadRequestOptions) {
  try {
    const res = await adminApi.upload(options.file as File, 'logo')
    values.logo_url = res.url
    options.onSuccess?.(res)
    ElMessage.success('Logo 已上传')
  } catch (e) {
    options.onError?.(e as never)
  }
}

async function uploadFavicon(options: UploadRequestOptions) {
  try {
    const res = await adminApi.upload(options.file as File, 'favicon')
    values.favicon_url = res.url
    options.onSuccess?.(res)
    // 立即应用，省得用户以为没生效
    applyBranding({
      site_name: values.site_name,
      seo_home_title: values.seo_home_title,
      logo_url: values.logo_url,
      favicon_url: values.favicon_url,
    })
    ElMessage.success('图标已上传，浏览器标签页图标已更新')
  } catch (e) {
    options.onError?.(e as never)
  }
}
async function uploadQr(options: UploadRequestOptions) {
  try {
    const res = await adminApi.upload(options.file as File, 'logo')
    values.service_qr = res.url
    options.onSuccess?.(res)
    ElMessage.success('二维码已上传')
  } catch (e) {
    options.onError?.(e as never)
  }
}
async function uploadBanner(index: number, options: UploadRequestOptions) {
  try {
    const res = await adminApi.upload(options.file as File, 'banner')
    banners.value[index].image_url = res.url
    options.onSuccess?.(res)
    ElMessage.success('轮播图已上传')
  } catch (e) {
    options.onError?.(e as never)
  }
}
function bannerUploader(index: number) {
  return (options: UploadRequestOptions) => uploadBanner(index, options)
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.settings()
    Object.keys(values).forEach((k) => delete values[k])
    Object.assign(values, res.values || {})

    steps.value = parseArray(values.process_steps).map((s) => ({
      title: String(s?.title ?? ''),
      desc: String(s?.desc ?? ''),
    }))
    banners.value = parseArray(values.banner).map((b) => ({
      image_url: String(b?.image_url ?? ''),
      title: String(b?.title ?? ''),
      subtitle: String(b?.subtitle ?? ''),
    }))
    const df = parseObject(values.display_fields)
    DISPLAY_FIELDS.forEach((f) => { displayFields[f.key] = df[f.key] !== false })
  } finally {
    loading.value = false
  }
}

async function save() {
  const cleanSteps = steps.value.filter((s) => s.title.trim() || s.desc.trim())
  const cleanBanners = banners.value.filter((b) => b.image_url || b.title.trim() || b.subtitle.trim())
  const payload: Record<string, string> = {
    ...values,
    process_steps: JSON.stringify(cleanSteps, null, 0),
    banner: JSON.stringify(cleanBanners, null, 0),
    display_fields: JSON.stringify({ ...displayFields }),
  }
  saving.value = true
  try {
    await adminApi.saveSettings(payload)
    // 保存后立即应用到网页头（标题 + 图标），不用刷新就能看到效果
    applyBranding({
      site_name: values.site_name,
      seo_home_title: values.seo_home_title,
      logo_url: values.logo_url,
      favicon_url: values.favicon_url,
    })
    ElMessage.success('配置已保存并生效')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await load()
  applyBranding({
    site_name: values.site_name,
    seo_home_title: values.seo_home_title,
    logo_url: values.logo_url,
    favicon_url: values.favicon_url,
  })
})
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 1080px;
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
.cfg-form {
  max-width: 720px;
  padding-top: var(--space-2);
}
.hint {
  margin-left: var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
.tab-tip {
  margin: 0 0 var(--space-4);
  font-size: var(--text-sm);
}
.img-field {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.img-field__preview {
  width: 120px;
  height: 44px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.img-field__preview--qr {
  width: 100px;
  height: 100px;
}
.img-field__favicon {
  width: 44px;
  height: 44px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  padding: 3px;
}
.img-field__empty {
  display: grid;
  place-items: center;
  width: 120px;
  height: 44px;
  font-size: 11px;
  color: var(--color-subtle-fg);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
}
.img-field__empty--qr {
  width: 100px;
  height: 100px;
}
.img-field__ops {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.sub__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.sub__head h4 {
  margin: 0 0 4px;
  font-size: var(--text-base);
}
.sub__head p {
  margin: 0;
  font-size: var(--text-xs);
}
.steps-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.step-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.step-row__no {
  flex: none;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 11px;
}
.step-row__title {
  width: 220px;
}
.step-row__desc {
  flex: 1;
}
.banner-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.banner-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
}
.banner-row__img {
  flex: none;
  width: 150px;
  height: 84px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: #fff;
  overflow: hidden;
  font-size: 11px;
}
.banner-row__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.banner-row__fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.banner-row__ops {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.switch-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  max-width: 760px;
}
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.switch-row__label {
  font-size: var(--text-sm);
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}
@media (max-width: 900px) {
  .switch-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .step-row,
  .banner-row {
    flex-wrap: wrap;
  }
  .step-row__title,
  .step-row__desc {
    width: 100%;
    flex: auto;
  }
}
</style>
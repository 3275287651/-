<template>
  <div class="system-page">
    <!-- A. 版本信息 -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>版本信息</h3>
          <p class="text-subtle">当前实例的应用信息与指纹，用于授权签发与升级核对。</p>
        </div>
        <el-button :icon="Refresh" :loading="loadingVersion" @click="loadVersion">刷新</el-button>
      </div>

      <div v-loading="loadingVersion">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="应用名">{{ versionInfo?.app_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="版本号">
            <span class="num">{{ versionInfo?.version || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="构建时间">{{ versionInfo?.build_time || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Python 版本">
            <span class="num">{{ versionInfo?.python || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="实例指纹" :span="2">
            <div class="fingerprint">
              <span class="mono-id">{{ versionInfo?.instance_id || '—' }}</span>
              <el-button
                link
                type="primary"
                :icon="CopyDocument"
                :disabled="!versionInfo?.instance_id"
                @click="copyText(versionInfo?.instance_id, '实例指纹')"
              >
                复制
              </el-button>
            </div>
            <p class="text-subtle fingerprint__hint">
              把它提供给服务商，即可为你签发绑定本实例的授权码。
            </p>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- B. 授权（License） -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>
            授权（License）
            <el-tag :type="licenseTag.type" effect="light" size="small">{{ licenseTag.text }}</el-tag>
          </h3>
          <p class="text-subtle">授权码由服务商签发，绑定本实例指纹，用于控制功能与授权期限。</p>
        </div>
      </div>

      <el-alert
        v-if="license?.reason"
        :type="license.valid ? 'success' : 'info'"
        :closable="false"
        class="mb-4"
      >
        <template #title>{{ license.reason }}</template>
      </el-alert>

      <el-descriptions v-if="license?.valid" :column="2" border size="small" class="mb-4">
        <el-descriptions-item label="授权对象">{{ license.customer || '—' }}</el-descriptions-item>
        <el-descriptions-item label="到期日期">
          <span class="num">{{ license.expires_at || '—' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="功能项" :span="2">
          <template v-if="license.features?.length">
            <el-tag v-for="f in license.features" :key="f" size="small" effect="plain" class="feat-tag">{{ f }}</el-tag>
          </template>
          <span v-else>—</span>
        </el-descriptions-item>
        <el-descriptions-item label="当前策略" :span="2">
          <b>{{ enforceLabel }}</b>
          <span class="text-subtle">{{ enforceHint }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <template v-else>
        <p class="text-subtle mb-2">当前策略：{{ enforceLabel }}{{ enforceHint }}</p>
      </template>

      <el-input
        v-model="licenseKey"
        type="textarea"
        :rows="4"
        placeholder="粘贴服务商签发的授权码"
        class="mono-input"
      />

      <el-alert v-if="licenseError" type="error" :closable="false" class="mt-3">
        <template #title>授权码未通过校验</template>
        <p class="alert-text">{{ licenseError }}</p>
      </el-alert>

      <div class="actions">
        <el-button type="primary" :loading="savingLicense" :disabled="!licenseKey.trim()" @click="saveLicense">
          保存授权码
        </el-button>
        <el-button
          type="danger"
          plain
          :loading="clearingLicense"
          :disabled="!license?.has_key"
          @click="clearLicense"
        >
          清除授权码
        </el-button>
      </div>
    </el-card>

    <!-- C. 升级 -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>升级</h3>
          <p class="text-subtle">
            当前版本 <b class="num">{{ versionInfo?.version || '—' }}</b>
            · 升级校验密钥
            <el-tag :type="upgrade?.key_configured ? 'success' : 'danger'" size="small" effect="plain">
              {{ upgrade?.key_configured ? '已配置' : '未配置' }}
            </el-tag>
          </p>
        </div>
      </div>

      <el-alert v-if="upgrade && !upgrade.key_configured" type="warning" :closable="false" class="mb-4">
        <template #title>本实例未配置升级校验密钥</template>
        <p class="alert-text">
          需要在实例上设置环境变量 <code>UPGRADE_KEY</code>（与厂商侧一致），否则无法校验升级清单签名，升级功能不可用。
        </p>
      </el-alert>

      <!-- 步骤 1 -->
      <el-divider content-position="left">步骤 1 · 校验升级清单</el-divider>
      <el-input
        v-model="manifestText"
        type="textarea"
        :rows="5"
        placeholder="粘贴厂商 tools/upgrade_sign.py 生成的升级清单 JSON"
        class="mono-input"
      />
      <div class="actions">
        <el-button type="primary" :loading="checking" :disabled="!manifestText.trim()" @click="doCheck">
          校验清单
        </el-button>
      </div>

      <template v-if="checkResult">
        <el-alert
          :type="checkResult.has_update ? 'success' : 'info'"
          :closable="false"
          class="mt-3"
        >
          <template #title>{{ checkResult.message }}</template>
        </el-alert>
        <el-descriptions :column="2" border size="small" class="mt-3">
          <el-descriptions-item label="本地版本">
            <span class="num">{{ checkResult.current_version }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="远端版本">
            <span class="num">{{ checkResult.remote_version }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="发布日期">{{ checkResult.released_at || '—' }}</el-descriptions-item>
          <el-descriptions-item label="签名校验">
            <el-tag :type="checkResult.signed ? 'success' : 'warning'" size="small" effect="plain">
              {{ checkResult.signed ? '已通过' : '未签名' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="更新说明" :span="2">{{ checkResult.notes || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="checkResult.images?.length" class="img-list">
          <div v-for="(img, i) in checkResult.images" :key="i" class="img-item">
            <div class="img-item__row">
              <span>镜像文件</span><span class="mono-id">{{ img.file || '—' }}</span>
            </div>
            <div class="img-item__row">
              <span>镜像名:tag</span><span class="mono-id">{{ (img.name || '—') }}:{{ img.tag || '—' }}</span>
            </div>
            <div class="img-item__row">
              <span>sha256</span>
              <span class="mono-id ellipsis" :title="img.sha256">{{ img.sha256 || '—' }}</span>
              <el-button
                link
                type="primary"
                :icon="CopyDocument"
                :disabled="!img.sha256"
                @click="copyText(img.sha256, 'sha256')"
              />
            </div>
          </div>
        </div>
      </template>

      <!-- 步骤 2 -->
      <el-divider content-position="left">步骤 2 · 上传镜像包</el-divider>
      <el-upload
        action="#"
        drag
        :auto-upload="false"
        :show-file-list="false"
        :limit="1"
        accept=".tar,.tar.gz,.zip"
        :on-change="onFileChange"
        class="uploader"
      >
        <el-icon class="uploader__icon"><UploadFilled /></el-icon>
        <div class="uploader__title">把镜像包拖到这里，或点击选择文件</div>
        <div class="uploader__sub">仅支持 .tar / .tar.gz / .zip；需与上面清单声明一致</div>
      </el-upload>

      <div v-if="file" class="file-chip">
        <el-icon><Document /></el-icon>
        <span class="file-chip__name">{{ file.name }}</span>
        <span class="num text-subtle">{{ fileSizeText }}</span>
        <el-button link type="danger" @click="clearFile">移除</el-button>
      </div>

      <div class="actions">
        <el-button
          type="primary"
          :loading="staging"
          :disabled="!file || !manifestText.trim()"
          @click="doStage"
        >
          上传并校验
        </el-button>
        <span class="text-subtle">上传前会先在本地解析清单，签名与 sha256 由后端校验。</span>
      </div>

      <template v-if="stageResult">
        <el-alert type="success" :closable="false" class="mt-3">
          <template #title>{{ stageResult.message }}</template>
        </el-alert>
        <el-descriptions :column="3" border size="small" class="mt-3">
          <el-descriptions-item label="文件">{{ stageResult.staged.name }}</el-descriptions-item>
          <el-descriptions-item label="大小">
            <span class="num">{{ stageResult.staged.megabytes }} MB</span>
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            <span class="num">{{ stageResult.version || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="sha256" :span="3">
            <div class="fingerprint">
              <span class="mono-id ellipsis" :title="stageResult.staged.sha256">{{ stageResult.staged.sha256 }}</span>
              <el-button link type="primary" :icon="CopyDocument" @click="copyText(stageResult.staged.sha256, 'sha256')" />
            </div>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert type="info" :closable="false" class="mt-3">
          <template #title>应用命令（需在服务器上执行）</template>
          <p class="alert-text">
            数据在数据卷里，换镜像不会丢；以下命令需要在服务器上执行，确认无误后再操作。
          </p>
        </el-alert>
        <div class="cmd-block">
          <div class="cmd-block__head">
            <span class="text-subtle">应用命令</span>
            <el-button link type="primary" :icon="CopyDocument" @click="copyText(commandsText, '全部命令')">
              复制全部
            </el-button>
          </div>
          <div v-for="(c, i) in stageResult.commands" :key="i" class="cmd-line">
            <code class="code-block">{{ c }}</code>
            <el-button link type="primary" :icon="CopyDocument" @click="copyText(c, '命令')" />
          </div>
        </div>
      </template>

      <el-divider content-position="left">已暂存升级包</el-divider>
      <el-table :data="upgrade?.staged || []" size="small" border stripe>
        <el-table-column label="名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }"><span class="mono-id">{{ row.name }}</span></template>
        </el-table-column>
        <el-table-column label="大小" width="120" align="right">
          <template #default="{ row }"><span class="num">{{ row.megabytes }} MB</span></template>
        </el-table-column>
        <el-table-column label="时间" width="180">
          <template #default="{ row }"><span class="num">{{ row.staged_at }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="removeStaged(row.name)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">重启应用</el-divider>
      <el-alert type="warning" :closable="false" class="mb-4">
        <template #title>重启只重启服务，不替换镜像</template>
        <p class="alert-text">
          只重启当前镜像里的服务，不会替换镜像；换版本请先 <code>docker load</code> 新镜像；容器 <code>--restart=always</code> 会自动拉起。
        </p>
      </el-alert>
      <div class="actions">
        <el-button type="danger" :loading="restarting" @click="doRestart">重启应用</el-button>
      </div>
    </el-card>

    <!-- D. 防护姿态 -->
    <el-card shadow="never" class="panel">
      <div class="sec-head">
        <div>
          <h3>防护姿态</h3>
          <p class="text-subtle">当前实例的限流、请求签名与防逆向现状（只读）。</p>
        </div>
      </div>

      <el-descriptions :column="2" border size="small" class="mb-4">
        <el-descriptions-item label="普通接口限流">
          <span class="num">{{ rateLimit?.per_min ?? '—' }}</span> 次 / 分钟
        </el-descriptions-item>
        <el-descriptions-item label="登录类限流">
          <span class="num">{{ rateLimit?.login_per_min ?? '—' }}</span> 次 / 分钟
        </el-descriptions-item>
        <el-descriptions-item label="信任反向代理">{{ rateLimit?.trust_proxy ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="追踪 IP 数">
          <span class="num">{{ rateLimit?.tracked_ips ?? '—' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="请求签名模式">
          <el-tag :type="signatureType" size="small" effect="plain">{{ signatureLabel }}</el-tag>
          <span class="text-subtle">（时间窗 {{ signature?.window_seconds ?? '—' }} 秒）</span>
        </el-descriptions-item>
        <el-descriptions-item label="签名是否启用">{{ signature?.enabled ? '已启用' : '未启用' }}</el-descriptions-item>
      </el-descriptions>

      <el-alert v-if="signature?.note" type="info" :closable="false" class="mb-4">
        <template #title>{{ signature.note }}</template>
      </el-alert>

      <el-alert type="warning" :closable="false" class="mb-4">
        <template #title>能力边界说明</template>
        <p class="alert-text">
          前端代码在浏览器里必然可读，混淆只能提高门槛，不能真正防止逆向；接口签名与限流能挡住脚本化抓取与请求重放，但挡不住有资源的定向破解。真正的保护是交付形态（SaaS 自营、代码与数据不出服务器）加上后端加固。
        </p>
      </el-alert>

      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="前端混淆">{{ antiReverse?.frontend_obfuscation || '—' }}</el-descriptions-item>
        <el-descriptions-item label="后端二进制化">{{ antiReverse?.backend_compiled || '—' }}</el-descriptions-item>
        <el-descriptions-item label="说明" :span="2">{{ antiReverse?.note || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- E. 厂商工具用法 -->
    <el-card shadow="never" class="panel">
      <el-collapse v-model="activeCollapse">
        <el-collapse-item name="tools" title="厂商工具用法（仅超级管理员可见）">
          <h4>1. 派生并签发授权码</h4>
          <pre class="code-block">python tools/license_gen.py init</pre>
          <p class="text-subtle">
            把输出的公钥 hex 配置到实例的环境变量 <code>LICENSE_PUBLIC_KEY</code>，再签发授权码：
          </p>
          <pre class="code-block">python tools/license_gen.py issue --customer "客户名" --expires 2027-12-31 --instance &lt;实例指纹&gt;</pre>

          <h4>2. 生成升级清单</h4>
          <p class="text-subtle">需先设置环境变量 <code>UPGRADE_KEY</code>（与实例一致），执行：</p>
          <pre class="code-block">python tools/upgrade_sign.py --version 1.0.4 --file ../release/trademark-market-1.0.4.tar --tag 1.0.4 --notes "更新说明"</pre>
          <p class="text-subtle">把输出的 JSON 粘贴到上方「步骤 1 · 校验升级清单」输入框。</p>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CopyDocument, Document, Refresh, UploadFilled,
} from '@element-plus/icons-vue'
import {
  adminSystemApi,
  type HardeningStatus,
  type UpgradeCheckResult,
} from '@/api'

type VersionInfo = {
  version: string; build_time: string; instance_id: string
  app_name: string; python: string; license_valid: boolean
}
type StageResult = {
  ok: boolean
  staged: { name: string; sha256: string; megabytes: number }
  version: string
  commands: string[]
  message: string
}

const loadingVersion = ref(false)
const loadingStatus = ref(false)
const savingLicense = ref(false)
const clearingLicense = ref(false)
const checking = ref(false)
const staging = ref(false)
const restarting = ref(false)

const versionInfo = ref<VersionInfo | null>(null)
const status = ref<HardeningStatus | null>(null)

const licenseKey = ref('')
const licenseError = ref('')

const manifestText = ref('')
const checkResult = ref<UpgradeCheckResult | null>(null)

const file = ref<File | null>(null)
const stageResult = ref<StageResult | null>(null)

const activeCollapse = ref<string[]>([])

const license = computed(() => status.value?.license)
const upgrade = computed(() => status.value?.upgrade)
const rateLimit = computed(() => status.value?.rate_limit)
const signature = computed(() => status.value?.signature)
const antiReverse = computed(() => status.value?.anti_reverse)

const licenseTag = computed(() => {
  const l = license.value
  if (!l) return { type: 'info' as const, text: '加载中' }
  if (l.valid) return { type: 'success' as const, text: `有效（剩余 ${l.days_left ?? 0} 天）` }
  if (!l.has_key) return { type: 'info' as const, text: '未配置授权码' }
  if (!l.instance_match) return { type: 'warning' as const, text: '指纹不匹配' }
  if (l.days_left !== null && l.days_left < 0) return { type: 'danger' as const, text: '已过期' }
  return { type: 'danger' as const, text: '未通过校验' }
})

const ENFORCE_LABEL: Record<string, string> = {
  warn: '仅提示',
  block_admin_write: '超期后禁后台写操作',
  block_all: '超期后仅保留登录与授权接口',
}
const ENFORCE_HINT: Record<string, string> = {
  warn: '：授权超期只提示，不拦截任何请求。',
  block_admin_write: '：授权超期后，后台的写操作（新增 / 修改 / 删除）会被拦截。',
  block_all: '：授权超期后，除登录与授权接口外，其余接口一律拦截。',
}
const enforceLabel = computed(() => ENFORCE_LABEL[license.value?.enforce || ''] || license.value?.enforce || '—')
const enforceHint = computed(() => ENFORCE_HINT[license.value?.enforce || ''] || '')

const SOC: Record<string, { type: 'success' | 'info' | 'warning' | 'danger'; text: string }> = {
  off: { type: 'info', text: 'off（关闭）' },
  write: { type: 'warning', text: 'write（覆盖写操作）' },
  all: { type: 'success', text: 'all（覆盖全部请求）' },
}
const signatureType = computed(() => SOC[signature.value?.mode || '']?.type || 'info')
const signatureLabel = computed(() => SOC[signature.value?.mode || '']?.text || signature.value?.mode || '—')

const fileSizeText = computed(() => {
  if (!file.value) return ''
  const mb = file.value.size / 1024 / 1024
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${(file.value.size / 1024).toFixed(1)} KB`
})
const commandsText = computed(() => (stageResult.value?.commands || []).join('\n'))

function copyText(text?: string | null, label = '内容') {
  if (!text) return
  navigator.clipboard?.writeText(text)
  ElMessage.success(`已复制${label}`)
}

async function loadVersion() {
  loadingVersion.value = true
  try {
    versionInfo.value = await adminSystemApi.version()
  } finally {
    loadingVersion.value = false
  }
}

async function loadStatus() {
  loadingStatus.value = true
  try {
    status.value = await adminSystemApi.status()
  } finally {
    loadingStatus.value = false
  }
}

async function saveLicense() {
  savingLicense.value = true
  licenseError.value = ''
  try {
    await adminSystemApi.saveLicense(licenseKey.value.trim())
    ElMessage.success('授权码已保存并生效')
    licenseKey.value = ''
    await loadStatus()
    await loadVersion()
  } catch (err: any) {
    licenseError.value = err?.response?.data?.detail || err?.message || '授权码保存失败'
  } finally {
    savingLicense.value = false
  }
}

async function clearLicense() {
  try {
    await ElMessageBox.confirm(
      '清除后本实例将回到「未配置授权码」状态，若当前策略为拦截类，相关接口会被拦下。确定清除吗？',
      '清除授权码',
      { type: 'warning', confirmButtonText: '确认清除', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  clearingLicense.value = true
  try {
    await adminSystemApi.clearLicense()
    ElMessage.success('授权码已清除')
    await loadStatus()
    await loadVersion()
  } finally {
    clearingLicense.value = false
  }
}

function parseManifest(): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(manifestText.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      ElMessage.warning('清单不是合法 JSON')
      return null
    }
    return parsed as Record<string, unknown>
  } catch {
    ElMessage.warning('清单不是合法 JSON')
    return null
  }
}

async function doCheck() {
  const manifest = parseManifest()
  if (!manifest) return
  checking.value = true
  try {
    checkResult.value = await adminSystemApi.upgradeCheck(manifest)
  } finally {
    checking.value = false
  }
}

function onFileChange(f: { raw?: File }) {
  if (!f.raw) return
  const name = f.raw.name.toLowerCase()
  if (!name.endsWith('.tar') && !name.endsWith('.tar.gz') && !name.endsWith('.zip')) {
    ElMessage.warning('仅支持 .tar / .tar.gz / .zip 升级包')
    return
  }
  file.value = f.raw
  stageResult.value = null
}
function clearFile() {
  file.value = null
  stageResult.value = null
}

async function doStage() {
  const manifest = parseManifest()
  if (!manifest || !file.value) return
  staging.value = true
  try {
    stageResult.value = await adminSystemApi.upgradeStage(manifest, file.value)
    ElMessage.success('升级包已校验并暂存')
    file.value = null
    await loadStatus()
  } finally {
    staging.value = false
  }
}

async function removeStaged(name: string) {
  try {
    await ElMessageBox.confirm(`确定删除已暂存的升级包「${name}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }
  await adminSystemApi.deleteStaged(name)
  ElMessage.success('已删除')
  await loadStatus()
}

async function doRestart() {
  try {
    await ElMessageBox.confirm(
      '只重启当前镜像里的服务，不会替换镜像；换版本请先 docker load 新镜像；容器 --restart=always 会自动拉起。确定重启吗？',
      '重启应用',
      { type: 'warning', confirmButtonText: '确认重启', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  restarting.value = true
  try {
    await adminSystemApi.restart()
    ElMessage.success('服务将在 2 秒内重启，请稍后手动刷新页面')
  } finally {
    restarting.value = false
  }
}

onMounted(() => {
  loadVersion()
  loadStatus()
})
</script>

<style scoped>
.system-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
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
.fingerprint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.fingerprint__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
}
.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.feat-tag {
  margin-right: var(--space-2);
}
.mono-input :deep(.el-textarea__inner) {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.7;
}
.alert-text {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  line-height: 1.8;
}
.actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-3);
}
.img-list {
  margin-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.img-item {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
}
.img-item__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-xs);
  line-height: 2;
}
.img-item__row > span:first-child {
  min-width: 84px;
  color: var(--color-muted-fg);
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
  font-size: 40px;
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
.cmd-block {
  margin-top: var(--space-3);
}
.cmd-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.cmd-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.code-block {
  display: block;
  margin: 0;
  padding: var(--space-3) var(--space-4);
  background: var(--color-primary);
  color: #e2e8f0;
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
}
.cmd-line .code-block {
  flex: 1;
}
h4 {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--text-sm);
}
h4:first-child {
  margin-top: 0;
}
code {
  padding: 1px 5px;
  background: var(--color-muted);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.mb-2 {
  margin-bottom: var(--space-2);
}
.mb-4 {
  margin-bottom: var(--space-4);
}
.mt-3 {
  margin-top: var(--space-3);
}
</style>
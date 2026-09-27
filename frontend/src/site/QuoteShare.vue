<template>
  <div class="share-shell">
    <header class="share-header">
      <div class="share-header__inner">
        <router-link to="/" class="site-logo">
          <img v-if="siteCfg?.logo_url" :src="siteCfg.logo_url" :alt="`${siteCfg?.site_name || '商标交易平台'} Logo`" class="site-logo__img" />
          <span v-else class="site-logo__mark">尚</span>
          <span class="site-logo__text">
            <strong>{{ siteCfg?.site_name || '尚标易 · 商标交易平台' }}</strong>
            <span>报价单在线预览</span>
          </span>
        </router-link>
        <el-button link type="primary" @click="$router.push('/trademarks')">浏览全部商标</el-button>
      </div>
    </header>

    <main class="share-main" v-loading="loading">
      <!-- 密码 -->
      <div v-if="needPassword" class="panel-card password-card">
        <h1 class="password-title">{{ title || '商标报价单' }}</h1>
        <p class="text-muted">该报价单设置了访问密码，请输入密码后查看。</p>
        <el-input
          v-model="passwordInput"
          type="password"
          show-password
          size="large"
          placeholder="请输入访问密码"
          @keyup.enter="submitPassword"
        />
        <el-button type="primary" size="large" class="full" :loading="loading" @click="submitPassword">查看报价单</el-button>
      </div>

      <!-- 内容 -->
      <template v-else-if="quote">
        <el-alert
          v-if="expired"
          type="warning"
          :closable="false"
          show-icon
          class="expired-bar"
          title="该报价单已过期，价格可能已变动，请联系客服重新报价"
        />

        <div class="panel-card">
          <div class="quote-head">
            <div>
              <h1 class="quote-title">{{ quote.title }}</h1>
              <p class="quote-meta">
                报价单号 <span class="mono-id">{{ quote.quote_no }}</span>
                <span v-if="quote.customer_name"> · 客户：{{ quote.customer_name }}</span>
              </p>
              <p class="quote-meta text-subtle">
                生成时间：{{ quote.created_at || '—' }} · 有效期至：{{ quote.expire_at || '长期有效' }}
              </p>
            </div>
            <el-button :icon="Download" @click="exportExcel">导出 Excel</el-button>
          </div>

          <div class="table-scroll">
            <table class="quote-table">
              <thead>
                <tr>
                  <th>图样</th>
                  <th>商标名</th>
                  <th>类别</th>
                  <th>注册号</th>
                  <th class="ta-right">原价</th>
                  <th class="ta-right">报价</th>
                  <th class="ta-right">小计</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in quote.items || []" :key="item.trademark_id">
                  <td>
                    <el-image
                      v-if="item.image"
                      :src="item.image"
                      :preview-src-list="[item.image]"
                      preview-teleported
                      fit="contain"
                      :alt="`${item.name} 图样`"
                      class="cell-thumb"
                    />
                    <div v-else class="cell-thumb cell-thumb--empty">暂无图样</div>
                  </td>
                  <td class="cell-name">{{ item.name }}</td>
                  <td>{{ item.category ? `${item.category}类` : '—' }}</td>
                  <td class="mono-id">{{ item.trademark_no || '—' }}</td>
                  <td class="ta-right num">{{ money(item.original_price) }}</td>
                  <td class="ta-right num">
                    <span :class="{ 'quote-strong': item.quote_price !== null }">{{ money(item.quote_price) }}</span>
                  </td>
                  <td class="ta-right num">{{ subtotal(item) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="quote-summary">
            <div class="quote-summary__row">
              <span>原价合计</span>
              <span class="num">¥{{ quote.total_original.toLocaleString() }}</span>
            </div>
            <div class="quote-summary__row">
              <span>{{ discount >= 0 ? '优惠金额' : '加价金额' }}</span>
              <span class="num">{{ discount >= 0 ? '-' : '+' }}¥{{ Math.abs(discount).toLocaleString() }}</span>
            </div>
            <div class="quote-summary__total">
              <span>共 {{ quote.item_count }} 件</span>
              <span>报价合计 <b>¥{{ quote.total_quote.toLocaleString() }}</b></span>
            </div>
          </div>

          <div v-if="quote.remark" class="quote-note">
            <h4>备注</h4>
            <p class="legal-text">{{ quote.remark }}</p>
          </div>
        </div>

        <div class="panel-card contact-card">
          <div>
            <h4>需要协助？请联系客服</h4>
            <p class="contact-wechat">
              客服微信
              <span class="mono-id">{{ siteCfg?.service_wechat || '—' }}</span>
              <el-button v-if="siteCfg?.service_wechat" link type="primary" :icon="CopyDocument" @click="copyWechat">
                复制微信号
              </el-button>
            </p>
            <p class="text-muted">{{ siteCfg?.service_text }}</p>
            <p class="text-muted">服务时间：{{ siteCfg?.service_hours || '—' }} · 电话：{{ siteCfg?.contact_phone || '—' }}</p>
          </div>
          <img v-if="siteCfg?.service_qr" :src="siteCfg.service_qr" alt="客服微信二维码" class="contact-qr" />
          <div v-else class="contact-qr contact-qr--empty">二维码待上传</div>
        </div>
      </template>

      <div v-else-if="!loading" class="empty-state">
        <h3>报价单不存在或链接已失效</h3>
        <p>请联系对接的客服重新发送报价单链接。</p>
        <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
      </div>
    </main>

    <footer class="share-footer">
      <div class="share-footer__inner">
        <span>{{ siteCfg?.copyright }}</span>
        <span>{{ siteCfg?.icp }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument, Download } from '@element-plus/icons-vue'
import { quoteApi, type Quote, type QuoteItem } from '@/api'
import { ensureSiteConfig, siteConfig } from './SiteLayout.vue'

const route = useRoute()

const token = String(route.params.token || '')
const siteCfg = siteConfig
const loading = ref(false)
const needPassword = ref(false)
const title = ref('')
const quote = ref<Quote | null>(null)
const expired = ref(false)
const passwordInput = ref('')
const passwordTried = ref(false)

const discount = computed(() =>
  quote.value ? quote.value.total_original - quote.value.total_quote : 0,
)

function money(v: number | null) {
  return v === null || v === undefined ? '面议' : `¥${v.toLocaleString()}`
}
function subtotal(item: QuoteItem) {
  const v = item.quote_price ?? item.original_price
  return v === null || v === undefined ? '面议' : `¥${v.toLocaleString()}`
}

async function load(password?: string) {
  loading.value = true
  try {
    const res = await quoteApi.share(token, password)
    if (res.need_password) {
      needPassword.value = true
      title.value = res.title || '商标报价单'
      expired.value = !!res.expired
      if (passwordTried.value) ElMessage.error('访问密码不正确')
      return
    }
    needPassword.value = false
    quote.value = res.quote || null
    expired.value = !!res.expired
    if (res.config) siteCfg.value = res.config
  } catch {
    quote.value = null
  } finally {
    loading.value = false
  }
}

function submitPassword() {
  if (!passwordInput.value.trim()) return ElMessage.warning('请输入访问密码')
  passwordTried.value = true
  load(passwordInput.value.trim())
}

function copyWechat() {
  const wx = siteCfg.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

async function exportExcel() {
  if (!quote.value) return
  try {
    await quoteApi.exportExcel(token, passwordInput.value || undefined)
  } catch {
    /* 拦截器已提示 */
  }
}

onMounted(() => {
  ensureSiteConfig()
  load()
})
</script>

<style scoped>
.share-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}
.share-header {
  background: #fff;
  border-bottom: 1px solid var(--color-border);
}
.share-header__inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-3) var(--space-6);
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.site-logo__img {
  height: 34px;
  width: auto;
}
.share-main {
  flex: 1;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.password-card {
  max-width: 440px;
  margin: var(--space-12) auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.password-title {
  margin: 0;
  font-size: var(--text-xl);
}
.full {
  width: 100%;
  height: 46px;
}
.expired-bar {
  margin-bottom: 0;
}
.quote-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-5);
}
.quote-title {
  margin: 0 0 var(--space-2);
  font-size: var(--text-xl);
}
.quote-meta {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.table-scroll {
  overflow-x: auto;
}
.quote-table {
  min-width: 720px;
}
.ta-right {
  text-align: right;
}
.cell-thumb {
  width: 48px;
  height: 48px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.cell-thumb--empty {
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--color-subtle-fg);
}
.cell-name {
  font-weight: 600;
}
.quote-strong {
  color: var(--color-accent);
  font-weight: 700;
}
.quote-note {
  border-top: 1px solid var(--color-border);
  padding: var(--space-5) var(--space-6);
}
.quote-note h4 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-base);
}
.quote-note p {
  margin: 0;
}
.contact-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  flex-wrap: wrap;
}
.contact-card h4 {
  margin: 0 0 var(--space-2);
}
.contact-wechat {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-2);
  font-size: var(--text-md);
}
.contact-card p {
  margin: 0;
}
.contact-qr {
  width: 130px;
  height: 130px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.contact-qr--empty {
  display: grid;
  place-items: center;
  color: var(--color-subtle-fg);
  font-size: var(--text-sm);
}
.share-footer {
  border-top: 1px solid var(--color-border);
  background: #fff;
}
.share-footer__inner {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
@media (max-width: 820px) {
  .share-main {
    padding: var(--space-5) var(--space-4);
  }
  .quote-summary {
    align-items: stretch;
  }
  .quote-summary__row,
  .quote-summary__total {
    justify-content: space-between;
    gap: var(--space-4);
  }
}
</style>
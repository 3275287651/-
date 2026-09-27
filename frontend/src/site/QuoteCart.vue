<template>
  <div class="site-container">
    <h1 class="page-title">报价单</h1>
    <p class="page-sub">把心仪的商标加入报价单，一次性议价并生成专属分享链接</p>

    <template v-if="user.cart.length">
      <div class="panel-card panel-card--flush">
        <div class="table-scroll">
          <table class="quote-table">
            <thead>
              <tr>
                <th>图样</th>
                <th>商标名</th>
                <th>类别</th>
                <th>注册号</th>
                <th class="ta-right">标价</th>
                <th class="ta-right">报价</th>
                <th class="ta-right">小计</th>
                <th class="ta-center">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in user.cart" :key="item.trademark_id">
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
                <td>
                  <router-link :to="`/trademark/${item.trademark_id}`" class="cell-name">{{ item.name }}</router-link>
                </td>
                <td>{{ item.category ? `${item.category}类` : '—' }}</td>
                <td class="mono-id">{{ item.trademark_no || '—' }}</td>
                <td class="ta-right num">{{ item.price !== null ? `¥${item.price.toLocaleString()}` : '面议' }}</td>
                <td class="ta-right">
                  <div v-if="item.price !== null" class="quote-input">
                    <el-input-number
                      :model-value="item.quote_price ?? item.price"
                      :min="0"
                      :step="100"
                      :controls="false"
                      size="small"
                      @change="(v: number | undefined) => setPrice(item.trademark_id, v ?? null)"
                    />
                  </div>
                  <div v-else class="na-cell">
                    <span class="tm-card__price tm-card__price--na">面议</span>
                    <span class="na-hint">该标无公开价，请在备注中说明需求</span>
                  </div>
                </td>
                <td class="ta-right num">{{ subtotalText(item) }}</td>
                <td class="ta-center">
                  <el-button link type="danger" :icon="Delete" @click="removeItem(item.trademark_id, item.name)">
                    移除
                  </el-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="quote-summary">
          <div class="quote-summary__row">
            <span>原价合计</span>
            <span class="num">¥{{ user.cartOriginalTotal.toLocaleString() }}</span>
          </div>
          <div class="quote-summary__row">
            <span>报价合计{{ user.unpricedCount ? '（不含面议商标）' : '' }}</span>
            <span class="num">¥{{ quoteTotal.toLocaleString() }}</span>
          </div>
          <div class="quote-summary__row">
            <span>{{ discount >= 0 ? '优惠金额' : '加价金额' }}</span>
            <span class="num" :class="discount >= 0 ? 'discount' : 'surcharge'">
              ¥{{ Math.abs(discount).toLocaleString() }}
            </span>
          </div>
          <div class="quote-summary__total">
            <span>共 {{ user.cartCount }} 件</span>
            <span>报价合计 <b>¥{{ quoteTotal.toLocaleString() }}</b></span>
          </div>
          <el-alert
            v-if="user.unpricedCount"
            type="info"
            :closable="false"
            class="summary-alert"
            :title="`有 ${user.unpricedCount} 件商标无公开价，合计未包含这些标的金额，请在备注中说明需求`"
          />
          <el-button type="primary" size="large" :icon="Document" class="generate-btn" @click="openCreate">
            生成报价单
          </el-button>
        </div>
      </div>

      <el-button link :icon="Delete" class="clear-all" @click="clearCart">清空报价单</el-button>
    </template>

    <div v-else class="empty-state">
      <h3>报价单还是空的</h3>
      <p>浏览在售商标，把心仪的标加入报价单后即可一键生成报价链接。</p>
      <el-button type="primary" size="large" @click="$router.push('/trademarks')">去挑选商标</el-button>
    </div>

    <!-- 生成报价单 -->
    <el-dialog v-model="createVisible" title="生成报价单" width="480px">
      <el-form label-width="92px" label-position="top">
        <el-form-item label="报价单标题">
          <el-input v-model="form.title" placeholder="如：某公司商标采购报价单" />
        </el-form-item>
        <el-form-item label="客户名称 / 公司">
          <el-input v-model="form.customer_name" placeholder="选填，显示在报价单抬头" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" placeholder="便于客服与您核对" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="可写明议价区间、面议商标的需求等" />
        </el-form-item>
        <el-form-item label="有效期">
          <el-select v-model="form.expire_days" class="full">
            <el-option v-for="d in [3, 7, 15, 30]" :key="d" :label="`${d} 天`" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="访问密码">
          <el-input v-model="form.password" placeholder="留空表示不加密，可直接打开链接" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitQuote">生成</el-button>
      </template>
    </el-dialog>

    <!-- 生成结果 -->
    <el-dialog v-model="resultVisible" title="报价单已生成" width="480px" :close-on-click-modal="false">
      <div v-if="result" class="result-box">
        <p class="result-row">
          <span>分享链接</span>
          <span class="mono-id result-link">{{ shareUrl }}</span>
        </p>
        <div class="result-actions">
          <el-button :icon="CopyDocument" @click="copyLink">复制链接</el-button>
          <el-button :icon="Download" @click="exportExcel">导出 Excel</el-button>
          <el-button type="primary" @click="viewQuote">查看报价单</el-button>
        </div>
        <el-alert
          type="info"
          :closable="false"
          title="该链接可直接发给客户查看；已设置有效期与访问密码时，请一并告知客户。"
        />
      </div>
      <template #footer>
        <el-button @click="closeResult(false)">保留报价单商品</el-button>
        <el-button type="primary" @click="closeResult(true)">清空购物车</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Document, Download } from '@element-plus/icons-vue'
import { quoteApi } from '@/api'
import { useUserStore, type CartItem } from '@/stores/user'
import { ensureSiteConfig, siteConfig } from './SiteLayout.vue'

const router = useRouter()
const user = useUserStore()

const createVisible = ref(false)
const resultVisible = ref(false)
const creating = ref(false)
const result = ref<{ token: string; sharePath: string; password: string } | null>(null)

const form = reactive({
  title: '商标报价单',
  customer_name: '',
  contact_phone: '',
  remark: '',
  expire_days: 7,
  password: '',
})

const quoteTotal = computed(() =>
  user.cart.reduce((sum, i) => sum + (i.quote_price ?? i.price ?? 0), 0),
)
const discount = computed(() => user.cartOriginalTotal - quoteTotal.value)
const shareUrl = computed(() => (result.value ? location.origin + result.value.sharePath : ''))

function subtotalText(item: CartItem) {
  const v = item.quote_price ?? item.price
  return v === null || v === undefined ? '面议' : `¥${v.toLocaleString()}`
}

function setPrice(id: number, value: number | null) {
  user.setQuotePrice(id, value)
}

async function removeItem(id: number, name: string) {
  await ElMessageBox.confirm(`确定把「${name}」移出报价单吗？`, '移除确认', { type: 'warning' })
  user.removeFromCart(id)
  ElMessage.success('已移除')
}

async function clearCart() {
  await ElMessageBox.confirm('确定清空报价单中的全部商标吗？', '清空确认', { type: 'warning' })
  user.clearCart()
  ElMessage.success('已清空')
}

function openCreate() {
  if (!user.isLoggedIn) {
    ElMessage.warning('登录后即可生成报价单')
    router.push({ path: '/login', query: { redirect: '/cart' } })
    return
  }
  form.contact_phone = user.profile?.phone || ''
  form.expire_days = Number(siteConfig.value?.quote_default_days || 7)
  createVisible.value = true
}

async function submitQuote() {
  creating.value = true
  try {
    const res = await quoteApi.create({
      title: form.title || '商标报价单',
      customer_name: form.customer_name || null,
      contact_phone: form.contact_phone || null,
      remark: form.remark || null,
      expire_days: form.expire_days,
      password: form.password || null,
      items: user.cart.map((i) => ({
        trademark_id: i.trademark_id,
        quote_price: i.quote_price ?? i.price,
      })),
    })
    result.value = {
      token: res.quote.token,
      sharePath: res.share_path,
      password: form.password,
    }
    createVisible.value = false
    resultVisible.value = true
  } catch {
    /* 拦截器已提示 */
  } finally {
    creating.value = false
  }
}

function copyLink() {
  if (!shareUrl.value) return
  navigator.clipboard?.writeText(shareUrl.value)
  ElMessage.success('分享链接已复制')
}

async function exportExcel() {
  if (!result.value) return
  try {
    await quoteApi.exportExcel(result.value.token, result.value.password || undefined)
  } catch {
    /* 拦截器已提示 */
  }
}

function viewQuote() {
  if (!result.value) return
  const token = result.value.token
  resultVisible.value = false
  router.push(`/quote/${token}`)
}

function closeResult(clear: boolean) {
  if (clear) user.clearCart()
  resultVisible.value = false
  if (clear) ElMessage.success('已清空购物车')
}

onMounted(ensureSiteConfig)
</script>

<style scoped>
.table-scroll {
  overflow-x: auto;
}
.quote-table {
  min-width: 760px;
}
.ta-right {
  text-align: right;
}
.ta-center {
  text-align: center;
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
  color: var(--color-fg);
  font-weight: 600;
}
.cell-name:hover {
  color: var(--color-accent);
}
.quote-input {
  display: flex;
  justify-content: flex-end;
}
.quote-input :deep(.el-input-number) {
  width: 120px;
}
.na-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.na-hint {
  font-size: 11px;
  color: var(--color-warning);
  max-width: 170px;
  text-align: right;
}
.discount {
  color: var(--color-success);
}
.surcharge {
  color: var(--color-warning);
}
.summary-alert {
  max-width: 420px;
}
.generate-btn {
  margin-top: var(--space-3);
  min-height: 48px;
}
.clear-all {
  margin-top: var(--space-4);
}
.result-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.result-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.result-link {
  word-break: break-all;
  color: var(--color-fg);
}
.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.full {
  width: 100%;
}
@media (max-width: 820px) {
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
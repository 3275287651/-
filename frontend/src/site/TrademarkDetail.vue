<template>
  <div class="site-container" v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: '/trademarks' }">全部商标</el-breadcrumb-item>
      <el-breadcrumb-item>{{ trademark?.name || '商标详情' }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="trademark">
      <div class="detail-layout">
        <!-- 左：图样 -->
        <div class="detail-gallery">
          <template v-if="images.length">
            <el-image
              :src="images[activeImage]"
              :preview-src-list="images"
              :initial-index="activeImage"
              preview-teleported
              fit="contain"
              :alt="`${trademark.name} 商标图样`"
              class="detail-gallery__main"
            />
            <div v-if="images.length > 1" class="detail-gallery__thumbs">
              <button
                v-for="(img, i) in images"
                :key="i"
                type="button"
                class="thumb"
                :class="{ 'thumb--active': i === activeImage }"
                :aria-label="`查看第 ${i + 1} 张图样`"
                @click="activeImage = i"
              >
                <img :src="img" :alt="`${trademark.name} 图样 ${i + 1}`" />
              </button>
            </div>
          </template>
          <div v-else class="detail-gallery__empty">
            <span class="detail-gallery__watermark">{{ trademark.category ? `${trademark.category}类` : '商标' }}</span>
            <span>暂无图样</span>
          </div>
        </div>

        <!-- 右：信息 -->
        <div>
          <div class="detail-head">
            <h1 class="detail-name">{{ trademark.name }}</h1>
            <div class="detail-tags">
              <el-tag :type="statusType" effect="light">{{ trademark.status?.label }}</el-tag>
              <el-tag v-if="trademark.category" type="info" effect="plain">{{ trademark.category }}类</el-tag>
              <el-tag v-if="trademark.is_featured" type="warning" effect="plain">精选</el-tag>
            </div>
          </div>

          <div class="detail-price-box">
            <div>
              <span v-if="trademark.price !== null" class="detail-price">¥{{ trademark.price.toLocaleString() }}</span>
              <span v-else class="detail-price detail-price--na">面议</span>
              <small class="detail-price-note">最终价格以客服确认为准</small>
            </div>
            <span class="detail-views text-subtle">浏览 {{ trademark.view_count }} 次</span>
          </div>

          <div class="detail-actions">
            <el-button type="primary" size="large" :icon="Tickets" @click="addToCart">加入报价单</el-button>
            <el-button size="large" :icon="faved ? StarFilled : Star" @click="onFavorite">
              {{ faved ? '已收藏' : '收藏' }}
            </el-button>
            <el-button size="large" :icon="ChatDotRound" @click="contactVisible = true">联系客服</el-button>
          </div>

          <!-- 字段表（尊重 display_fields） -->
          <div class="field-grid">
            <div v-if="show('trademark_no')" class="field-row field-row--full">
              <div class="field-row__label">注册号</div>
              <div class="field-row__value mono-id id-value">{{ trademark.trademark_no || '—' }}</div>
            </div>
            <div v-if="show('category')" class="field-row">
              <div class="field-row__label">类别</div>
              <div class="field-row__value">{{ trademark.category ? `${trademark.category}类` : '—' }}</div>
            </div>
            <div v-if="show('registration_date')" class="field-row">
              <div class="field-row__label">注册日期</div>
              <div class="field-row__value">{{ trademark.registration_date || '—' }}</div>
            </div>
            <div v-if="show('expiry_date')" class="field-row">
              <div class="field-row__label">有效期至</div>
              <div class="field-row__value">{{ trademark.expiry_date || '—' }}</div>
            </div>
            <div v-if="show('legal_status')" class="field-row">
              <div class="field-row__label">法律状态</div>
              <div class="field-row__value">{{ trademark.legal_status || '—' }}</div>
            </div>
            <div v-if="show('application_count')" class="field-row">
              <div class="field-row__label">申请量</div>
              <div class="field-row__value num">{{ trademark.application_count ?? '—' }}</div>
            </div>
            <div v-if="show('groups')" class="field-row field-row--full">
              <div class="field-row__label">群组</div>
              <div class="field-row__value">{{ trademark.groups || '—' }}</div>
            </div>
            <div v-if="show('products')" class="field-row field-row--full">
              <div class="field-row__label">产品/服务</div>
              <div class="field-row__value legal-text">{{ trademark.products || '—' }}</div>
            </div>
            <div v-if="show('ai_description')" class="field-row field-row--full">
              <div class="field-row__label">AI 释义</div>
              <div class="field-row__value legal-text">{{ trademark.ai_description || '—' }}</div>
            </div>
            <div v-if="show('remark')" class="field-row field-row--full">
              <div class="field-row__label">备注</div>
              <div class="field-row__value">{{ trademark.remark || '—' }}</div>
            </div>
          </div>

          <!-- Excel 自定义列 -->
          <template v-if="extraEntries.length">
            <h3 class="sub-title">补充信息</h3>
            <div class="field-grid">
              <div v-for="[k, v] in extraEntries" :key="k" class="field-row">
                <div class="field-row__label">{{ k }}</div>
                <div class="field-row__value">{{ v ?? '—' }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 同类别推荐 -->
      <template v-if="recommend.length">
        <div class="section-head">
          <h2>同类别推荐</h2>
          <router-link :to="{ path: '/trademarks', query: { category: trademark.category } }">更多同类 →</router-link>
        </div>
        <div class="tm-grid">
          <TrademarkCard v-for="card in recommend" :key="card.id" :card="card" @click="$router.push(`/trademark/${card.id}`)" />
        </div>
      </template>
    </template>

    <div v-else-if="!loading" class="empty-state">
      <h3>商标不存在或已下架</h3>
      <p>该商标可能已被售出或下架，可以浏览其它在售商标。</p>
      <el-button type="primary" @click="$router.push('/trademarks')">浏览全部商标</el-button>
    </div>

    <el-dialog v-model="contactVisible" title="联系客服" width="420px">
      <div class="contact-box">
        <p class="contact-wechat">
          客服微信
          <span class="mono-id">{{ config?.service_wechat || '—' }}</span>
          <el-button v-if="config?.service_wechat" link type="primary" :icon="CopyDocument" @click="copyWechat">
            复制
          </el-button>
        </p>
        <img v-if="config?.service_qr" :src="config.service_qr" alt="客服微信二维码" class="contact-qr" />
        <p class="text-muted">{{ config?.service_text }}</p>
        <p class="text-muted">服务时间：{{ config?.service_hours || '—' }}</p>
      </div>
      <template #footer>
        <el-button @click="contactVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, CopyDocument, Star, StarFilled, Tickets } from '@element-plus/icons-vue'
import { siteApi, type PublicCard, type SiteConfig } from '@/api'
import { useUserStore } from '@/stores/user'
import TrademarkCard from './components/TrademarkCard.vue'

type DetailData = PublicCard & Record<string, any>

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const loading = ref(false)
const trademark = ref<DetailData | null>(null)
const recommend = ref<PublicCard[]>([])
const config = ref<SiteConfig | null>(null)
const activeImage = ref(0)
const contactVisible = ref(false)

const images = computed<string[]>(() => (trademark.value?.images || []).map((i: any) => i.url))
const extraEntries = computed<[string, unknown][]>(() => Object.entries(trademark.value?.extra || {}))
const faved = computed(() => (trademark.value ? user.isFavorite(trademark.value.id) : false))
const STATUS_TYPES: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  on_sale: 'success', reserved: 'warning', sold: 'danger', off_shelf: 'info',
}
const statusType = computed(() => STATUS_TYPES[String(trademark.value?.status?.code || '')] || 'info')

function show(field: string) {
  return (config.value?.display_fields || {})[field] !== false
}

async function load() {
  const id = Number(route.params.id)
  if (!id) return
  loading.value = true
  trademark.value = null
  activeImage.value = 0
  try {
    const res = await siteApi.detail(id)
    trademark.value = res.trademark
    recommend.value = res.recommend
    config.value = res.config
  } finally {
    loading.value = false
  }
}

function addToCart() {
  if (!trademark.value) return
  if (!user.isLoggedIn) {
    ElMessage.warning('登录后即可加入报价单')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  const added = user.addToCart(trademark.value)
  if (added) ElMessage.success('已加入报价单')
  else ElMessage.info('该商标已在报价单中')
}

async function onFavorite() {
  if (!trademark.value) return
  if (!user.isLoggedIn) {
    ElMessage.warning('登录后可收藏')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    const added = await user.toggleFavorite(trademark.value.id)
    ElMessage.success(added ? '已加入收藏' : '已取消收藏')
  } catch {
    /* 拦截器已提示 */
  }
}

function copyWechat() {
  const wx = config.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

watch(() => route.params.id, () => load())
onMounted(load)
</script>

<style scoped>
.crumb {
  margin-bottom: var(--space-5);
}
.detail-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.detail-name {
  margin: 0;
  font-size: var(--text-2xl);
  letter-spacing: -0.3px;
}
.detail-tags {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.detail-price--na {
  font-size: var(--text-2xl);
  color: var(--color-muted-fg);
}
.detail-price-note {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
.detail-views {
  font-size: var(--text-sm);
}
.detail-gallery__main {
  width: 100%;
  height: 320px;
  background: #fff;
}
.detail-gallery__thumbs {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
  margin-top: var(--space-4);
}
.thumb {
  width: 56px;
  height: 56px;
  padding: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
  cursor: pointer;
}
.thumb--active {
  border-color: var(--color-accent);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.detail-gallery__empty {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--color-subtle-fg);
}
.detail-gallery__watermark {
  font-size: 34px;
  font-weight: 700;
  color: var(--color-border-strong);
}
.sub-title {
  margin: var(--space-6) 0 var(--space-3);
  font-size: var(--text-md);
}
.contact-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.contact-wechat {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-md);
  margin: 0;
}
.contact-qr {
  width: 160px;
  height: 160px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}
.contact-box p {
  margin: 0;
}
@media (max-width: 820px) {
  .detail-actions {
    flex-direction: column;
  }
  .detail-actions :deep(.el-button) {
    width: 100%;
    height: 46px;
    margin-left: 0;
  }
}
</style>
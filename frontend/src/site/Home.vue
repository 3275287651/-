<template>
  <div v-loading="loading">
    <!-- Hero -->
    <section class="hero">
      <div class="hero__inner">
        <div>
          <span class="hero__eyebrow">自有货源 · 价格公开 · 过户保障</span>
          <h1>{{ config?.site_subtitle || '精选现成商标 · 即买即用 · 全程代办' }}</h1>
          <p>
            价格公开透明，无隐藏费用。每枚商标均展示官方注册号、类别与法律状态，
            支持多标合议、一键生成专属报价单，转让材料与过户手续全程代办。
          </p>
          <div class="hero__cta">
            <el-button type="primary" size="large" :icon="Search" @click="router.push('/trademarks')">
              浏览全部商标
            </el-button>
            <el-button size="large" :icon="ChatDotRound" class="hero__cta-ghost" @click="contactVisible = true">
              联系客服
            </el-button>
          </div>

          <div class="hero__stats">
            <div class="hero__stat">
              <b class="num">{{ stats.on_sale }}</b>
              <span>在售商标</span>
            </div>
            <div class="hero__stat">
              <b class="num">{{ stats.categories }}</b>
              <span>覆盖类别</span>
            </div>
            <div class="hero__stat">
              <b class="num">{{ stats.total }}</b>
              <span>累计货源</span>
            </div>
          </div>
        </div>

        <aside class="hero__panel">
          <h3>为什么选择我们</h3>
          <div class="hero__panel-list">
            <div v-for="(point, i) in points" :key="point" class="hero__panel-item">
              <i>{{ String(i + 1).padStart(2, '0') }}</i>
              <span>{{ point }}</span>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <div class="site-container">
      <!-- 轮播（无 banner 时整块隐藏） -->
      <el-carousel v-if="banners.length" :height="bannerHeight" class="banner-carousel" :interval="5000">
        <el-carousel-item v-for="(b, i) in banners" :key="i">
          <a
            class="banner-item"
            :href="b.url || undefined"
            :target="b.url ? '_blank' : undefined"
            :rel="b.url ? 'noopener' : undefined"
          >
            <img v-if="b.image_url" :src="b.image_url" :alt="b.title || `横幅 ${i + 1}`" />
            <div v-else class="banner-item__text">
              <strong>{{ b.title }}</strong>
              <span>{{ b.subtitle }}</span>
            </div>
          </a>
        </el-carousel-item>
      </el-carousel>

      <!-- 类别快捷入口 -->
      <template v-if="categories.length">
        <div class="section-head">
          <h2>按类别选标</h2>
          <router-link to="/trademarks">查看全部 →</router-link>
        </div>
        <div class="cat-grid">
          <button
            v-for="c in categories"
            :key="c.value"
            type="button"
            class="cat-card"
            @click="router.push({ path: '/trademarks', query: { category: c.value } })"
          >
            <strong class="num">{{ c.value }}类</strong>
            <span>{{ c.count }} 件在售</span>
          </button>
        </div>
      </template>

      <!-- 精选商标 -->
      <div class="section-head">
        <h2>精选商标</h2>
        <router-link to="/trademarks?featured=1">更多精选 →</router-link>
      </div>
      <div v-if="featured.length" class="tm-grid">
        <TrademarkCard v-for="card in featured" :key="card.id" :card="card" @click="openDetail(card.id)" />
      </div>
      <div v-else class="empty-state">
        <h3>暂无精选商标</h3>
        <p>可先浏览全部在售商标，或联系客服协助选标。</p>
      </div>

      <!-- 最新上架 -->
      <div class="section-head">
        <h2>最新上架</h2>
        <router-link to="/trademarks">全部商标 →</router-link>
      </div>
      <div v-if="latest.length" class="tm-grid">
        <TrademarkCard v-for="card in latest" :key="card.id" :card="card" @click="openDetail(card.id)" />
      </div>
      <div v-else class="empty-state">
        <h3>暂无在售商标</h3>
        <p>新货源正在整理中，欢迎联系客服预留需求。</p>
      </div>

      <!-- 交易流程 -->
      <div class="section-head">
        <h2>交易流程</h2>
        <router-link to="/process">了解详情 →</router-link>
      </div>
      <div class="steps-grid">
        <div v-for="(step, i) in steps" :key="i" class="step-card">
          <div class="step-card__no">{{ String(i + 1).padStart(2, '0') }}</div>
          <h4>{{ step.title }}</h4>
          <p>{{ step.desc }}</p>
        </div>
      </div>
    </div>

    <!-- 客服联系方式 -->
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
        <div v-else class="contact-qr contact-qr--empty">二维码待上传</div>
        <p class="text-muted">{{ config?.service_text }}</p>
        <p class="text-muted">服务时间：{{ config?.service_hours || '—' }}</p>
        <p class="text-muted">咨询电话：{{ config?.contact_phone || '—' }}</p>
      </div>
      <template #footer>
        <el-button @click="contactVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
// 复用 SiteLayout 中请求并缓存的站点配置（首页接口又返回一份，下面直接写入缓存）
import { siteConfig } from './SiteLayout.vue'
</script>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, CopyDocument, Search } from '@element-plus/icons-vue'
import { siteApi, type PublicCard, type SiteConfig } from '@/api'
import TrademarkCard from './components/TrademarkCard.vue'

const router = useRouter()

const loading = ref(false)
const contactVisible = ref(false)
const config = ref<SiteConfig | null>(null)
const banners = ref<SiteConfig['banner']>([])
const featured = ref<PublicCard[]>([])
const latest = ref<PublicCard[]>([])
const categories = ref<{ value: number; count: number }[]>([])
const stats = reactive({ on_sale: 0, total: 0, categories: 0 })
const steps = ref<{ title: string; desc: string }[]>([])

// 轮播高度跟随屏幕：手机 160px / 平板 220px / 桌面 320px
const bannerHeight = ref('320px')
function syncBannerHeight() {
  const w = window.innerWidth
  bannerHeight.value = w <= 620 ? '160px' : w <= 1100 ? '220px' : '320px'
}

const points = [
  '自有货源，无中间加价，价格公开可查',
  '每枚商标展示官方注册号、类别与法律状态',
  '多标合议，一键生成专属报价单便于比价',
  '材料准备、公证与商标局过户全程代办',
]

function openDetail(id: number) {
  router.push(`/trademark/${id}`)
}

function copyWechat() {
  const wx = config.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

onMounted(async () => {
  syncBannerHeight()
  window.addEventListener('resize', syncBannerHeight)
  loading.value = true
  try {
    const res = await siteApi.home()
    config.value = res.config
    siteConfig.value = res.config
    banners.value = res.banners || []
    featured.value = res.featured
    latest.value = res.latest
    categories.value = res.categories
    steps.value = res.config.process_steps || []
    Object.assign(stats, res.stats)
  } finally {
    loading.value = false
  }
})

onUnmounted(() => window.removeEventListener('resize', syncBannerHeight))
</script>

<style scoped>
.hero__cta {
  align-items: center;
}
.hero__cta-ghost {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.35);
  color: #e2e8f0;
}
.hero__cta-ghost:hover {
  border-color: #7dd3fc;
  color: #7dd3fc;
  background: transparent;
}
.banner-carousel {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-6);
}
.banner-item {
  display: block;
  height: 100%;
  width: 100%;
}
.banner-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.banner-item__text {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-3);
  padding: 0 var(--space-10);
  background: var(--color-primary);
  color: #fff;
}
.banner-item__text strong {
  font-size: var(--text-2xl);
}
.banner-item__text span {
  color: #94a3b8;
}
.cat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--space-3);
}
.cat-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  align-items: flex-start;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-card);
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
  font-family: inherit;
}
.cat-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}
.cat-card strong {
  font-size: var(--text-lg);
  color: var(--color-primary);
}
.cat-card span {
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
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
.contact-qr--empty {
  display: grid;
  place-items: center;
  color: var(--color-subtle-fg);
  font-size: var(--text-sm);
}
.contact-box p {
  margin: 0;
}
@media (max-width: 1100px) {
  .cat-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 620px) {
  .cat-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-2);
  }
  .cat-card {
    padding: var(--space-3);
  }
  .banner-item__text {
    padding: 0 var(--space-5);
  }
  .banner-item__text strong {
    font-size: var(--text-lg);
  }
  .banner-item__text span {
    font-size: var(--text-sm);
  }
  .hero__cta {
    width: 100%;
  }
  .hero__cta :deep(.el-button) {
    flex: 1;
    min-width: 0;
    min-height: 46px;
  }
}
</style>
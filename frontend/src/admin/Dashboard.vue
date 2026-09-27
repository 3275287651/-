<template>
  <div v-loading="loading" class="dash">
    <!-- 空数据引导 -->
    <el-card v-if="isEmpty" shadow="never" class="panel">
      <el-empty description="还没有数据，先导入 Excel 建立你的商标库">
        <el-button type="primary" :icon="Upload" @click="$router.push('/admin/trademarks/import')">
          去批量导入
        </el-button>
      </el-empty>
    </el-card>

    <!-- 顶部指标卡 -->
    <section class="metrics" aria-label="核心指标">
      <div class="metric">
        <div class="metric__icon"><el-icon><Goods /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">商标总数</div>
          <div class="metric__value num">{{ n(tm.total) }}</div>
          <div class="metric__sub">在售 <b class="num">{{ n(tm.on_sale) }}</b> · 精选 <b class="num">{{ n(tm.featured) }}</b></div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon metric__icon--success"><el-icon><CircleCheck /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">在售商标</div>
          <div class="metric__value num">{{ n(tm.on_sale) }}</div>
          <div class="metric__sub">下架 <b class="num">{{ n(tm.off_shelf) }}</b> · 已售 <b class="num">{{ n(tm.sold) }}</b></div>
        </div>
      </div>

      <div
        class="metric metric--link"
        role="button"
        tabindex="0"
        @click="$router.push('/admin/trademarks?price_state=unset')"
        @keydown.enter="$router.push('/admin/trademarks?price_state=unset')"
        @keydown.space.prevent="$router.push('/admin/trademarks?price_state=unset')"
      >
        <div class="metric__icon metric__icon--warning"><el-icon><WarningFilled /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">未定价</div>
          <div class="metric__value num">{{ n(tm.unpriced) }}</div>
          <div class="metric__sub">点此查看并补充价格 →</div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon"><el-icon><Picture /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">图样总数</div>
          <div class="metric__value num">{{ n(stats?.images) }}</div>
          <div class="metric__sub">平均每个商标 {{ avgImages }} 张</div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon"><el-icon><User /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">客户数</div>
          <div class="metric__value num">{{ n(customers.total) }}</div>
          <div class="metric__sub">今日新增 <b class="num">{{ n(customers.today) }}</b></div>
        </div>
      </div>

      <div class="metric">
        <div class="metric__icon metric__icon--accent"><el-icon><Tickets /></el-icon></div>
        <div class="metric__body">
          <div class="metric__label">报价单数</div>
          <div class="metric__value num">{{ n(quotes.total) }}</div>
          <div class="metric__sub">今日生成 <b class="num">{{ n(quotes.today) }}</b></div>
        </div>
      </div>
    </section>

    <!-- 图表区 -->
    <section class="grid">
      <!-- 访问趋势 -->
      <el-card shadow="never" class="panel grid__span2">
        <template #header>
          <div class="card-head">
            <div>
              <h3>近 30 天访问趋势</h3>
              <p class="text-subtle">今日 <b class="num">{{ n(visits.today) }}</b> 次 · 近 7 天 <b class="num">{{ n(visits.week) }}</b> 次 · 累计 <b class="num">{{ n(visits.total) }}</b> 次</p>
            </div>
            <el-tag size="small" effect="plain">按天统计</el-tag>
          </div>
        </template>
        <div v-if="hasTrend" class="line-wrap">
          <svg class="line-svg" :viewBox="`0 0 ${chartW} ${chartH}`" role="img" aria-label="近 30 天访问量折线图">
            <!-- 横向网格线 + 刻度 -->
            <g>
              <template v-for="t in yTicks" :key="t.value">
                <line :x1="padL" :x2="chartW - padR" :y1="t.y" :y2="t.y" class="grid-line" />
                <text :x="padL - 8" :y="t.y + 4" class="axis-text" text-anchor="end">{{ t.value }}</text>
              </template>
            </g>
            <!-- 坐标轴基线 -->
            <line :x1="padL" :x2="chartW - padR" :y1="baseY" :y2="baseY" class="axis-line" />
            <line :x1="padL" :x2="padL" :y1="padT" :y2="baseY" class="axis-line" />
            <!-- 面积 + 折线 -->
            <polygon :points="areaPoints" class="line-area" />
            <polyline :points="linePoints" class="line-path" />
            <!-- 数据点（含 hover 提示） -->
            <circle v-for="(p, i) in points" :key="i" :cx="p.x" :cy="p.y" r="2.6" class="line-dot">
              <title>{{ p.day }}：{{ p.count }} 次访问</title>
            </circle>
            <!-- x 轴日期 -->
            <text v-for="(x, i) in xLabels" :key="i" :x="x.x" :y="chartH - 8" class="axis-text" :text-anchor="x.anchor">{{ x.label }}</text>
          </svg>
        </div>
        <el-empty v-else description="近 30 天还没有访问记录" :image-size="70" />
      </el-card>

      <!-- 到期提醒 -->
      <el-card shadow="never" class="panel expire">
        <template #header>
          <div class="card-head">
            <h3>到期提醒</h3>
            <el-icon class="text-subtle"><AlarmClock /></el-icon>
          </div>
        </template>
        <div class="expire__row" @click="$router.push('/admin/expiring')" @keydown.enter="$router.push('/admin/expiring')" tabindex="0" role="button">
          <span class="expire__dot expire__dot--danger" />
          <div class="expire__text">
            <div class="expire__num num">{{ n(expiring.within_30) }}</div>
            <div class="expire__label">30 天内到期</div>
          </div>
        </div>
        <div class="expire__row" @click="$router.push('/admin/expiring')" @keydown.enter="$router.push('/admin/expiring')" tabindex="0" role="button">
          <span class="expire__dot expire__dot--warning" />
          <div class="expire__text">
            <div class="expire__num num">{{ n(expiring.within_90) }}</div>
            <div class="expire__label">90 天内到期</div>
          </div>
        </div>
        <el-button class="full" :icon="AlarmClock" @click="$router.push('/admin/expiring')">查看到期商标</el-button>
        <p class="expire__foot text-subtle">已累计导入 {{ n(stats?.import_batches) }} 个批次</p>
      </el-card>

      <!-- 类别分布 -->
      <el-card shadow="never" class="panel">
        <template #header>
          <div class="card-head">
            <h3>类别分布</h3>
            <span class="text-subtle">共 {{ categories.length }} 个类别</span>
          </div>
        </template>
        <div v-if="categories.length" class="hbars">
          <div v-for="c in categories" :key="c.value" class="hbar">
            <span class="hbar__label">{{ c.label }}</span>
            <span class="hbar__track"><span class="hbar__fill" :style="{ width: barWidth(c.count, maxCategory) }" /></span>
            <span class="hbar__count num">{{ n(c.count) }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无类别数据" :image-size="70" />
      </el-card>

      <!-- 价格区间分布 -->
      <el-card shadow="never" class="panel">
        <template #header>
          <div class="card-head">
            <h3>价格区间分布</h3>
            <span class="text-subtle">未定价 {{ n(tm.unpriced) }} 个</span>
          </div>
        </template>
        <div v-if="hasPrice" class="vbars">
          <div v-for="p in priceDist" :key="p.label" class="vbar">
            <span class="vbar__count num">{{ n(p.count) }}</span>
            <span class="vbar__track">
              <span class="vbar__fill" :style="{ height: barWidth(p.count, maxPrice) }" />
            </span>
            <span class="vbar__label">{{ p.label }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无价格数据，可为商标补价" :image-size="70" />
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  AlarmClock, CircleCheck, Goods, Picture, Tickets, Upload, User, WarningFilled,
} from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const loading = ref(true)
const stats = ref<Record<string, any> | null>(null)

const tm = computed<Record<string, number>>(() => stats.value?.trademarks || {})
const images = computed(() => stats.value?.images || 0)
const customers = computed<Record<string, number>>(() => stats.value?.customers || {})
const quotes = computed<Record<string, number>>(() => stats.value?.quotes || {})
const visits = computed<Record<string, any>>(() => stats.value?.visits || {})
const expiring = computed<Record<string, number>>(() => stats.value?.expiring || {})
const categories = computed<{ label: string; value: number; count: number }[]>(() => stats.value?.categories || [])
const priceDist = computed<{ label: string; count: number }[]>(() => stats.value?.price_dist || [])
const trend = computed<{ day: string; count: number }[]>(() => visits.value.trend || [])

const isEmpty = computed(() =>
  !loading.value && Number(tm.value.total || 0) === 0 && Number(visits.value.total || 0) === 0,
)
const avgImages = computed(() => {
  const t = Number(tm.value.total || 0)
  return t ? (Number(images.value) / t).toFixed(1) : '0'
})
const hasTrend = computed(() => trend.value.some((t) => Number(t.count) > 0))
const hasPrice = computed(() => priceDist.value.some((p) => Number(p.count) > 0))
const maxCategory = computed(() => Math.max(1, ...categories.value.map((c) => Number(c.count) || 0)))
const maxPrice = computed(() => Math.max(1, ...priceDist.value.map((p) => Number(p.count) || 0)))

function n(v: unknown) {
  return Number(v || 0).toLocaleString()
}
function barWidth(v: number, max: number) {
  return `${Math.max(2, (Number(v) || 0) / max * 100)}%`
}

// ── 折线图几何 ──
const chartW = 760
const chartH = 220
const padL = 44
const padR = 16
const padT = 16
const padB = 30
const plotW = chartW - padL - padR
const plotH = chartH - padT - padB
const baseY = chartH - padB
const maxTrend = computed(() => Math.max(1, ...trend.value.map((t) => Number(t.count) || 0)))

const points = computed(() => {
  const len = trend.value.length
  const denom = Math.max(len - 1, 1)
  return trend.value.map((t, i) => ({
    x: padL + (i / denom) * plotW,
    y: padT + plotH - ((Number(t.count) || 0) / maxTrend.value) * plotH,
    day: t.day,
    count: t.count,
  }))
})
const linePoints = computed(() => points.value.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '))
const areaPoints = computed(() => {
  if (!points.value.length) return ''
  const first = points.value[0]
  const last = points.value[points.value.length - 1]
  return `${first.x.toFixed(1)},${baseY} ${linePoints.value} ${last.x.toFixed(1)},${baseY}`
})
const yTicks = computed(() => {
  const max = maxTrend.value
  return [
    { value: max, y: padT },
    { value: Math.round(max / 2), y: padT + plotH / 2 },
    { value: 0, y: baseY },
  ]
})
const xLabels = computed(() => {
  const ps = points.value
  if (ps.length < 2) return []
  const pick = [0, Math.floor(ps.length / 2), ps.length - 1]
  return pick.map((i, idx) => ({
    x: ps[i].x,
    label: String(ps[i].day).slice(5),
    anchor: idx === 0 ? 'start' : idx === ps.length - 1 ? 'end' : 'middle',
  }))
})

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await adminApi.stats()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dash {
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
  grid-template-columns: repeat(6, 1fr);
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
  text-align: left;
  transition: var(--transition);
}
.metric--link {
  cursor: pointer;
  font-family: inherit;
  color: inherit;
}
.metric--link:hover {
  border-color: var(--color-accent);
  background: var(--color-accent-050);
  box-shadow: var(--shadow-sm);
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
.metric__icon--accent {
  background: var(--color-accent);
}
.metric__icon--success {
  background: var(--color-success);
}
.metric__icon--warning {
  background: var(--color-warning);
}
.metric__body {
  min-width: 0;
}
.metric__label {
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
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
.metric__sub b {
  color: var(--color-muted-fg);
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}
.grid__span2 {
  grid-column: span 2;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.card-head h3 {
  margin: 0;
  font-size: var(--text-md);
}
.card-head p {
  margin: 4px 0 0;
  font-size: var(--text-xs);
}

.line-wrap {
  padding: var(--space-1) 0;
}
.line-svg {
  width: 100%;
  height: auto;
  display: block;
}
.grid-line {
  stroke: var(--color-border);
  stroke-width: 1;
  stroke-dasharray: 3 4;
}
.axis-line {
  stroke: var(--color-border-strong);
  stroke-width: 1;
}
.axis-text {
  fill: var(--color-subtle-fg);
  font-size: 11px;
  font-family: var(--font-num);
}
.line-area {
  fill: var(--color-accent);
  opacity: 0.08;
}
.line-path {
  fill: none;
  stroke: var(--color-accent);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.line-dot {
  fill: #fff;
  stroke: var(--color-accent);
  stroke-width: 1.6;
  transition: r 120ms ease;
}
.line-dot:hover {
  r: 5;
  fill: var(--color-accent);
}

.expire__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  margin-bottom: var(--space-3);
  cursor: pointer;
  transition: var(--transition);
}
.expire__row:hover {
  border-color: var(--color-accent);
  background: var(--color-accent-050);
}
.expire__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: none;
}
.expire__dot--danger {
  background: var(--color-destructive);
}
.expire__dot--warning {
  background: var(--color-warning);
}
.expire__num {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.2;
}
.expire__label {
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.expire__foot {
  margin: var(--space-4) 0 0;
  font-size: 11px;
  text-align: center;
}
.full {
  width: 100%;
}

.hbars {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 260px;
  overflow: auto;
}
.hbar {
  display: grid;
  grid-template-columns: 64px 1fr 46px;
  align-items: center;
  gap: var(--space-3);
}
.hbar__label {
  font-size: var(--text-xs);
  color: var(--color-muted-fg);
}
.hbar__track {
  height: 14px;
  background: var(--color-muted);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.hbar__fill {
  display: block;
  height: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-sm);
  transition: width var(--transition);
}
.hbar__count {
  font-size: var(--text-xs);
  text-align: right;
  color: var(--color-primary);
  font-weight: 600;
}

.vbars {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  height: 220px;
  padding-top: var(--space-4);
}
.vbar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  gap: 6px;
}
.vbar__count {
  font-size: var(--text-xs);
  color: var(--color-primary);
  font-weight: 600;
}
.vbar__track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  background: var(--color-bg);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  border-bottom: 1px solid var(--color-border);
}
.vbar__fill {
  display: block;
  width: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: height var(--transition);
}
.vbar__label {
  font-size: 11px;
  color: var(--color-muted-fg);
  text-align: center;
  white-space: nowrap;
}

@media (max-width: 1200px) {
  .metrics {
    grid-template-columns: repeat(3, 1fr);
  }
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid__span2 {
    grid-column: span 2;
  }
}
@media (max-width: 900px) {
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid {
    grid-template-columns: 1fr;
  }
  .grid__span2 {
    grid-column: span 1;
  }
}
</style>
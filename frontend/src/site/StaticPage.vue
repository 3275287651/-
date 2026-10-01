<template>
  <div class="site-container">
    <!-- 关于我们 -->
    <template v-if="page === 'about'">
      <h1 class="page-title">关于我们</h1>
      <p class="page-sub">{{ config?.site_subtitle }}</p>

      <div class="panel-card">
        <h3 class="block-title">公司简介</h3>
        <p class="legal-text intro-text">{{ config?.company_intro || '暂无简介' }}</p>
      </div>

      <div class="panel-card info-card">
        <h3 class="block-title">公司信息</h3>
        <div class="info-row"><span class="info-label">公司地址</span><span>{{ config?.address || '—' }}</span></div>
        <div class="info-row"><span class="info-label">联系电话</span><span class="num">{{ config?.contact_phone || '—' }}</span></div>
        <div class="info-row"><span class="info-label">客服微信</span><span class="mono-id">{{ config?.service_wechat || '—' }}</span></div>
        <div class="info-row"><span class="info-label">服务时间</span><span>{{ config?.service_hours || '—' }}</span></div>
      </div>

      <div class="cta-row">
        <el-button type="primary" size="large" @click="$router.push('/trademarks')">浏览全部商标</el-button>
        <el-button size="large" @click="$router.push('/contact')">联系我们</el-button>
      </div>
    </template>

    <!-- 交易流程 -->
    <template v-else-if="page === 'process'">
      <h1 class="page-title">交易流程</h1>
      <p class="page-sub">自有货源 · 价格公开 · 材料齐全 · 过户全程代办</p>

      <div class="panel-card">
        <ol class="timeline">
          <li v-for="(step, i) in steps" :key="i" class="timeline__item">
            <span class="timeline__no num">{{ String(i + 1).padStart(2, '0') }}</span>
            <div class="timeline__body">
              <h4>{{ step.title }}</h4>
              <p>{{ step.desc }}</p>
            </div>
          </li>
        </ol>
      </div>

      <h2 class="faq-head">常见问题</h2>
      <div class="panel-card">
        <el-collapse>
          <el-collapse-item v-for="(f, i) in faqs" :key="i" :title="f.q" :name="i">
            <p class="faq-a legal-text">{{ f.a }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div class="cta-row">
        <el-button type="primary" size="large" @click="$router.push('/trademarks')">开始挑选商标</el-button>
        <el-button size="large" @click="$router.push('/contact')">联系客服咨询</el-button>
      </div>
    </template>

    <!-- 联系我们 -->
    <template v-else>
      <h1 class="page-title">联系我们</h1>
      <p class="page-sub">添加客服微信，1 对 1 协助选标、议价与过户</p>

      <div class="contact-layout">
        <div class="panel-card contact-main">
          <span class="contact-label">客服微信</span>
          <div class="contact-wx">
            <strong class="mono-id">{{ config?.service_wechat || '—' }}</strong>
            <el-button v-if="config?.service_wechat" type="primary" :icon="CopyDocument" @click="copyWechat">
              复制微信号
            </el-button>
          </div>
          <p class="text-muted">{{ config?.service_text }}</p>
          <div class="info-row"><span class="info-label">服务时间</span><span>{{ config?.service_hours || '—' }}</span></div>
          <div class="info-row"><span class="info-label">咨询电话</span><span class="num">{{ config?.contact_phone || '—' }}</span></div>
          <div class="info-row"><span class="info-label">公司地址</span><span>{{ config?.address || '—' }}</span></div>
        </div>

        <div class="panel-card contact-aside">
          <img v-if="config?.service_qr" :src="config.service_qr" alt="客服微信二维码" class="contact-qr" />
          <div v-else class="contact-qr contact-qr--empty">二维码待上传</div>
          <span class="text-subtle">扫码添加客服微信</span>
        </div>
      </div>

      <div class="panel-card map-card">
        <div class="map-placeholder">
          <el-icon class="map-icon"><Location /></el-icon>
          <strong>{{ config?.address || '公司地址' }}</strong>
          <span class="text-subtle">如需到访，请提前联系客服预约</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Location } from '@element-plus/icons-vue'
import { ensureSiteConfig, siteConfig } from './SiteLayout.vue'

defineProps<{ page: 'about' | 'process' | 'contact' }>()

const config = siteConfig
const steps = computed(() => config.value?.process_steps || [])

const faqs = [
  {
    q: '现成商标转让一般需要多久？',
    a: '常规流程为：双方确认标的情况并签订转让合同后，先办理转让公证，再向国家知识产权局提交转让申请。公证通常 3-5 个工作日，商标局审查约 4-6 个月，整体约 5-7 个月完成过户。若走加急通道或标的材料齐全，时间可相应缩短。',
  },
  {
    q: '需要准备哪些材料？',
    a: '受让方（买方）需提供营业执照副本复印件（企业）或身份证复印件（个人）并加盖公章/签字；我方可提供商标注册证、转让申请书、委托书等标准文书，并协助完成公证与提交。若买方为境外主体，需另行准备主体资格证明的翻译与公证认证文件。',
  },
  {
    q: '可以先使用商标、后办理过户吗？',
    a: '可以。签订合同并支付首款后，可通过《商标使用授权书》获得授权，先行合法使用该商标；过户手续同步推进。授权期间的使用范围以合同约定为准，不影响商标的最终归属。',
  },
  {
    q: '费用能否分期支付？',
    a: '支持分期。常见方式为签订合同时支付定金，公证完成支付第二期，商标局受理或核准后再支付尾款。具体比例可与客服协商，并在合同中明确约定各期付款节点与对应的退款条件。',
  },
  {
    q: '报价是否包含商标局官费？',
    a: '平台展示的价格为商标本身的转让报价，商标局官费（转让规费）需按官方标准另计，由买方承担。若委托我方代办，代办服务费与官费会在合同中逐项列明，价格公开透明，无隐藏费用。',
  },
  {
    q: '如果过户失败怎么办？',
    a: '我方会在签约前对商标的法律状态、有效期与权利归属做尽职核查，尽可能规避风险。若因我方原因导致转让无法完成，将按合同约定全额退还已收款项；因买方材料不合规等买方原因导致失败的，退还扣除公证等已实际发生费用后的余额。',
  },
]

function copyWechat() {
  const wx = config.value?.service_wechat
  if (!wx) return
  navigator.clipboard?.writeText(wx)
  ElMessage.success(`已复制微信号：${wx}`)
}

onMounted(ensureSiteConfig)
</script>

<style scoped>
.block-title {
  margin: 0 0 var(--space-3);
  font-size: var(--text-md);
}
.intro-text {
  margin: 0;
}
.info-card {
  margin-top: var(--space-5);
}
.info-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}
.info-row:last-child {
  border-bottom: none;
}
.info-label {
  width: 84px;
  flex: none;
  color: var(--color-muted-fg);
}
.cta-row {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-8);
}
.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}
.timeline__item {
  display: flex;
  gap: var(--space-5);
  padding: var(--space-4) 0 var(--space-6);
  border-left: 2px solid var(--color-border);
  padding-left: var(--space-6);
  margin-left: var(--space-4);
  position: relative;
}
.timeline__item:last-child {
  padding-bottom: var(--space-2);
}
.timeline__item::before {
  content: '';
  position: absolute;
  left: -7px;
  top: 24px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid #fff;
}
.timeline__no {
  font-family: var(--font-num);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-border-strong);
  line-height: 1.2;
}
.timeline__body h4 {
  margin: 0 0 var(--space-1);
  font-size: var(--text-md);
}
.timeline__body p {
  margin: 0;
  color: var(--color-muted-fg);
  font-size: var(--text-sm);
  line-height: 1.8;
}
.faq-head {
  margin: var(--space-10) 0 var(--space-4);
  font-size: var(--text-xl);
}
.faq-a {
  margin: 0;
  padding: 0 0 var(--space-3);
}
.contact-layout {
  display: grid;
  grid-template-columns: 1.6fr 0.9fr;
  gap: var(--space-5);
  align-items: flex-start;
}
.contact-label {
  color: var(--color-muted-fg);
  font-size: var(--text-sm);
}
.contact-wx {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin: var(--space-2) 0 var(--space-3);
}
.contact-wx strong {
  font-size: var(--text-2xl);
  color: var(--color-primary);
  letter-spacing: 0.5px;
}
.contact-aside {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}
.contact-qr {
  width: 180px;
  height: 180px;
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
.map-card {
  margin-top: var(--space-5);
  padding: 0;
  overflow: hidden;
}
.map-placeholder {
  height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background:
    repeating-linear-gradient(45deg, #f1f5f9 0 14px, #e8eef5 14px 28px);
  color: var(--color-muted-fg);
}
.map-icon {
  font-size: 30px;
  color: var(--color-accent);
}
.contact-main p {
  margin: 0 0 var(--space-4);
}
@media (max-width: 820px) {
  .contact-layout {
    grid-template-columns: 1fr;
  }
  .cta-row :deep(.el-button) {
    flex: 1;
    min-height: 46px;
  }
}
@media (max-width: 620px) {
  .contact-wx strong {
    font-size: var(--text-xl);
    word-break: break-all;
  }
  .contact-qr {
    width: 150px;
    height: 150px;
  }
  .map-placeholder {
    height: 170px;
  }
  .timeline__item {
    gap: var(--space-3);
    padding-left: var(--space-4);
    margin-left: var(--space-2);
  }
  .info-row {
    gap: var(--space-3);
  }
}
</style>
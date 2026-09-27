<template>
  <article class="tm-card" tabindex="0" role="link" :aria-label="`查看商标 ${card.name} 详情`" @click="$emit('click')" @keyup.enter="$emit('click')">
    <div class="tm-card__img">
      <img v-if="card.image" :src="card.image" :alt="`${card.name} 商标图样`" loading="lazy" />
      <div v-else class="tm-card__noimg">
        <span class="tm-card__watermark">{{ card.category ? `${card.category}类` : '商标' }}</span>
        <span>暂无图样</span>
      </div>

      <span v-if="card.category" class="tm-card__badge">{{ card.category }}类</span>
      <span v-if="card.is_featured" class="tm-card__badge tm-card__badge--featured">精选</span>

      <button
        type="button"
        class="tm-card__fav"
        :class="{ 'tm-card__fav--on': faved }"
        :aria-label="faved ? '取消收藏' : '收藏该商标'"
        :aria-pressed="faved"
        @click.stop="onFavorite"
      >
        <el-icon><StarFilled v-if="faved" /><Star v-else /></el-icon>
      </button>
    </div>

    <div class="tm-card__body">
      <h3 class="tm-card__name" :title="card.name">{{ card.name }}</h3>
      <div class="tm-card__meta">
        <span>注册号 <span class="mono-id">{{ card.trademark_no || '—' }}</span></span>
        <span v-if="card.registration_date">注册 {{ card.registration_date }}</span>
      </div>
      <div class="tm-card__foot">
        <span v-if="card.price !== null" class="tm-card__price">{{ card.price_text }}<small>起</small></span>
        <span v-else class="tm-card__price tm-card__price--na">面议</span>
        <span class="tm-card__more">查看详情</span>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Star, StarFilled } from '@element-plus/icons-vue'
import type { PublicCard } from '@/api'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ card: PublicCard }>()
defineEmits<{ click: [] }>()

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const faved = computed(() => user.isFavorite(props.card.id))

async function onFavorite() {
  if (!user.isLoggedIn) {
    ElMessage.warning('登录后可收藏')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    const added = await user.toggleFavorite(props.card.id)
    ElMessage.success(added ? '已加入收藏' : '已取消收藏')
  } catch {
    /* 错误提示由 http 拦截器统一处理 */
  }
}
</script>

<style scoped>
.tm-card__noimg {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--color-subtle-fg);
  font-size: var(--text-xs);
  background:
    repeating-linear-gradient(45deg, #f8fafc 0 10px, #f1f5f9 10px 20px);
}
.tm-card__watermark {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-border-strong);
  letter-spacing: 1px;
}
.tm-card__fav {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  z-index: 2;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-subtle-fg);
  cursor: pointer;
  transition: var(--transition);
}
/* 精选角标默认贴右上角，会与收藏按钮重叠，这里让它坐落在收藏按钮左侧 */
.tm-card__badge--featured {
  right: calc(var(--space-2) + 36px);
}
.tm-card__fav:hover {
  color: #b45309;
  border-color: #b45309;
}
.tm-card__fav--on {
  color: #b45309;
  border-color: #b45309;
}
.tm-card__more {
  font-size: var(--text-xs);
  color: var(--color-accent);
  padding-bottom: 2px;
}
</style>
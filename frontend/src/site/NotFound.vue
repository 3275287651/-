<template>
  <div class="site-shell">
    <main class="notfound">
      <div class="notfound__box">
        <div class="notfound__code num">404</div>
        <h1>页面不存在或已下架</h1>
        <p>你访问的页面可能已被移除、更名，或链接有误。</p>
        <div class="notfound__actions">
          <el-button type="primary" size="large" @click="$router.push('/')">返回首页</el-button>
          <el-button size="large" @click="$router.push('/trademarks')">浏览商标</el-button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.notfound {
  flex: 1;
  display: grid;
  place-items: center;
  padding: var(--space-16) var(--space-6);
}
.notfound__box {
  text-align: center;
  max-width: 460px;
}
.notfound__code {
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
  font-size: 96px;
  font-weight: 700;
  line-height: 1;
  color: var(--color-primary);
  letter-spacing: -4px;
}
.notfound__box h1 {
  margin: var(--space-4) 0 var(--space-2);
  font-size: var(--text-xl);
}
.notfound__box p {
  margin: 0 0 var(--space-8);
  color: var(--color-muted-fg);
}
.notfound__actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}
@media (max-width: 820px) {
  .notfound__actions :deep(.el-button) {
    min-height: 46px;
  }
}
</style>
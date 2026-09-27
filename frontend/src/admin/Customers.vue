<template>
  <div class="cust-page">
    <el-card shadow="never" class="panel">
      <div class="filter-bar">
        <el-input
          v-model="q"
          placeholder="按手机号搜索"
          clearable
          class="filter-search"
          :prefix-icon="Search"
          @keyup.enter="reload(1)"
          @clear="reload(1)"
        />
        <el-button type="primary" :icon="Search" @click="reload(1)">搜索</el-button>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ total }}</b> 位客户</span>
        <span class="text-subtle">· 状态为「已停用」的客户将无法登录前台</span>
      </div>

      <el-table v-loading="loading" :data="rows" size="small" border stripe>
        <el-table-column type="index" label="序号" width="62" align="center" />
        <el-table-column label="手机号" width="150">
          <template #default="{ row }"><span class="mono-id">{{ row.phone || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="昵称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.nickname || '—' }}</template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="收藏数" width="90" align="right">
          <template #default="{ row }"><span class="num">{{ row.fav_count }}</span></template>
        </el-table-column>
        <el-table-column label="报价单数" width="100" align="right">
          <template #default="{ row }"><span class="num">{{ row.quote_count }}</span></template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="130">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="150">
          <template #default="{ row }">{{ row.last_login_at || '从未登录' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 1" type="success" size="small" effect="light">正常</el-tag>
            <el-tag v-else type="info" size="small" effect="light">已停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 1"
              link
              type="danger"
              size="small"
              @click="toggleStatus(row, 0)"
            >
              停用
            </el-button>
            <el-button v-else link type="primary" size="small" @click="toggleStatus(row, 1)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="load"
          @size-change="reload(1)"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api'

const loading = ref(false)
const rows = ref<Record<string, any>[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const q = ref('')

async function load() {
  loading.value = true
  try {
    const res = await adminApi.customers({ page: page.value, page_size: pageSize.value, q: q.value || undefined })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}
function reload(p = page.value) {
  page.value = p
  load()
}

async function toggleStatus(row: Record<string, any>, status: number) {
  if (status === 0) {
    try {
      await ElMessageBox.confirm(
        `停用后客户「${row.nickname || row.phone}」将无法登录前台，已生成的报价单不受影响。确定停用吗？`,
        '停用确认',
        { type: 'warning', confirmButtonText: '确认停用', confirmButtonClass: 'el-button--danger' },
      )
    } catch {
      return
    }
  }
  await adminApi.updateCustomer(row.id, { status })
  ElMessage.success(status === 1 ? '已启用该客户' : '已停用该客户')
  load()
}

onMounted(load)
</script>

<style scoped>
.cust-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.filter-search {
  width: 260px;
}
.filter-spacer {
  flex: 1;
}
.table-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
}
</style>
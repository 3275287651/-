<template>
  <div class="admin-page">
    <el-card shadow="never" class="panel">
      <div class="toolbar">
        <div>
          <h3>运营账户</h3>
          <p class="text-subtle">超级管理员拥有全部权限；普通运营不可访问网站配置、账户管理与操作日志。</p>
        </div>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增账户</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="panel">
      <div class="table-meta">
        <span>共 <b class="num">{{ rows.length }}</b> 个账户</span>
        <span class="text-subtle">· 不能删除或变更当前登录账户自己的角色与状态</span>
      </div>

      <el-table v-loading="loading" :data="rows" size="small" border stripe>
        <el-table-column label="用户名" width="140">
          <template #default="{ row }">
            <span class="mono-id">{{ row.username }}</span>
            <el-tag v-if="row.id === myId" size="small" effect="plain" class="self-tag">我</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" min-width="130" show-overflow-tooltip />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" type="warning" size="small" effect="light">超级管理员</el-tag>
            <el-tag v-else type="info" size="small" effect="light">普通运营</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 1" type="success" size="small" effect="light">正常</el-tag>
            <el-tag v-else type="info" size="small" effect="light">已停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">{{ row.last_login_at || '从未登录' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="130">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.id === myId"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="dialog" :title="isEdit ? '编辑账户' : '新增账户'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="至少 3 位，创建后不可修改" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="真实姓名或称呼" />
        </el-form-item>
        <el-form-item :label="isEdit ? '重置密码' : '密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEdit ? '留空表示不修改密码' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role" :disabled="isEdit && isSelf">
            <el-radio value="operator">普通运营</el-radio>
            <el-radio value="admin">超级管理员</el-radio>
          </el-radio-group>
          <div v-if="isEdit && isSelf" class="hint">不能修改自己的角色</div>
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-switch
            v-model="form.status"
            :disabled="isSelf"
            active-text="正常"
            inactive-text="停用"
            :active-value="1"
            :inactive-value="0"
          />
          <div v-if="isSelf" class="hint">不能停用自己的账户</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">{{ isEdit ? '保存修改' : '创建账户' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { adminApi } from '@/api'
import { useAdminStore } from '@/stores/auth'

const auth = useAdminStore()
const myId = computed(() => auth.profile?.id)

const loading = ref(false)
const saving = ref(false)
const rows = ref<Record<string, any>[]>([])
const dialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  name: '',
  password: '',
  role: 'operator',
  status: 1 as number,
})

const isSelf = computed(() => isEdit.value && editId.value === myId.value)

const rules = {
  username: [
    { required: true, message: '请填写用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 位', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请填写姓名', trigger: 'blur' }],
  password: [
    {
      validator: (_r: unknown, value: string, cb: (e?: Error) => void) => {
        if (!isEdit.value && !value) return cb(new Error('请填写密码'))
        if (value && value.length < 6) return cb(new Error('密码至少 6 位'))
        return cb()
      },
      trigger: 'blur',
    },
  ],
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.admins()
    rows.value = res.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, { username: '', name: '', password: '', role: 'operator', status: 1 })
  dialog.value = true
}
function openEdit(row: Record<string, any>) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    name: row.name || '',
    password: '',
    role: row.role === 'admin' ? 'admin' : 'operator',
    status: row.status === 1 ? 1 : 0,
  })
  dialog.value = true
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editId.value !== null) {
      const payload: Record<string, unknown> = { name: form.name.trim() }
      if (form.password) payload.password = form.password
      payload.role = form.role
      payload.status = form.status
      await adminApi.updateAdmin(editId.value, payload)
      ElMessage.success('账户已更新')
    } else {
      await adminApi.createAdmin({
        username: form.username.trim(),
        password: form.password,
        name: form.name.trim(),
        role: form.role,
      })
      ElMessage.success('账户已创建')
    }
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: Record<string, any>) {
  try {
    await ElMessageBox.confirm(
      `删除账户「${row.name || row.username}」后该账号将立即失效，且不可恢复。确定删除吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  await adminApi.deleteAdmin(row.id)
  ElMessage.success('账户已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.toolbar h3 {
  margin: 0 0 4px;
  font-size: var(--text-md);
}
.toolbar p {
  margin: 0;
  font-size: var(--text-xs);
}
.table-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-muted-fg);
}
.self-tag {
  margin-left: 6px;
  transform: scale(0.85);
}
.hint {
  font-size: var(--text-xs);
  color: var(--color-subtle-fg);
}
</style>
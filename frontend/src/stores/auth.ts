import { defineStore } from 'pinia'
import { authApi } from '@/api'

interface AdminProfile {
  id: number
  username: string
  name: string
  role: string
}

function readProfile(): AdminProfile | null {
  try {
    return JSON.parse(localStorage.getItem('admin_profile') || 'null')
  } catch {
    return null
  }
}

export const useAdminStore = defineStore('admin', {
  state: () => ({
    token: localStorage.getItem('admin_token') || '',
    profile: readProfile() as AdminProfile | null,
    loading: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isSuper: (s) => s.profile?.role === 'admin',
    displayName: (s) => s.profile?.name || s.profile?.username || '运营',
  },
  actions: {
    async login(username: string, password: string) {
      this.loading = true
      try {
        const res = await authApi.adminLogin(username, password)
        this.token = res.token
        this.profile = res.admin
        localStorage.setItem('admin_token', res.token)
        localStorage.setItem('admin_profile', JSON.stringify(res.admin))
        return res.admin
      } finally {
        this.loading = false
      }
    },
    logout() {
      this.token = ''
      this.profile = null
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_profile')
    },
  },
})
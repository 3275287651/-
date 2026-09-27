import { defineStore } from 'pinia'
import { authApi, siteApi, type PublicCard } from '@/api'

export interface CartItem {
  trademark_id: number
  name: string
  category: number | null
  trademark_no: string | null
  price: number | null
  quote_price: number | null
  image: string | null
}

const CART_KEY = 'quote_cart'

function readCart(): CartItem[] {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY) || '[]')
  } catch {
    return []
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('user_token') || '',
    profile: JSON.parse(localStorage.getItem('user_profile') || 'null') as
      { id: number; phone: string; nickname: string } | null,
    cart: readCart(),
    favoriteIds: [] as number[],
    loading: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    cartCount: (s) => s.cart.length,
    cartTotal: (s) => s.cart.reduce((sum, i) => sum + (i.quote_price ?? i.price ?? 0), 0),
    cartOriginalTotal: (s) => s.cart.reduce((sum, i) => sum + (i.price ?? 0), 0),
    unpricedCount: (s) => s.cart.filter((i) => i.price === null).length,
  },
  actions: {
    persistCart() {
      localStorage.setItem(CART_KEY, JSON.stringify(this.cart))
    },
    async login(phone: string, password: string) {
      const res = await authApi.userLogin(phone, password)
      this.token = res.token
      this.profile = res.user
      localStorage.setItem('user_token', res.token)
      localStorage.setItem('user_profile', JSON.stringify(res.user))
      await this.loadFavorites()
    },
    async register(payload: Record<string, unknown>) {
      const res = await authApi.userRegister(payload)
      this.token = res.token
      this.profile = res.user
      localStorage.setItem('user_token', res.token)
      localStorage.setItem('user_profile', JSON.stringify(res.user))
    },
    logout() {
      this.token = ''
      this.profile = null
      this.favoriteIds = []
      localStorage.removeItem('user_token')
      localStorage.removeItem('user_profile')
    },
    addToCart(item: PublicCard | Record<string, any>) {
      const id = (item as any).id ?? (item as any).trademark_id
      if (this.cart.some((i) => i.trademark_id === id)) return false
      this.cart.push({
        trademark_id: id,
        name: (item as any).name,
        category: (item as any).category ?? null,
        trademark_no: (item as any).trademark_no ?? null,
        price: (item as any).price ?? null,
        quote_price: (item as any).price ?? null,
        image: (item as any).image ?? (item as any).images?.[0]?.url ?? null,
      })
      this.persistCart()
      return true
    },
    removeFromCart(id: number) {
      this.cart = this.cart.filter((i) => i.trademark_id !== id)
      this.persistCart()
    },
    clearCart() {
      this.cart = []
      this.persistCart()
    },
    setQuotePrice(id: number, price: number | null) {
      const item = this.cart.find((i) => i.trademark_id === id)
      if (item) {
        item.quote_price = price
        this.persistCart()
      }
    },
    async loadFavorites() {
      if (!this.token) {
        this.favoriteIds = []
        return
      }
      try {
        const res = await siteApi.favoriteIds()
        this.favoriteIds = res.ids
      } catch {
        this.favoriteIds = []
      }
    },
    async toggleFavorite(id: number) {
      if (this.favoriteIds.includes(id)) {
        await siteApi.removeFavorite(id)
        this.favoriteIds = this.favoriteIds.filter((x) => x !== id)
        return false
      }
      await siteApi.addFavorite(id)
      this.favoriteIds = [...this.favoriteIds, id]
      return true
    },
    isFavorite(id: number) {
      return this.favoriteIds.includes(id)
    },
  },
})
import { defineStore } from 'pinia'
import { authService } from '../services/authService'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthenticated: false
  }),

  actions: {
    async checkToken() {
      try {
        const u = await authService.checkToken()
        if (u && u.user) {
          this.user = u.user
          this.isAuthenticated = true
          return u.user
        }
        this.logout()
        return null
      } catch (error) {
        this.logout()
        throw error
      }
    },

    logout() {
      this.user = null
      this.isAuthenticated = false
      authService.logout()
    },

    setUser(user) {
      this.user = user
      this.isAuthenticated = !!user
    }
  }
})


import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
  state: () => ({
    loading: false,
    isSidebarCollapsed: false,
    selectedPortfolioId: null
  }),

  getters: {
    isLoading: (state) => state.loading
  },

  actions: {
    setLoading(value) {
      this.loading = value
    },

    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed
    },

    setSelectedPortfolioId(id) {
      this.selectedPortfolioId = id
      if (id) {
        localStorage.setItem('selectedPortfolioId', id.toString())
      } else {
        localStorage.removeItem('selectedPortfolioId')
      }
    },

    initSelectedPortfolioId(portfolios) {
      // Инициализация из localStorage или выбор первого портфеля
      const stored = localStorage.getItem('selectedPortfolioId')
      const storedId = stored ? Number(stored) : null
      
      if (portfolios.length > 0) {
        const exists = portfolios.find(p => p.id === storedId)
        if (storedId && exists) {
          this.selectedPortfolioId = storedId
        } else {
          this.selectedPortfolioId = portfolios[0].id
          this.setSelectedPortfolioId(portfolios[0].id)
        }
      }
    }
  }
})


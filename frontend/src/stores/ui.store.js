import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
  state: () => ({
    loading: false,
    isSidebarCollapsed: false,
    isMobileMenuOpen: false,
    selectedPortfolioId: null,
    expandedPortfolios: [],
    showSoldAssets: false,
  }),

  persist: [
    'selectedPortfolioId',
    'isSidebarCollapsed',
    'expandedPortfolios',
    'showSoldAssets',
  ],

  persistLegacyKeys: {
    selectedPortfolioId: 'selectedPortfolioId',
    expandedPortfolios: 'expandedPortfolios',
    showSoldAssets: 'showSoldAssets',
  },

  getters: {
    isLoading: (state) => state.loading,
    isPortfolioExpanded: (state) => (id) => state.expandedPortfolios.includes(id),
  },

  actions: {
    setLoading(value) {
      this.loading = value
    },

    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed
    },

    setMobileMenuOpen(value) {
      this.isMobileMenuOpen = !!value
    },

    setSelectedPortfolioId(id) {
      this.selectedPortfolioId = id
    },

    initSelectedPortfolioId(portfolios) {
      const storedId = this.selectedPortfolioId
      if (portfolios.length > 0) {
        const exists = portfolios.find(p => p.id === storedId)
        if (!storedId || !exists) {
          this.selectedPortfolioId = portfolios[0].id
        }
      }
    },

    togglePortfolio(id) {
      const idx = this.expandedPortfolios.indexOf(id)
      if (idx === -1) {
        this.expandedPortfolios.push(id)
      } else {
        this.expandedPortfolios.splice(idx, 1)
      }
    },

    expandPortfolio(id) {
      if (!this.expandedPortfolios.includes(id)) {
        this.expandedPortfolios.push(id)
      }
    },

    collapseAllPortfolios() {
      this.expandedPortfolios = []
    },

    setShowSoldAssets(value) {
      this.showSoldAssets = value
    },
  }
})

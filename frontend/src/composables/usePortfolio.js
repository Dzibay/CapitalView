/**
 * Композабл для работы с портфелями
 * Централизует логику работы с портфелями и их иерархией
 */
import { computed, ref } from 'vue';

export function usePortfolio(dashboardData, selectedPortfolioId) {
  const portfolios = computed(() => dashboardData.value?.data?.portfolios ?? []);

  const selectedPortfolio = computed(() => {
    if (!selectedPortfolioId.value) return null;
    return portfolios.value.find(p => p.id === selectedPortfolioId.value) || null;
  });

  /**
   * Собирает все ID портфеля и его дочерних портфелей
   */
  function collectPortfolioIds(portfolio, allPortfolios) {
    let ids = [portfolio.id];
    const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id);

    for (const child of children) {
      ids = ids.concat(collectPortfolioIds(child, allPortfolios));
    }

    return ids;
  }

  /**
   * Собирает все активы портфеля и его дочерних портфелей
   */
  function collectAssets(portfolio, allPortfolios) {
    let assets = [...(portfolio.assets || [])];
    const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id);

    for (const child of children) {
      assets = assets.concat(collectAssets(child, allPortfolios));
    }

    return assets;
  }

  /**
   * Строит иерархическое дерево портфелей
   */
  function buildPortfolioTree(portfoliosList) {
    const map = {};
    const roots = [];

    portfoliosList.forEach((p) => {
      map[p.id] = { ...p, children: [] };
    });

    portfoliosList.forEach((p) => {
      if (p.parent_portfolio_id && map[p.parent_portfolio_id]) {
        map[p.parent_portfolio_id].children.push(map[p.id]);
      } else {
        roots.push(map[p.id]);
      }
    });

    return roots;
  }

  /**
   * Получает данные выбранного портфеля с учетом дочерних
   */
  const parsedPortfolioData = computed(() => {
    if (!selectedPortfolio.value) return null;

    const allPortfolios = portfolios.value;
    const portfolioIds = collectPortfolioIds(selectedPortfolio.value, allPortfolios);
    const assets = collectAssets(selectedPortfolio.value, allPortfolios);

    const data = dashboardData.value?.data;
    const transactions = (data?.transactions ?? []).filter(
      t => portfolioIds.includes(t.portfolio_id)
    );

    return {
      portfolio: selectedPortfolio.value,
      portfolioIds,
      assets,
      transactions,
      totalAmount: Number(selectedPortfolio.value.total_value || 0),
      investedAmount: Number(selectedPortfolio.value.total_invested || 0),
      monthlyChange: selectedPortfolio.value.monthly_change || 0,
      assetAllocation: selectedPortfolio.value.asset_allocation ?? {
        labels: [],
        datasets: [{ backgroundColor: [], data: [] }]
      },
      portfolioChart: selectedPortfolio.value.history ?? { labels: [], data: [] },
    };
  });

  return {
    portfolios,
    selectedPortfolio,
    parsedPortfolioData,
    collectPortfolioIds,
    collectAssets,
    buildPortfolioTree,
  };
}


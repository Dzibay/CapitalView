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
   * Оптимизировано: используем Map для O(1) поиска дочерних портфелей
   */
  function collectPortfolioIds(portfolio, portfolioMap) {
    const ids = [portfolio.id];
    
    // Получаем дочерние портфели из Map (O(1) вместо O(n))
    const children = portfolioMap.get(portfolio.id) || [];
    
    for (const child of children) {
      ids.push(...collectPortfolioIds(child, portfolioMap));
    }

    return ids;
  }
  
  /**
   * Создает Map для быстрого поиска дочерних портфелей
   * Возвращает Map<parentId, childPortfolios[]>
   */
  function buildPortfolioChildrenMap(portfolios) {
    const childrenMap = new Map();
    
    // Инициализируем все портфели как имеющие пустой массив детей
    for (const p of portfolios) {
      childrenMap.set(p.id, []);
    }
    
    // Заполняем children для каждого родителя
    for (const p of portfolios) {
      if (p.parent_portfolio_id && childrenMap.has(p.parent_portfolio_id)) {
        childrenMap.get(p.parent_portfolio_id).push(p);
      }
    }
    
    return childrenMap;
  }

  /**
   * Собирает все активы портфеля и его дочерних портфелей
   * Оптимизировано: используем Map для O(1) поиска дочерних портфелей
   */
  function collectAssets(portfolio, portfolioMap) {
    const assets = [...(portfolio.assets || [])];
    
    // Получаем дочерние портфели из Map (O(1) вместо O(n))
    const children = portfolioMap.get(portfolio.id) || [];
    
    for (const child of children) {
      assets.push(...collectAssets(child, portfolioMap));
    }

    return assets;
  }

  /**
   * Строит иерархическое дерево портфелей
   * Скрывает портфели с несуществующими родителями (сироты)
   */
  function buildPortfolioTree(portfoliosList) {
    const map = {};
    const roots = [];

    // Создаем map всех портфелей
    portfoliosList.forEach((p) => {
      map[p.id] = { ...p, children: [] };
    });

    // Строим дерево, скрывая портфели с несуществующими родителями
    portfoliosList.forEach((p) => {
      if (p.parent_portfolio_id) {
        // Проверяем, существует ли родительский портфель
        if (map[p.parent_portfolio_id]) {
          map[p.parent_portfolio_id].children.push(map[p.id]);
        } else {
          // Родитель не существует - это "сирота", не добавляем в дерево
          // (портфель останется в массиве, но не будет отображаться)
          if (import.meta.env.DEV) {
            console.warn(`Портфель ${p.id} (${p.name}) имеет несуществующего родителя ${p.parent_portfolio_id} - скрыт из дерева`)
          }
        }
      } else {
        // Корневой портфель
        roots.push(map[p.id]);
      }
    });

    return roots;
  }

  /**
   * Получает данные выбранного портфеля с учетом дочерних
   * Оптимизировано: используем Set для O(1) поиска вместо O(n) includes
   */
  const parsedPortfolioData = computed(() => {
    if (!selectedPortfolio.value) return null;

    const allPortfolios = portfolios.value;
    
    // Создаем Map дочерних портфелей один раз
    const portfolioMap = buildPortfolioChildrenMap(allPortfolios);
    
    const portfolioIds = collectPortfolioIds(selectedPortfolio.value, portfolioMap);
    const assets = collectAssets(selectedPortfolio.value, portfolioMap);

    // Используем Set для быстрого поиска O(1) вместо O(n) includes
    const portfolioIdSet = new Set(portfolioIds);
    const data = dashboardData.value?.data;
    const transactions = (data?.transactions ?? []).filter(
      t => portfolioIdSet.has(t.portfolio_id)
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




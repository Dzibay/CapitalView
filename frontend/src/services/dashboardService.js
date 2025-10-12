// services/dashboardService.js
import assetsService from './assetsService.js';
import { fetchPortfolioHistory } from './statisticsService.js';

/* === Основная функция === */
export async function fetchDashboardData(user) {
  try {
    const portfolios = await assetsService.getAssets();
    const portfolioHistory = await fetchPortfolioHistory();

    return {
      totalCapital: calculateTotalCapital(portfolios),
      assetAllocation: calculateAssetAllocation(portfolios),
      portfolioChart: buildPortfolioChart(portfolioHistory),
      // investmentGoal: await getInvestmentGoal(user.id),
      // recentTransactions: transactions,
      // topAssets: getTopAssets(portfolios)
    };
  } catch (error) {
    console.error(error);
    return { totalCapital: 0 };
  }
}

/* === Расчёт общего капитала === */
function calculateTotalCapital(portfolios) {
  let totalCurrent = 0;
  let totalInvested = 0;

  portfolios.forEach(p => {
    if (p.assets && Array.isArray(p.assets)) {
      p.assets.forEach(a => {
        const qty = Number(a.quantity) || 0;
        const avgPrice = Number(a.average_price) || 0;
        const currentPrice = Number(a.current_price) || 0;

        totalInvested += qty * avgPrice;
        totalCurrent += qty * currentPrice;
      });
    }
  });

  const absoluteChange = totalCurrent - totalInvested;
  const percentageChange = totalInvested > 0 ? (absoluteChange / totalInvested) * 100 : 0;

  return {
    totalAmount: totalCurrent.toFixed(2),
    investedAmount: totalInvested.toFixed(2),
    monthlyChange: {
      absolute: absoluteChange.toFixed(2),
      percentage: percentageChange.toFixed(2)
    }
  };
}

/* === Распределение активов === */
function calculateAssetAllocation(portfolios = []) {
  if (!Array.isArray(portfolios) || portfolios.length === 0) {
    return { labels: [], datasets: [{ backgroundColor: [], data: [] }] };
  }

  const allocation = {};

  portfolios.forEach(p => {
    p.assets?.forEach(a => {
      const type = a.type;
      if (type === undefined) return;

      const quantity = Number(a.quantity ?? 0);
      const price = Number(a.current_price ?? 0);

      allocation[type] = (allocation[type] || 0) + quantity * price;
    });
  });

  return {
    labels: Object.keys(allocation),
    datasets: [{
      backgroundColor: ['#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
      data: Object.values(allocation),
    }],
  };
}

function buildPortfolioChart(portfolioHistory) {
  console.log('Собираем')
  console.log(portfolioHistory)
  if (!portfolioHistory || Object.keys(portfolioHistory).length === 0) {
    return { labels: [], data: [] };
  }

  // Собираем все даты
  const allDatesSet = new Set();
  Object.values(portfolioHistory).forEach(portfolio => {
    if (!Array.isArray(portfolio)) return;
    portfolio.forEach(point => allDatesSet.add(point.date));
  });

  const allDates = Array.from(allDatesSet).sort();

  // Агрегируем суммарную стоимость по каждой дате
  const aggregatedByDate = {};
  allDates.forEach(date => (aggregatedByDate[date] = 0));

  Object.values(portfolioHistory).forEach(portfolio => {
    if (!Array.isArray(portfolio)) return;
    portfolio.forEach(point => {
      aggregatedByDate[point.date] += point.total_value || 0;
    });
  });

  const labels = Object.keys(aggregatedByDate);
  const data = labels.map(date => aggregatedByDate[date]);

  return { labels, data };
}


/* === Остальные вспомогательные функции (по желанию) === */
async function getInvestmentGoal(userId) {
  return { title: 'Накопить миллион', targetAmount: 1000000, currentAmount: 812430 };
}

function getTopAssets(portfolios) {
  const allAssets = [];
  portfolios.forEach(p => allAssets.push(...p.portfolio_assets));
  allAssets.sort((a, b) => (b.quantity * b.average_price) - (a.quantity * a.average_price));
  return allAssets.slice(0, 5).map(a => ({
    id: a.id,
    name: a.assets.name,
    ticker: a.assets.ticker,
    value: a.quantity * a.average_price,
    changePercentage: 0
  }));
}

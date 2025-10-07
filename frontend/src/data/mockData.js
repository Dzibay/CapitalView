export const mockData = {
  user: {
    firstName: 'Антон',
    lastName: 'Иванов',
    email: 'a.ivanov@invest.com',
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
  },
  totalCapital: {
    totalAmount: 125430.50,
    monthlyChange: {
      percentage: 5.2,
      absolute: 6190.22,
    },
  },
  assetAllocation: {
    labels: ['Акции', 'Облигации', 'Криптовалюта', 'Золото'],
    datasets: [{
      backgroundColor: ['#4A55A2', '#7895CB', '#A0BFE0', '#C5DFF8'],
      data: [40, 25, 20, 15],
    }],
  },
  portfolioChart: {
    labels: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл'],
    datasets: [{
      label: 'Стоимость портфеля',
      data: [65000, 72000, 81000, 75000, 89000, 105000, 125430],
      borderColor: '#4A55A2',
      backgroundColor: 'rgba(74, 85, 162, 0.1)',
      tension: 0.4,
      fill: true,
    }],
  },
  investmentGoal: {
    title: 'Накопить на автомобиль',
    targetAmount: 500000,
    currentAmount: 125430,
    // Данные для прогнозного графика
    predictionData: {
      labels: ['Q3', 'Q4', 'Q1 \'26', 'Q2 \'26'],
      datasets: [{
        label: 'Прогноз роста',
        data: [125430, 210000, 350000, 500000],
        borderColor: '#7895CB',
        tension: 0.4,
      }],
    },
  },
  recentTransactions: [{
      id: 1,
      type: 'buy',
      asset: 'Tesla (TSLA)',
      amount: 1500,
      date: '2025-10-03'
    },
    {
      id: 2,
      type: 'sell',
      asset: 'Bitcoin (BTC)',
      amount: 850.75,
      date: '2025-10-01'
    },
    {
      id: 3,
      type: 'buy',
      asset: 'Облигации ОФЗ-26238',
      amount: 2200,
      date: '2025-09-28'
    },
  ],
  topAssets: [{
      id: 1,
      name: 'NVIDIA Corp.',
      ticker: 'NVDA',
      value: 25600,
      changePercentage: 12.5
    },
    {
      id: 2,
      name: 'Ethereum',
      ticker: 'ETH',
      value: 11200,
      changePercentage: 8.2
    },
    {
      id: 3,
      name: 'S&P 500 ETF',
      ticker: 'VOO',
      value: 18300,
      changePercentage: -1.8
    },
  ],
};
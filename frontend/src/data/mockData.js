export const mockData = {
  user: {
    firstName: 'Антон',
    lastName: 'Балыбин',
    email: 'a.ivanov@invest.com',
    avatarUrl: 'https://i.pravatar.cc/150?u=a042581f4e29026704d',
  },
  totalCapital: {
    totalAmount: 812430.50,
    monthlyChange: {
      percentage: 5.2,
      absolute: 60190.22,
    },
  },
  assetAllocation: {
    labels: ['Акции', 'Облигации', 'Криптовалюта', 'Золото'],
    datasets: [{
      backgroundColor: ['#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
      data: [447873, 210172, 40354, 76000],
    }],
  },
  portfolioChart: {
    labels: ['Нояб', 'Дек', '2025', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Авг', 'Сент', 'Окт'],
    data: [0, 0, 0, 0, 67000, 130000, 240000, 350000, 480000, 640000, 812000]
  },
  investmentGoal: {
    title: 'Накопить миллион',
    targetAmount: 1000000,
    currentAmount: 812430,
  },
  
  recentTransactions: [{
      id: 1,
      type: 'Покупка',
      asset: 'EUTR',
      count: 150,
      amount: 20723.29,
      date: '2025-10-05'
    },
    {
      id: 2,
      type: 'Купон',
      asset: 'ГК Самолет БО-П18',
      count: 20,
      amount: 394.60,
      date: '2025-10-05'
    },
    {
      id: 3,
      type: 'Покупка',
      asset: 'LKOH',
      count: 1,
      amount: 6320.03,
      date: '2025-09-12'
    },
    {
      id: 4,
      type: 'Дивиденды',
      asset: 'X5',
      count: 25,
      amount: 5638.00,
      date: '2025-07-15'
    },
  ],
  topAssets: [{
      id: 1,
      name: 'КЦ ИКС 5',
      ticker: 'X5',
      value: 65475,
      changePercentage: 10.25
    },
    {
      id: 2,
      name: 'Московская биржа',
      ticker: 'MOEX',
      value: 26479,
      changePercentage: 8.32
    },
    {
      id: 3,
      name: 'Лукойл',
      ticker: 'LKOH',
      value: 70668,
      changePercentage: 5.78
    },
    {
      id: 4,
      name: 'Биткойн',
      ticker: 'BTC',
      value: 30652,
      changePercentage: 3.24
    },
  ],
};
// Генерация 2 лет данных (730 дней)
function generatePortfolioData() {
  const labels = []
  const data = []

  const startDate = new Date('2024-01-01')
  let value = 0 // начальный капитал

  for (let i = 0; i < 730; i++) { // 2 года
    const date = new Date(startDate)
    date.setDate(startDate.getDate() + i)

    // Немного шума + постепенный рост
    const growth = Math.random() * 2000 + 100 // прирост за день
    value += growth

    labels.push(date.toISOString().split('T')[0]) // формат YYYY-MM-DD
    data.push(Math.round(value))
  }

  return { labels, data }
}

export default {
  data() {
    return {
      portfolioChart: generatePortfolioData()
    }
  }
}

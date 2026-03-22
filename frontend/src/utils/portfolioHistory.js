/**
 * История портфеля с API: history.series — массив строк
 * [date, value, invested, payouts, pnl, balance].
 */
const D = 0
const V = 1
const I = 2
const PAYOUT = 3
const PNL = 4
const BAL = 5

export function expandPortfolioHistoryForCharts(history) {
  const empty = {
    labels: [],
    data_value: [],
    data_invested: [],
    data_payouts: [],
    data_pnl: [],
    data_balance: [],
  }
  if (!history) return empty

  if (Array.isArray(history.series) && history.series.length > 0) {
    const labels = []
    const data_value = []
    const data_invested = []
    const data_payouts = []
    const data_pnl = []
    const data_balance = []
    for (const row of history.series) {
      if (!Array.isArray(row) || row.length < 6) continue
      labels.push(row[D])
      data_value.push(Number(row[V]) || 0)
      data_invested.push(Number(row[I]) || 0)
      data_payouts.push(Number(row[PAYOUT]) || 0)
      data_pnl.push(Number(row[PNL]) || 0)
      data_balance.push(Number(row[BAL]) || 0)
    }
    return { labels, data_value, data_invested, data_payouts, data_pnl, data_balance }
  }

  if (history.labels && history.data_value) {
    return {
      labels: history.labels || [],
      data_value: history.data_value || [],
      data_invested: history.data_invested || [],
      data_payouts: history.data_payouts || [],
      data_pnl: history.data_pnl || [],
      data_balance: history.data_balance || [],
    }
  }

  if (Array.isArray(history) && history.length > 0) {
    return {
      labels: history.map((h) => h.date || h.month || ''),
      data_value: history.map((h) => h.value || h.total_value || 0),
      data_invested: history.map((h) => h.invested || h.total_invested || 0),
      data_payouts: history.map((h) => h.payouts || 0),
      data_pnl: history.map((h) => h.pnl || h.total_pnl || 0),
      data_balance: history.map((h) => h.balance || 0),
    }
  }

  return empty
}

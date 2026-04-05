import { effectiveUnitPriceInCurrency } from './effectiveAssetPrice'

/**
 * Распределение по типам активов из списка позиций (как в dashboard.assets).
 */
export function assetAllocationFromPositions(assets) {
  if (!assets?.length) {
    return {
      labels: [],
      datasets: [{ backgroundColor: [], data: [] }],
    }
  }
  const allocation = {}
  for (const asset of assets) {
    const atype = asset.type
    if (!atype) continue
    const quantity = Number(asset.quantity || 0)
    const price = effectiveUnitPriceInCurrency(asset)
    const currencyMultiplier = Number(asset.currency_rate_to_rub || 1)
    const lev = Number(asset.leverage || 1) || 1
    allocation[atype] =
      (allocation[atype] || 0) + (quantity * price * currencyMultiplier) / lev
  }
  return {
    labels: Object.keys(allocation),
    datasets: [
      {
        backgroundColor: [
          '#3b82f6',
          '#f59e0b',
          '#ef4444',
          '#8b5cf6',
          '#10b981',
          '#f472b6',
          '#60a5fa',
          '#fbbf24',
          '#a78bfa',
        ],
        data: Object.values(allocation),
      },
    ],
  }
}

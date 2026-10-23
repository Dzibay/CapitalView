import { reactive } from 'vue'
import assetsService from '../../services/assetsService'

/**
 * Короткая история цен для мини-графиков в строках (≈ последний месяц).
 * Кэш общий на сессию: одна бумага запрашивается один раз, даже если она в нескольких виджетах.
 */
const DAYS = 35
const trails = reactive({}) // asset_id -> number[] (пустой массив — истории нет)
const inflight = new Map()

function fetchTrail(assetId) {
  if (inflight.has(assetId)) return inflight.get(assetId)
  const from = new Date(Date.now() - DAYS * 86400000).toISOString().slice(0, 10)
  const p = assetsService
    .getAssetPriceHistory(assetId, from, null, 400)
    .then((res) => {
      const prices = Array.isArray(res?.prices) ? res.prices : []
      trails[assetId] = prices
        .slice()
        .sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)))
        .map((p) => Number(p.price))
        .filter(Number.isFinite)
    })
    .catch(() => { trails[assetId] = [] })
  inflight.set(assetId, p)
  return p
}

export function usePriceTrail() {
  const ensure = (ids) => {
    for (const id of ids) if (id != null && !(id in trails) && !inflight.has(id)) fetchTrail(id)
  }
  return { trails, ensure }
}

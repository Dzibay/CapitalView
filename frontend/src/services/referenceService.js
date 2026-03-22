import apiClient from '../utils/apiClient'
import { API_ENDPOINTS } from '../config/api'
import {
  getCachedReferenceBundle,
  setCachedReferenceBundle,
} from '../utils/referenceCache'

const assetMetaCache = new Map()

/**
 * Поиск системных активов (минимум 2 символа запроса; лимит на сервере).
 */
export async function searchReferenceAssets(query, limit = 25) {
  const q = String(query || '').trim()
  if (q.length < 2) return []
  const res = await apiClient.get(API_ENDPOINTS.REFERENCE.SEARCH_ASSETS, {
    params: { q, limit },
  })
  return res.data?.assets ?? []
}

/**
 * Метаданные одного актива (тикер, quote, last_price). Кэш в памяти на сессию.
 */
export async function fetchReferenceAssetMeta(assetId, options = {}) {
  const force = options.force === true
  const id = Number(assetId)
  if (!id) return null
  if (!force && assetMetaCache.has(id)) return assetMetaCache.get(id)
  const res = await apiClient.get(API_ENDPOINTS.REFERENCE.ASSET_META(id))
  const asset = res.data?.asset
  if (asset && asset.id != null) assetMetaCache.set(id, asset)
  return asset ?? null
}

/**
 * Загрузка справочника с IndexedDB-кэшем по reference_version.
 * @param {{ bypassCache?: boolean }} options — при true всегда тянем полный ответ (после мутаций / force reload).
 */
export async function fetchReferenceData(options = {}) {
  const bypassCache = options.bypassCache === true

  if (!bypassCache && typeof indexedDB !== 'undefined') {
    try {
      const cached = await getCachedReferenceBundle()
      // Нет сохранённой версии — сразу GET /reference/ (лишний GET /version не нужен)
      if (cached?.version) {
        const verRes = await apiClient.get(API_ENDPOINTS.REFERENCE.VERSION)
        const serverVer = verRes.data?.reference_version
        if (
          serverVer &&
          cached.version === serverVer &&
          cached.reference &&
          typeof cached.reference === 'object'
        ) {
          return {
            success: verRes.data?.success !== false,
            reference: cached.reference,
            reference_version: serverVer,
          }
        }
      }
    } catch {
      /* сеть / 401 — ниже полная загрузка */
    }
  }

  const res = await apiClient.get(API_ENDPOINTS.REFERENCE.BASE)
  const body = res.data
  const ref = body?.reference
  const serverVer = body?.reference_version

  if (!bypassCache && ref && serverVer && typeof indexedDB !== 'undefined') {
    await setCachedReferenceBundle({ version: serverVer, reference: ref })
  }

  return body
}

/** Справочный id типа «Вклад» в БД (init.sql) */
export const DEPOSIT_ASSET_TYPE_ID = 10

/**
 * Позиция/актив в портфеле или метаданные — вклад (UI не показывает qty/цену как у бумаг).
 */
export function isDepositLikePortfolioAsset(asset) {
  if (!asset) return false
  const t = String(asset.type || '').trim().toLowerCase()
  if (t === 'вклад' || t === 'вклады' || t.startsWith('вклад')) return true
  if (asset.asset_type_id != null && Number(asset.asset_type_id) === DEPOSIT_ASSET_TYPE_ID) return true
  return false
}

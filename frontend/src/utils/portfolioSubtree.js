/**
 * Id выбранного портфеля и всех его дочерних портфелей (для фильтрации позиций после одного запроса по корню).
 */
export function getDescendantPortfolioIds(portfolios, selectedPortfolioId) {
  if (selectedPortfolioId == null || !portfolios?.length) return new Set()
  const byParent = new Map()
  for (const p of portfolios) {
    const pid = p.parent_portfolio_id
    if (!byParent.has(pid)) byParent.set(pid, [])
    byParent.get(pid).push(p.id)
  }
  const out = new Set()
  const stack = [selectedPortfolioId]
  while (stack.length) {
    const id = stack.pop()
    if (out.has(id)) continue
    out.add(id)
    const children = byParent.get(id) || []
    for (const c of children) stack.push(c)
  }
  return out
}

/** Корневые портфели пользователя (без parent_portfolio_id). */
export function getRootPortfolioIds(portfolios) {
  if (!portfolios?.length) return []
  return portfolios.filter((p) => !p.parent_portfolio_id).map((p) => p.id).filter((id) => id != null)
}

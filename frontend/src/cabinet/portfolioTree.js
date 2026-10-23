/** Портфели в порядке дерева: корень, затем его дочерние (с глубиной). */
export function flattenPortfolioTree(portfolios = []) {
  const byParent = new Map()
  const ids = new Set(portfolios.map((p) => p.id))
  for (const p of portfolios) {
    const parent = p.parent_portfolio_id != null && ids.has(p.parent_portfolio_id) ? p.parent_portfolio_id : null
    if (!byParent.has(parent)) byParent.set(parent, [])
    byParent.get(parent).push(p)
  }
  const out = []
  const walk = (parent, depth) => {
    for (const p of byParent.get(parent) || []) {
      out.push({ portfolio: p, depth })
      walk(p.id, depth + 1)
    }
  }
  walk(null, 0)
  return out
}

export function userInitials(user) {
  const src = (user?.name || user?.email || '?').trim()
  const parts = src.split(/[\s@._-]+/).filter(Boolean)
  return ((parts[0]?.[0] || '?') + (parts[1]?.[0] || '')).toUpperCase()
}

/**
 * Позиции выбранного портфеля и всех дочерних (для графиков / виджетов).
 * Список assets у каждого узла — только прямые; итог по ветке собирается здесь.
 */
export function collectSubtreeAssets(root, allPortfolios) {
  if (!root || !Array.isArray(allPortfolios)) return []

  const childrenByParent = new Map()
  for (const p of allPortfolios) {
    const parentId = p.parent_portfolio_id
    if (parentId == null) continue
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, [])
    childrenByParent.get(parentId).push(p)
  }

  function walk(p) {
    const out = [...(p.assets || [])]
    for (const c of childrenByParent.get(p.id) || []) {
      out.push(...walk(c))
    }
    return out
  }

  return walk(root)
}


WITH RECURSIVE children AS (
    SELECT id, name, parent_portfolio_id
    FROM portfolios
    WHERE parent_portfolio_id = p_parent_id

    UNION ALL

    SELECT p.id, p.name, p.parent_portfolio_id
    FROM portfolios p
    INNER JOIN children c ON p.parent_portfolio_id = c.id
)
SELECT * FROM children;

BEGIN
    RETURN (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'name', p.name,
                'description', p.description,
                'parent_portfolio_id', p.parent_portfolio_id,
                'assets', COALESCE(a.assets_json, '[]'::jsonb),
                'history', COALESCE(h.history_json, '[]'::jsonb),
                'analytics', COALESCE(an.analytics_json, '{}'::jsonb)
            )
        )
        FROM portfolios p

        -- 🟣 Активы
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(row_to_json(ga)) AS assets_json
            FROM get_portfolio_assets(p.id) AS ga
        ) a ON TRUE

        -- 🔵 История стоимости
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'date', gh.report_date,
                    'value', gh.total_value,
                    'invested', gh.total_invested,
                    'payouts', gh.total_payouts,
                    'pnl', gh.total_pnl
                )
                ORDER BY gh.report_date
            ) AS history_json
            FROM get_portfolio_value_history(p.id) AS gh
        ) h ON TRUE

        -- 🟠 Аналитика портфеля
        LEFT JOIN LATERAL (
            SELECT get_portfolio_analytics(p.id, p.user_id)::jsonb AS analytics_json
        ) an ON TRUE

        WHERE p.user_id = p_user_id
    );
END;
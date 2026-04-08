-- Единый снимок данных для админки (счётчики + ряд регистраций по дням).
DROP FUNCTION IF EXISTS get_admin_users_registration_series();

CREATE OR REPLACE FUNCTION get_admin_data()
RETURNS json
LANGUAGE sql
STABLE
AS $$
  SELECT json_build_object(
    'overview', json_build_object(
      'users_total', (SELECT COUNT(*)::bigint FROM users),
      'users_verified', (SELECT COUNT(*)::bigint FROM users WHERE email_verified),
      'portfolios_total', (SELECT COUNT(*)::bigint FROM portfolios),
      'portfolio_assets_total', (SELECT COUNT(*)::bigint FROM portfolio_assets)
    ),
    'users_registration_series', (
      SELECT COALESCE(
        (
          WITH bounds AS (
            SELECT
              MIN((created_at AT TIME ZONE 'UTC')::date) AS d0,
              (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date AS d1
            FROM users
          ),
          days AS (
            SELECT gs::date AS d
            FROM bounds
            CROSS JOIN LATERAL generate_series(
              bounds.d0,
              bounds.d1,
              interval '1 day'
            ) AS gs
          ),
          by_day AS (
            SELECT (created_at AT TIME ZONE 'UTC')::date AS d, COUNT(*)::bigint AS cnt
            FROM users
            GROUP BY 1
          ),
          by_day_verified AS (
            SELECT (created_at AT TIME ZONE 'UTC')::date AS d, COUNT(*)::bigint AS cnt
            FROM users
            WHERE email_verified
            GROUP BY 1
          ),
          series AS (
            SELECT
              days.d::text AS date,
              COALESCE(b.cnt, 0)::bigint AS new_users,
              SUM(COALESCE(b.cnt, 0)) OVER (ORDER BY days.d)::bigint AS cumulative_users,
              COALESCE(bv.cnt, 0)::bigint AS new_verified,
              SUM(COALESCE(bv.cnt, 0)) OVER (ORDER BY days.d)::bigint AS cumulative_verified
            FROM days
            LEFT JOIN by_day b ON b.d = days.d
            LEFT JOIN by_day_verified bv ON bv.d = days.d
          )
          SELECT json_agg(
            json_build_object(
              'date', s.date,
              'new_users', s.new_users,
              'cumulative_users', s.cumulative_users,
              'new_verified', s.new_verified,
              'cumulative_verified', s.cumulative_verified
            )
            ORDER BY s.date
          )
          FROM series s
        ),
        '[]'::json
      )
    ),
    'users', (
      SELECT COALESCE(
        (
          SELECT json_agg(
            json_build_object(
              'id', u.id,
              'name', u.name,
              'email', u.email,
              'created_at', u.created_at,
              'last_login_at', u.last_login_at
            )
            ORDER BY u.created_at DESC
          )
          FROM users u
        ),
        '[]'::json
      )
    )
  );
$$;

COMMENT ON FUNCTION get_admin_data() IS
  'Админка: overview, users_registration_series, список users (name, email, created_at, last_login_at)';

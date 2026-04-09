-- Список обращений в поддержку для админки (с email и именем пользователя).
CREATE OR REPLACE FUNCTION get_admin_support_messages(p_limit bigint DEFAULT 500)
RETURNS json
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    json_agg(
      json_build_object(
        'id', s.id,
        'user_id', s.user_id::text,
        'message', s.message,
        'created_at', s.created_at,
        'user_email', s.user_email,
        'user_name', s.user_name
      )
      ORDER BY s.sort_ts DESC
    ),
    '[]'::json
  )
  FROM (
    SELECT
      m.id,
      m.user_id,
      m.message,
      m.created_at,
      u.email AS user_email,
      u.name AS user_name,
      m.created_at AS sort_ts
    FROM support_messages m
    JOIN users u ON u.id = m.user_id
    ORDER BY m.created_at DESC
    LIMIT p_limit
  ) s;
$$;

COMMENT ON FUNCTION get_admin_support_messages(bigint) IS
  'Сообщения support_messages с данными users для platform admin (новые первыми).';

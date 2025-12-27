
BEGIN
  -- Отправляем запрос сами себе, база не ждет ответа
  PERFORM net.http_post(
    url := 'https://wnoulslvcvyhnwvjiixw.supabase.co/rest/v1/rpc/refresh_all_portfolio_daily_data',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indub3Vsc2x2Y3Z5aG53dmppaXh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTM1Njg3NywiZXhwIjoyMDc0OTMyODc3fQ.bHnjP5uD5wLIkiRaaX60MdaCdEW5EK82ayWxYqxf0CY"}'::jsonb
  );
  RETURN '{"status": "ok"}'::json;
END;

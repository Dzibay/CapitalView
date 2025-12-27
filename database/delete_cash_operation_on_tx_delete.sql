
BEGIN
  DELETE FROM cash_operations WHERE transaction_id = OLD.id;
  RETURN OLD;
END;

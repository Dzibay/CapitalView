"""
Unit тесты для утилит работы с датами.
"""
import pytest
from datetime import datetime, date, timezone
from app.shared.utils.date import (
    parse_date,
    normalize_date_to_string,
    normalize_date_to_day_string,
    parse_date_range
)


class TestParseDate:
    """Тесты для функции parse_date."""
    
    def test_parse_iso_string(self):
        """Тест парсинга ISO строки."""
        result = parse_date("2023-01-01")
        assert result == datetime(2023, 1, 1)
    
    def test_parse_iso_string_with_time(self):
        """Тест парсинга ISO строки с временем."""
        result = parse_date("2023-01-01T12:00:00")
        assert result == datetime(2023, 1, 1, 12, 0, 0)
    
    def test_parse_iso_string_with_timezone(self):
        """Тест парсинга ISO строки с timezone."""
        result = parse_date("2023-01-01T12:00:00Z")
        assert result is not None
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_datetime_object(self):
        """Тест парсинга datetime объекта."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = parse_date(dt)
        assert result == dt
    
    def test_parse_date_object(self):
        """Тест парсинга date объекта."""
        d = date(2023, 1, 1)
        result = parse_date(d)
        assert result == datetime(2023, 1, 1)
    
    def test_parse_none(self):
        """Тест парсинга None."""
        result = parse_date(None)
        assert result is None
    
    def test_parse_invalid_string(self):
        """Тест парсинга невалидной строки."""
        result = parse_date("invalid")
        assert result is None


class TestNormalizeDateToString:
    """Тесты для функции normalize_date_to_string."""
    
    def test_normalize_datetime(self):
        """Тест нормализации datetime."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = normalize_date_to_string(dt)
        assert result == "2023-01-01"
    
    def test_normalize_datetime_with_time(self):
        """Тест нормализации datetime с временем."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = normalize_date_to_string(dt, include_time=True)
        assert "2023-01-01T12:00:00" in result
    
    def test_normalize_date_object(self):
        """Тест нормализации date объекта."""
        d = date(2023, 1, 1)
        result = normalize_date_to_string(d)
        assert result == "2023-01-01"
    
    def test_normalize_string(self):
        """Тест нормализации строки."""
        result = normalize_date_to_string("2023-01-01T12:00:00Z")
        assert result == "2023-01-01"
    
    def test_normalize_none(self):
        """Тест нормализации None."""
        result = normalize_date_to_string(None)
        assert result is None


class TestNormalizeDateToDayString:
    """Тесты для функции normalize_date_to_day_string."""
    
    def test_normalize_to_day_string(self):
        """Тест нормализации в строку дня."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = normalize_date_to_day_string(dt)
        assert result == "2023-01-01"


class TestParseDateRange:
    """Тесты для функции parse_date_range."""
    
    def test_parse_date_range(self):
        """Тест парсинга диапазона дат."""
        start, end = parse_date_range("2023-01-01", "2023-12-31")
        assert start == datetime(2023, 1, 1)
        assert end == datetime(2023, 12, 31)
    
    def test_parse_date_range_with_none(self):
        """Тест парсинга диапазона с None."""
        start, end = parse_date_range(None, "2023-12-31")
        assert start is None
        assert end == datetime(2023, 12, 31)
    
    def test_parse_date_range_both_none(self):
        """Тест парсинга диапазона с обоими None."""
        start, end = parse_date_range(None, None)
        assert start is None
        assert end is None

import requests
from datetime import datetime
from app.services.supabase_service import table_select, table_insert

MOEX_DIVIDENDS_URL = "https://iss.moex.com/iss/securities/{ticker}/dividends.json"

def fetch_dividends_from_moex(ticker: str):
    """Получает дивиденды по тикеру с MOEX ISS API"""
    url = MOEX_DIVIDENDS_URL.format(ticker=ticker)
    r = requests.get(url)
    if r.status_code != 200:
        print(f"⚠️ Ошибка при запросе {ticker}: {r.status_code}")
        return []

    data = r.json()
    if "dividends" not in data or "data" not in data["dividends"]:
        print(f"⚠️ Нет данных по дивидендам для {ticker}")
        return []

    columns = data["dividends"]["columns"]
    rows = data["dividends"]["data"]

    results = []
    for row in rows:
        record = dict(zip(columns, row))
        results.append({
            "record_date": record.get("registryclosedate"),
            "value": record.get("value"),
            "currency": record.get("currencyid")
        })
    return results


def update_asset_dividends(asset):
    """Обновляет дивиденды для конкретного актива"""
    asset_id = asset["id"]
    ticker = asset["ticker"]

    print(f"\n📈 Проверяем дивиденды для {ticker} (asset_id={asset_id})")

    dividends = fetch_dividends_from_moex(ticker)
    if not dividends:
        print("  ⚠️ Нет дивидендных данных.")
        return

    # Существующие выплаты в базе
    existing = table_select("asset_payouts", filters={"asset_id": asset_id})
    existing_records = {(str(i["record_date"]), round(float(i["value"] or 0), 2)) for i in existing}

    added = 0
    for d in dividends:
        if not d["record_date"] or not d["value"]:
            continue

        key = (str(d["record_date"]), round(float(d["value"]), 2))
        if key in existing_records:
            continue

        payout_data = {
            "asset_id": asset_id,
            "value": d["value"],
            "record_date": d["record_date"],
            "declared_date": None,  # MOEX не даёт этих полей
            "payment_date": None
        }

        try:
            table_insert("asset_payouts", payout_data)
            added += 1
        except Exception as e:
            print(f"  ❌ Ошибка вставки: {e}")

    if added:
        print(f"  ✅ Добавлено {added} новых выплат.")
    else:
        print("  ℹ️ Новых выплат нет.")


def update_all_moex_assets():
    """Обновляет дивиденды по всем активам, где properties.source = 'moex'"""
    print("🚀 Обновляем дивиденды для активов MOEX...")
    assets = table_select("assets")
    moex_assets = [
        a for a in assets
        if a.get("properties") and a["properties"].get("source") == "moex"
    ]

    if not moex_assets:
        print("⚠️ Нет активов с source='moex'.")
        return

    for asset in moex_assets:
        try:
            update_asset_dividends(asset)
        except Exception as e:
            print(f"❌ Ошибка при обработке {asset['ticker']}: {e}")

    print("\n✅ Обновление завершено.")


if __name__ == "__main__":
    update_all_moex_assets()

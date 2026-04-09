"""ID типов выплат — совпадают с seed в database/init.sql (таблица payout_types)."""

PAYOUT_TYPE_DIVIDEND_ID = 1
PAYOUT_TYPE_COUPON_ID = 2
PAYOUT_TYPE_AMORTIZATION_ID = 3

PAYOUT_CODE_BY_ID = {
    PAYOUT_TYPE_DIVIDEND_ID: "dividend",
    PAYOUT_TYPE_COUPON_ID: "coupon",
    PAYOUT_TYPE_AMORTIZATION_ID: "amortization",
}

PAYOUT_ID_BY_CODE = {v: k for k, v in PAYOUT_CODE_BY_ID.items()}

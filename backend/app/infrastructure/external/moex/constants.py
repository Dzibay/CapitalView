"""
Общие константы для работы с MOEX API.
"""
# BOARDID для фондов
FUND_BOARDIDS = {"TQTF", "TQIF", "TQIR", "TQIA", "TQIM", "TQIN", "TQIP", "TQIU", "TQIV", "TQIW", "TQIX", "TQIY", "TQIZ"}

# Приоритетные BOARDID для выбора основной записи (в порядке приоритета)
PRIORITY_BOARDIDS = ["TQBR", "TQTF", "TQTD", "TQTY", "SMAL", "SPEQ", "TQCB"]

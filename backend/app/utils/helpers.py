import datetime

def format_date(dt):
    if isinstance(dt, str):
        return dt.split("T")[0]
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%d")
    return dt

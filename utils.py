import time
from datetime import datetime
from typing import Optional, Literal


def safe_access(data, keys) -> Optional:
    result = data
    for k in keys:
        if k not in result:
            return None
        result = result[k]
    return result


def now() -> int:
    return int(time.time())


#  date "2024-04-18T17:00Z"
def convert_date_to_timestamp(date: str) -> int:
    datetime_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
    return int(datetime_obj.timestamp())


def expiry_plus(length: Literal['3M', '1Y', 'end_day', '3Y', '1M']) -> int:
    if length == '3M':
        expiry = 90 * 24 * 3600
    elif length == '1Y':
        expiry = 365 * 24 * 3600
    elif length == 'end_day':
        current = datetime.now()
        end_day = datetime(current.year, current.month, current.day, 23, 59, 59)
        expiry = int((end_day - current).total_seconds())
    elif length == '3Y':
        expiry = 3 * 365 * 24 * 3600
    elif length == '1M':
        expiry = 30 * 24 * 3600
    else:
        raise ValueError("Invalid length")
    return expiry

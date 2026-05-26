import jdatetime
from datetime import datetime

def to_jalali(dt=None) -> str:
    if dt is None: dt = datetime.utcnow()
    try: return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
    except: return "—"

def jalali_now() -> str:
    return jdatetime.datetime.now().strftime("%Y/%m/%d  %H:%M")

def fmt(amount, currency="تومان") -> str:
    if amount is None: return "0"
    return f"{amount:,.0f} {currency}".strip()

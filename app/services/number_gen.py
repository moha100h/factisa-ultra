import random, string
from datetime import datetime

def gen_invoice_number() -> str:
    prefix = datetime.utcnow().strftime("%Y%m")
    rand = "".join(random.choices(string.digits, k=4))
    return f"INV-{prefix}-{rand}"

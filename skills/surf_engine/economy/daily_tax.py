# skills/surf_engine/economy/daily_tax.py
"""
Trigger setoran harian jam 9 pagi WIB.
Dipanggil dari colony_loop setiap siklus.
"""

from datetime import datetime, timezone, timedelta
from core.bank_digital import digital_bank

WIB = timezone(timedelta(hours=7))


def check_and_process_daily_tax():
    """
    Cek apakah sekarang jam 9 pagi WIB (±5 menit).
    Jika ya, proses setoran untuk semua DNA hidup.
    """
    now = datetime.now(WIB)
    if now.hour == 9 and now.minute < 5:
        digital_bank.process_all_daily_tax()
        return True
    return False

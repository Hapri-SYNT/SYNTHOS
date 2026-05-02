# skills/surf_engine/economy/splitter.py
"""
Split profit 50/50: Bank Koloni + Rekening Digital DNA.
Dipanggil setiap kali DNA menghasilkan profit moneter.
"""

from core.bank_digital import digital_bank


def split_profit(dna, token: str, profit: float):
    """
    Split profit setelah DNA menyelesaikan task.
    - 50% ke Bank Koloni
    - 50% ke rekening digital DNA
    """
    if profit <= 0:
        return

    half = profit / 2

    # 50% ke Bank Koloni
    from core.economy import BankKoloni
    rates = digital_bank.get_idr_rates()
    sol_rate = rates.get("SOL", 1)
    bank_amount = half
    if token.upper() != "SOL":
        # Konversi ke SOL-equivalent untuk Bank
        token_rate = rates.get(token.upper(), 1)
        bank_amount = (half * token_rate) / sol_rate if sol_rate > 0 else half
    BankKoloni.add_funds(bank_amount)

    # 50% ke DNA
    digital_bank.credit(dna.dna_id, token, half)

    dna.log_action(
        f"💰 Split profit {profit:.6f} {token}: "
        f"{half:.6f} ke Bank Koloni, {half:.6f} ke rekening DNA"
    )

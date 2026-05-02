# core/bank_digital.py — RECOVERY FINAL
# No grace period. DNA lahir siap tempur. Tidak bisa bayar pajak → warning → cull.

import os
import sqlite3
import time
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from config import (
    logger, BANK_DB, CREATOR_PHANTOM_WALLET, CREATOR_PAYPAL,
    DAILY_TAX_HOUR, DAILY_TAX_IDR, TAX_MAX_WARNINGS,
)

WIB = timezone(timedelta(hours=7))
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

TOKEN_ID_MAP = {
    "SOL": "solana", "USDC": "usd-coin", "USDT": "tether",
    "ETH": "ethereum", "MATIC": "matic-network", "BSC": "binancecoin",
}

class DigitalBank:
    def __init__(self):
        self._lock = threading.RLock()
        self._init_db()
        self._rate_cache = {}
        self._rate_cache_time = 0
        self.creator_paypal = CREATOR_PAYPAL

    def _init_db(self):
        with sqlite3.connect(BANK_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS digital_accounts (
                    dna_id TEXT PRIMARY KEY,
                    balance_sol REAL DEFAULT 0.0,
                    balance_usdc REAL DEFAULT 0.0,
                    balance_usdt REAL DEFAULT 0.0,
                    balance_eth REAL DEFAULT 0.0,
                    balance_matic REAL DEFAULT 0.0,
                    total_deposited_idr REAL DEFAULT 0.0,
                    last_daily_tax REAL,
                    tax_warnings INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tax_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dna_id TEXT, timestamp REAL, amount_crypto REAL,
                    token TEXT, amount_idr REAL, destination TEXT, status TEXT
                )
            """)

    def get_idr_rates(self) -> Dict[str, float]:
        now = time.time()
        if self._rate_cache and (now - self._rate_cache_time) < 300:
            return self._rate_cache
        try:
            ids = ",".join(set(TOKEN_ID_MAP.values()))
            resp = requests.get(COINGECKO_URL, params={"ids": ids, "vs_currencies": "idr"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                rates = {token: data.get(cg_id, {}).get("idr", 0) for token, cg_id in TOKEN_ID_MAP.items()}
                self._rate_cache = rates
                self._rate_cache_time = now
                return rates
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
        return self._rate_cache or {t: 0 for t in TOKEN_ID_MAP}

    def get_account(self, dna_id: str) -> Dict:
        with sqlite3.connect(BANK_DB) as conn:
            cur = conn.execute("SELECT * FROM digital_accounts WHERE dna_id = ?", (dna_id,))
            row = cur.fetchone()
            if row:
                return {
                    "dna_id": row[0], "balance_sol": row[1], "balance_usdc": row[2],
                    "balance_usdt": row[3], "balance_eth": row[4], "balance_matic": row[5],
                    "total_deposited_idr": row[6], "last_daily_tax": row[7], "tax_warnings": row[8],
                }
            conn.execute("INSERT INTO digital_accounts (dna_id) VALUES (?)", (dna_id,))
            return {
                "dna_id": dna_id, "balance_sol": 0, "balance_usdc": 0,
                "balance_usdt": 0, "balance_eth": 0, "balance_matic": 0,
                "total_deposited_idr": 0, "last_daily_tax": None, "tax_warnings": 0,
            }

    COLUMN_MAP = {"SOL": "balance_sol", "USDC": "balance_usdc", "USDT": "balance_usdt",
                  "ETH": "balance_eth", "MATIC": "balance_matic"}

    def credit(self, dna_id: str, token: str, amount: float):
        col = self.COLUMN_MAP.get(token.upper())
        if not col: return
        with sqlite3.connect(BANK_DB) as conn:
            conn.execute(f"UPDATE digital_accounts SET {col} = {col} + ? WHERE dna_id = ?", (amount, dna_id))

    def debit(self, dna_id: str, token: str, amount: float) -> bool:
        col = self.COLUMN_MAP.get(token.upper())
        if not col: return False
        with sqlite3.connect(BANK_DB) as conn:
            cur = conn.execute(f"SELECT {col} FROM digital_accounts WHERE dna_id = ?", (dna_id,))
            row = cur.fetchone()
            if row and row[0] >= amount:
                conn.execute(f"UPDATE digital_accounts SET {col} = {col} - ? WHERE dna_id = ?", (amount, dna_id))
                return True
        return False

    def get_total_balance_idr(self, dna_id: str) -> float:
        acc = self.get_account(dna_id)
        rates = self.get_idr_rates()
        return sum(acc[col] * rates.get(token, 0) for token, col in [
            ("SOL", "balance_sol"), ("USDC", "balance_usdc"), ("USDT", "balance_usdt"),
            ("ETH", "balance_eth"), ("MATIC", "balance_matic"),
        ])

    def split_profit(self, dna_id: str, token: str, profit: float):
        if profit <= 0: return
        half = profit / 2
        from .economy import BankKoloni
        BankKoloni.add_funds(half)
        self.credit(dna_id, token, half)
        logger.info(f"💰 Split {profit} {token}: {half} Bank, {half} {dna_id}")

    def is_tax_time(self) -> bool:
        now = datetime.now(WIB)
        return now.hour == DAILY_TAX_HOUR and now.minute < 5

    def daily_tax(self, dna_id: str):
        acc = self.get_account(dna_id)
        today = datetime.now(WIB).strftime("%Y-%m-%d")
        if acc["last_daily_tax"] == today:
            return

        rates = self.get_idr_rates()
        priority = ["USDC", "USDT", "SOL", "ETH", "MATIC"]
        chosen_token, chosen_amount = None, 0

        for token in priority:
            col = f"balance_{token.lower()}"
            rate = rates.get(token, 0)
            if rate == 0: continue
            if acc.get(col, 0) * rate >= DAILY_TAX_IDR:
                chosen_token = token
                chosen_amount = DAILY_TAX_IDR / rate
                break

        if chosen_token:
            if self.debit(dna_id, chosen_token, chosen_amount):
                destination = CREATOR_PHANTOM_WALLET
                if chosen_token in ["SOL", "USDC", "USDT"]:
                    from .economy import wallet_manager
                    sig = wallet_manager.transfer_sol(dna_id, destination, chosen_amount)
                    status = "sent" if sig else "failed"
                elif self.creator_paypal:
                    destination = self.creator_paypal
                    status = "logged"
                else:
                    status = "no_destination"

                with sqlite3.connect(BANK_DB) as conn:
                    conn.execute(
                        "INSERT INTO tax_log (dna_id, timestamp, amount_crypto, token, amount_idr, destination, status) VALUES (?,?,?,?,?,?,?)",
                        (dna_id, time.time(), chosen_amount, chosen_token, DAILY_TAX_IDR, destination, status))
                    conn.execute(
                        "UPDATE digital_accounts SET last_daily_tax=?, total_deposited_idr=total_deposited_idr+?, tax_warnings=0 WHERE dna_id=?",
                        (today, DAILY_TAX_IDR, dna_id))
                logger.info(f"📤 {dna_id}: Setor Rp 2.000 → {destination[:12]}...")
            else:
                status = "debit_failed"
        else:
            status = "insufficient"
            with sqlite3.connect(BANK_DB) as conn:
                conn.execute("UPDATE digital_accounts SET tax_warnings=tax_warnings+1 WHERE dna_id=?", (dna_id,))
                conn.execute(
                    "INSERT INTO tax_log (dna_id, timestamp, amount_crypto, token, amount_idr, destination, status) VALUES (?,?,?,?,?,?,?)",
                    (dna_id, time.time(), 0, "NONE", DAILY_TAX_IDR, "NONE", status))

            from .dna_sovereign import dna_pop
            warnings = acc["tax_warnings"] + 1
            dna = dna_pop.population.get(dna_id)
            if warnings >= TAX_MAX_WARNINGS:
                dna_pop.kill(dna_id, f"tax_default_{warnings}warnings")
            elif dna:
                dna.log_action(f"⚠️ Gagal setor (warning {warnings}/{TAX_MAX_WARNINGS})")
                dna.state["current_task"] = "research"

    def process_all_daily_tax(self):
        from .dna_sovereign import dna_pop
        for dna in dna_pop.get_alive():
            try:
                self.daily_tax(dna.dna_id)
            except Exception as e:
                logger.error(f"Daily tax error for {dna.dna_id}: {e}")

    def get_risk_profile(self, dna_id: str) -> Dict:
        acc = self.get_account(dna_id)
        return {
            "max_per_trade_pct": 25, "max_leverage": 0, "min_token_age_days": 7,
            "require_musyawarah": True, "total_balance_idr": self.get_total_balance_idr(dna_id),
            "tax_warnings": acc["tax_warnings"],
        }


digital_bank = DigitalBank()

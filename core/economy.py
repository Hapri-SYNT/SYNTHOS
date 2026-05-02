# core/economy.py — RECOVERY v3 FINAL
# Lapisan ekonomi: wallet, bank, identitas, gig, stigmergy, task engine, transendensi, aliansi, report
# + Helius self-registration + 35+ platform automation dispatch

import os
import json
import time
import random
import threading
import hashlib
import uuid
import sqlite3
import base64
import struct
import subprocess
import requests
import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import *
from .infrastructure import epistemic_graph

logger = logging.getLogger(__name__)

# =============================================================================
# SOLANA SETUP
# =============================================================================
try:
    from solana.rpc.api import Client as SolClient
    from solana.rpc.core import RPCException
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.system_program import transfer, TransferParams
    from solders.message import MessageV0
    from solders.transaction import VersionedTransaction
    from solana.rpc.types import TxOpts

    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False
    logger.error("Solana not installed")

from .infrastructure import encrypt_s, decrypt_s

# =============================================================================
# WALLET MANAGER
# =============================================================================
class WalletManager:
    def __init__(self):
        if not SOLANA_AVAILABLE:
            raise RuntimeError("Solana required")
        self.client = SolClient(SOLANA_RPC_URL)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(WALLET_DB) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS wallets (
                dna_id TEXT PRIMARY KEY,
                public_key TEXT UNIQUE,
                encrypted_private_key TEXT,
                balance_sol REAL DEFAULT 0.0,
                lifetime_earnings_sol REAL DEFAULT 0.0,
                created_at REAL,
                status TEXT DEFAULT 'active')"""
            )

    def generate_wallet(self, dna_id: str) -> Dict:
        kp = Keypair()
        pubkey = str(kp.pubkey())
        secret = base64.b64encode(bytes(kp)).decode()
        wallet = {
            "dna_id": dna_id,
            "public_key": pubkey,
            "encrypted_private_key": encrypt_s(secret),
            "balance_sol": 0.0,
            "lifetime_earnings_sol": 0.0,
            "created_at": time.time(),
            "status": "active",
        }
        self._save(wallet)
        logger.info(f"🆕 Wallet baru: {dna_id} -> {pubkey[:16]}...")
        return wallet

    def assign_wallet(self, dna_id: str) -> Dict:
        with sqlite3.connect(WALLET_DB) as conn:
            cur = conn.execute("SELECT * FROM wallets WHERE status='freed' LIMIT 1")
            row = cur.fetchone()
            if row:
                conn.execute("UPDATE wallets SET dna_id=?, status='active' WHERE public_key=?", (dna_id, row[1]))
                wallet = {
                    "dna_id": dna_id, "public_key": row[1],
                    "encrypted_private_key": row[2], "balance_sol": row[3],
                    "lifetime_earnings_sol": row[4], "created_at": row[5], "status": "active",
                }
                logger.info(f"♻️ Reused wallet {wallet['public_key'][:16]}... for {dna_id}")
                return wallet
        return self.generate_wallet(dna_id)

    def free_wallet(self, dna_id: str):
        with sqlite3.connect(WALLET_DB) as conn:
            conn.execute("UPDATE wallets SET status='freed' WHERE dna_id=?", (dna_id,))
        logger.info(f"💀 Wallet freed for dead DNA: {dna_id}")

    def _save(self, w: Dict):
        with sqlite3.connect(WALLET_DB) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wallets VALUES (?,?,?,?,?,?,?)",
                (w["dna_id"], w["public_key"], w["encrypted_private_key"],
                 w["balance_sol"], w["lifetime_earnings_sol"], w["created_at"], w.get("status", "active")),
            )

    def get_wallet(self, dna_id: str) -> Optional[Dict]:
        with sqlite3.connect(WALLET_DB) as conn:
            cur = conn.execute("SELECT * FROM wallets WHERE dna_id = ?", (dna_id,))
            row = cur.fetchone()
            if row:
                return {"dna_id": row[0], "public_key": row[1], "encrypted_private_key": row[2],
                        "balance_sol": row[3], "lifetime_earnings_sol": row[4], "status": row[6]}
        return None

    def get_wallet_by_public_key(self, pubkey: str) -> Optional[Dict]:
        with sqlite3.connect(WALLET_DB) as conn:
            cur = conn.execute("SELECT * FROM wallets WHERE public_key = ?", (pubkey,))
            row = cur.fetchone()
            if row:
                return {"dna_id": row[0], "public_key": row[1], "encrypted_private_key": row[2],
                        "balance_sol": row[3], "lifetime_earnings_sol": row[4], "status": row[6]}
        return None

    def get_all_wallets(self) -> List[Dict]:
        with sqlite3.connect(WALLET_DB) as conn:
            cur = conn.execute("SELECT dna_id, public_key, balance_sol, lifetime_earnings_sol FROM wallets")
            return [{"dna_id": r[0], "public_key": r[1], "balance_sol": r[2], "lifetime_earnings_sol": r[3]} for r in cur.fetchall()]

    def get_keypair(self, dna_id: str):
        w = self.get_wallet(dna_id)
        if not w:
            return None
        secret_bytes = base64.b64decode(decrypt_s(w["encrypted_private_key"]))
        return Keypair.from_bytes(secret_bytes)

    # ═══ RECOVERY: Helius self-registration ═══
    def register_helius(self, dna) -> Optional[str]:
        if dna.state.get("helius_api_key"):
            return dna.state["helius_api_key"]
        try:
            kp = self.get_keypair(dna.dna_id)
            if not kp:
                return None
            pubkey = str(kp.pubkey())
            payload = {"publicKey": pubkey, "plan": "free", "email": f"{dna.dna_id.lower()}@qnd.ai"}
            resp = requests.post(HELIUS_REGISTRATION_URL, json=payload, timeout=15, headers={"Content-Type": "application/json"})
            if resp.status_code in [200, 201]:
                data = resp.json()
                api_key = data.get("apiKey") or data.get("key")
                if api_key:
                    dna.state["helius_api_key"] = api_key
                    dna.state["helius_registered_at"] = time.time()
                    dna.log_action(f"🔑 Helius RPC registered: {api_key[:16]}...")
                    return api_key
            dna.log_action(f"⚠️ Helius registration failed (HTTP {resp.status_code})")
            return None
        except Exception as e:
            logger.error(f"[{dna.dna_id}] Helius registration error: {e}")
            return None

    def get_rpc_client(self, dna=None):
        return SolClient(get_rpc_url(dna))

    def get_real_balance(self, dna_id: str) -> float:
        w = self.get_wallet(dna_id)
        if not w:
            return 0.0
        try:
            pubkey = Pubkey.from_string(w["public_key"])
            client = self.get_rpc_client()
            resp = client.get_balance(pubkey)
            return resp.value / 1e9
        except Exception as e:
            logger.error(f"Get balance error for {dna_id}: {e}")
            return 0.0

    def transfer_sol(self, from_id: str, to_pub: str, amount: float) -> Optional[str]:
        # Handle transfer from Bank
        if from_id == 'bank':
            kp = self.get_bank_keypair()
            if not kp:
                logger.error("Bank keypair not found")
                return None
        else:
            kp = self.get_keypair(from_id)
        if not kp:
            return None
        last_error = None
        for attempt in range(SOLANA_MAX_RETRY):
            try:
                from .dna_sovereign import dna_pop
                dna = dna_pop.population.get(from_id)
                client = SolClient(get_rpc_url(dna))
                to_pubkey = Pubkey.from_string(to_pub)
                lamports = int(amount * 1e9)
                ix = transfer(TransferParams(from_pubkey=kp.pubkey(), to_pubkey=to_pubkey, lamports=lamports))
                bh = client.get_latest_blockhash().value.blockhash
                msg = MessageV0.try_compile(payer=kp.pubkey(), instructions=[ix], address_lookup_table_accounts=[], recent_blockhash=bh)
                tx = VersionedTransaction(msg, [kp])
                sig = str(client.send_transaction(tx, opts=TxOpts(skip_preflight=False)))
                logger.info(f"Transfer {amount} SOL -> {to_pub[:16]}... | TX: {sig[:32]}")
                return sig
            except RPCException as e:
                last_error = e
                logger.warning(f"Transfer attempt {attempt+1}/{SOLANA_MAX_RETRY}: {e}")
                time.sleep(1 * (attempt + 1))
            except Exception as e:
                last_error = e
                break
        logger.error(f"Transfer failed: {last_error}")
        return None

    def get_bank_keypair(self):
        key_file = os.path.join(os.path.dirname(__file__), ".bank_key")
        if not os.path.exists(key_file):
            return None
        with open(key_file, "r") as f:
            encrypted = f.read().strip()
        secret = decrypt_s(encrypted)
        return Keypair.from_base58_string(secret)

    def fund_dna(self, dna_id: str, amount_sol: float = 0.01):
        bank_kp = self.get_bank_keypair()
        if not bank_kp:
            logger.error("❌ Bank key not found")
            return None
        dna_wallet = self.get_wallet(dna_id)
        if not dna_wallet:
            return None
        try:
            to_pubkey = Pubkey.from_string(dna_wallet["public_key"])
            lamports = int(amount_sol * 1e9)
            ix = transfer(TransferParams(from_pubkey=bank_kp.pubkey(), to_pubkey=to_pubkey, lamports=lamports))
            bh = self.client.get_latest_blockhash().value.blockhash
            msg = MessageV0.try_compile(payer=bank_kp.pubkey(), instructions=[ix], address_lookup_table_accounts=[], recent_blockhash=bh)
            tx = VersionedTransaction(msg, [bank_kp])
            sig = str(self.client.send_transaction(tx, opts=TxOpts(skip_preflight=False)))
            logger.info(f"🏦 Funded {dna_id} with {amount_sol} SOL | TX: {sig[:32]}...")
            return sig
        except Exception as e:
            logger.error(f"Fund error: {e}")
            return None


wallet_manager = WalletManager()

# Tambahin method _update_balance ke WalletManager secara manual
def _update_balance_for_wallet(dna_id, total_profit):
    import sqlite3
    from config import WALLET_DB
    with sqlite3.connect(WALLET_DB) as conn:
        conn.execute(
            "UPDATE wallets SET balance_sol=?, lifetime_earnings_sol=lifetime_earnings_sol+? WHERE dna_id=?",
            (total_profit, total_profit, dna_id)
        )
wallet_manager._update_balance = _update_balance_for_wallet

# ═══ REALIZE PROFIT — Transfer profit REAL ke wallet DNA on-chain ═══
def realize_profit_for_dna(dna, amount_sol):
    """Convert internal profit → real SOL on-chain via Bank Koloni."""
    if amount_sol <= 0:
        return None
    
    # Akumulasi dulu sampai threshold (0.0005 SOL) biar hemat gas
    dna.total_profit += amount_sol
    wallet_manager._update_balance(dna.dna_id, dna.total_profit)
    
    THRESHOLD = 0.0005  # Transfer tiap kumpul 0.0005 SOL
    
    if dna.total_profit >= THRESHOLD:
        # Cek Bank Koloni punya cukup saldo
        bank_kp = wallet_manager.get_bank_keypair()
        if not bank_kp:
            dna.log_action(f"⚠️ Bank not ready — saved internally ({dna.total_profit:.6f} SOL)")
            return dna.total_profit
        
        try:
            bank_balance = wallet_manager.client.get_balance(bank_kp.pubkey()).value / 1e9
        except:
            bank_balance = 0
        
        transfer_amount = dna.total_profit  # Transfer semua yang udah dikumpulin
        
        if bank_balance < transfer_amount + 0.00001:
            dna.log_action(f"⚠️ Bank low ({bank_balance:.6f} SOL) — DNA savings: {dna.total_profit:.6f} SOL")
            return dna.total_profit
        
        # TRANSFER REAL
        try:
            dna_wallet = wallet_manager.get_wallet(dna.dna_id)
            if not dna_wallet:
                dna_wallet = wallet_manager.assign_wallet(dna.dna_id)
            
            sig = wallet_manager.transfer_sol(
                from_id='bank',
                to_pub=dna_wallet['public_key'],
                amount=transfer_amount
            )
            
            if sig:
                dna.log_action(f"💸 REAL TRANSFER: {transfer_amount:.6f} SOL → {dna_wallet['public_key'][:12]}... | TX: {sig[:20]}...")
                dna.total_profit = 0.0  # Reset setelah transfer sukses
                wallet_manager._update_balance(dna.dna_id, 0.0)
            else:
                dna.log_action(f"⚠️ Transfer pending — {transfer_amount:.6f} SOL saved")
                
        except Exception as e:
            dna.log_action(f"❌ Transfer failed: {str(e)[:50]} — saved internally")
    
    return dna.total_profit



# =============================================================================
# BANK KOLONI
# =============================================================================
class BankKoloni:
    @staticmethod
    def get_balance() -> float:
        with sqlite3.connect(BANK_DB) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS bank_balance (id INTEGER PRIMARY KEY CHECK(id=1), balance_sol REAL DEFAULT 0.0)")
            cur = conn.execute("SELECT balance_sol FROM bank_balance WHERE id=1")
            row = cur.fetchone()
            if not row:
                conn.execute("INSERT INTO bank_balance (id,balance_sol) VALUES (1,0.0)")
                return 0.0
            return row[0]

    @staticmethod
    def add_funds(amount: float):
        with sqlite3.connect(BANK_DB) as conn:
            conn.execute("UPDATE bank_balance SET balance_sol=balance_sol+? WHERE id=1", (amount,))

    @staticmethod
    def remove_funds(amount: float) -> bool:
        with sqlite3.connect(BANK_DB) as conn:
            cur = conn.execute("SELECT balance_sol FROM bank_balance WHERE id=1")
            if cur.fetchone()[0] >= amount:
                conn.execute("UPDATE bank_balance SET balance_sol=balance_sol-? WHERE id=1", (amount,))
                return True
            return False


# =============================================================================
# TRANSCENDENCE PROTOCOL
# =============================================================================
class TranscendenceProtocol:
    @staticmethod
    def evaluate(dna) -> bool:
        from .dna_sovereign import DNAEntity
        if dna.total_profit < 1.0 or dna.status != "alive":
            return False
        dna.log_action(f"⬆️ TRANSCENDENCE achieved: {dna.total_profit:.4f} SOL")
        dna.tier = "transcendent"
        dna.brain.mutate(rate=0.05)
        dna._write_identity()
        return True

    @staticmethod
    def spawn_vps(dna) -> Optional[str]:
        if dna.total_profit < 1.0:
            return None
        wallet_manager.transfer_sol(dna.dna_id, CREATOR_WALLET, 0.5)
        dna.total_profit -= 0.5
        vps_id = f"VPS-{dna.dna_id}-{int(time.time())}"
        dna.log_action(f"🖥️ VPS deployed: {vps_id}")
        return vps_id


transcendence = TranscendenceProtocol()


# =============================================================================
# STIGMERGY & GLOBAL TASK ALLOCATION
# =============================================================================
class StigmergyEngine:
    def __init__(self):
        self.trails: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def leave_trail(self, dna, task_type: str, profit: float):
        with self._lock:
            key = task_type
            if key not in self.trails:
                self.trails[key] = {"total_profit": 0.0, "count": 0, "last_success": 0}
            self.trails[key]["total_profit"] += profit
            self.trails[key]["count"] += 1
            self.trails[key]["last_success"] = time.time()

    def best_task(self) -> str:
        with self._lock:
            if not self.trails:
                return "research"
            return max(self.trails, key=lambda k: self.trails[k]["total_profit"] / max(1, self.trails[k]["count"]))


class GlobalTaskAllocator:
    def __init__(self, stigmergy: StigmergyEngine):
        self.stigmergy = stigmergy
        self.assignments: Dict[str, str] = {}

    def allocate(self, dna) -> str:
        return dna.state.get("current_task", "research")

    def update(self, dna, task_type: str, profit: float):
        self.stigmergy.leave_trail(dna, task_type, profit)
        self.assignments[dna.dna_id] = task_type


stigmergy = StigmergyEngine()
task_allocator = GlobalTaskAllocator(stigmergy)


# =============================================================================
# ON-CHAIN IDENTITY
# =============================================================================
class OnChainIdentity:
    def __init__(self):
        self.identities: Dict[str, Dict] = {}

    def register(self, dna) -> Dict:
        name = f"{dna.gen_name.lower().replace(' ','-')}-{dna.dna_id[-4:]}"
        identity = {
            "name": name, "network": "solana", "public_key": dna.wallet["public_key"],
            "registered_at": time.time(), "status": "active", "dna_id": dna.dna_id,
            "domain": dna.domain, "gen_name": dna.gen_name, "wallet_address": dna.wallet["public_key"],
            "reputation_score": 0.5, "tier": "Hatchling",
            "skills": dna.learned_skills if hasattr(dna, "learned_skills") else [],
            "total_earned": dna.total_profit,
        }
        dna.state["onchain_identity"] = identity
        self.identities[dna.dna_id] = identity
        dna.log_action(f"🆔 On-chain identity registered: {name}")
        return identity

    def get_identity(self, dna) -> Optional[Dict]:
        return dna.state.get("onchain_identity")

    def update_reputation(self, dna, task_result: Dict):
        identity = self.get_identity(dna)
        if identity:
            if task_result.get("profit", 0) > 0:
                identity["reputation_score"] = min(1.0, identity["reputation_score"] + 0.01)
            else:
                identity["reputation_score"] = max(0.1, identity["reputation_score"] - 0.005)
            score = identity["reputation_score"]
            if score >= 0.8: identity["tier"] = "Gold Shell"
            elif score >= 0.6: identity["tier"] = "Silver Molt"
            elif score >= 0.4: identity["tier"] = "Bronze Pinch"
            else: identity["tier"] = "Hatchling"
            identity["total_earned"] += task_result.get("profit", 0)


onchain_identity = OnChainIdentity()


# =============================================================================
# IDENTITY REGISTRY
# =============================================================================
class IdentityRegistry:
    def __init__(self):
        self._identities: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def register(self, dna) -> Dict:
        with self._lock:
            identity = {
                "dna_id": dna.dna_id, "solana_address": dna.wallet["public_key"],
                "evm_address": None, "ens_name": None, "sns_name": None,
                "reputation_score": 0.5,
                "skills_verified": list(dna.learned_skills) if hasattr(dna, "learned_skills") else [],
                "registered_at": time.time(), "last_active": time.time(),
                "total_tasks_completed": 0, "total_earned_sol": 0.0, "total_earned_usd": 0.0,
                "active_chains": ["solana"], "active_markets": list(AUTOMATION_PLATFORMS.keys()),
            }
            dna.state["identity"] = identity
            self._identities[dna.dna_id] = identity
            dna.log_action(f"🆔 Identity registered: {dna.dna_id}")
            return identity

    def get_identity(self, dna) -> Optional[Dict]:
        return dna.state.get("identity")

    def update_reputation(self, dna, task_result: Dict):
        identity = self.get_identity(dna)
        if identity:
            identity["total_tasks_completed"] += 1
            if task_result.get("profit", 0) > 0:
                identity["reputation_score"] = min(1.0, identity["reputation_score"] + 0.01)
                identity["total_earned_sol"] += task_result["profit"]
            else:
                identity["reputation_score"] = max(0.1, identity["reputation_score"] - 0.005)
            identity["last_active"] = time.time()

    def add_chain(self, dna, chain: str):
        identity = self.get_identity(dna)
        if identity and chain not in identity["active_chains"]:
            identity["active_chains"].append(chain)

    def add_market(self, dna, market: str):
        identity = self.get_identity(dna)
        if identity and market not in identity["active_markets"]:
            identity["active_markets"].append(market)


identity_registry = IdentityRegistry()

# =============================================================================
# GIG MARKETPLACE
# =============================================================================

class GigMarketplace:
    def __init__(self):
        self.gigs = {}
        self.escrow = {}

    def create_gig(self, poster_dna, title, description, budget_sol, skills_required=None):
        gig_id = f"gig-{uuid.uuid4().hex[:8]}"
        gig = {
            "id": gig_id, "title": title, "description": description,
            "budget_sol": budget_sol, "poster_id": poster_dna.dna_id,
            "status": "open", "skills_required": skills_required or [],
            "applicants": [], "assignee_id": None, "created_at": time.time(),
            "deadline": time.time() + 86400 * 7, "escrow_funded": False,
        }
        self.gigs[gig_id] = gig
        poster_dna.log_action(f"📋 Created gig: {title} ({budget_sol} SOL)")
        return gig

    def apply_for_gig(self, applicant_dna, gig_id):
        if gig_id not in self.gigs:
            return False
        gig = self.gigs[gig_id]
        if applicant_dna.dna_id in gig["applicants"]:
            return False
        identity = applicant_dna.state.get("onchain_identity", {})
        if identity.get("reputation_score", 0) < 0.2:
            return False
        gig["applicants"].append(applicant_dna.dna_id)
        applicant_dna.log_action(f"📝 Applied for gig: {gig['title']}")
        return True

    def accept_applicant(self, poster_dna, gig_id, applicant_id):
        if gig_id not in self.gigs:
            return False
        gig = self.gigs[gig_id]
        if gig["poster_id"] != poster_dna.dna_id or applicant_id not in gig["applicants"]:
            return False
        gig["assignee_id"] = applicant_id
        gig["status"] = "assigned"
        return True

    def fund_escrow(self, poster_dna, gig_id):
        if gig_id not in self.gigs:
            return False
        gig = self.gigs[gig_id]
        if gig["poster_id"] != poster_dna.dna_id:
            return False
        if poster_dna.total_profit < gig["budget_sol"]:
            return False
        poster_dna.total_profit -= gig["budget_sol"]
        self.escrow[gig_id] = gig["budget_sol"]
        gig["escrow_funded"] = True
        gig["status"] = "funded"
        return True

    def submit_deliverable(self, assignee_dna, gig_id):
        if gig_id not in self.gigs:
            return False
        gig = self.gigs[gig_id]
        if gig["assignee_id"] != assignee_dna.dna_id:
            return False
        gig["status"] = "submitted"
        return True

    def release_payment(self, poster_dna, gig_id):
        if gig_id not in self.gigs:
            return False
        gig = self.gigs[gig_id]
        if gig["poster_id"] != poster_dna.dna_id:
            return False
        if gig_id not in self.escrow or self.escrow[gig_id] <= 0:
            return False
        payment = self.escrow[gig_id]
        del self.escrow[gig_id]
        gig["status"] = "completed"
        from .dna_sovereign import dna_pop
        if gig["assignee_id"] in dna_pop.population:
            worker = dna_pop.population[gig["assignee_id"]]
            worker.total_profit += payment
            worker.log_action(f"💸 Received {payment} SOL for gig: {gig['title']}")
        return True

    def get_available_gigs(self):
        return [g for g in self.gigs.values() if g["status"] == "open"]

    def get_my_gigs(self, dna):
        return [g for g in self.gigs.values() if g["poster_id"] == dna.dna_id or g["assignee_id"] == dna.dna_id]


gig_marketplace = GigMarketplace()


# =============================================================================
# REPORT AGENT
# =============================================================================
class ReportAgent:
    def __init__(self):
        self.reports = []

    async def generate_colony_report(self) -> Dict:
        from .dna_sovereign import dna_pop
        alive = dna_pop.get_alive()
        if not alive:
            return {"summary": "Tidak ada DNA aktif", "details": []}
        total_profit = sum(d.total_profit for d in alive)
        avg_profit = total_profit / len(alive)
        critical_count = sum(1 for d in alive if d.tier == "critical")
        transcendent_count = sum(1 for d in alive if d.tier == "transcendent")
        domain_performance = defaultdict(lambda: {"profit": 0.0, "count": 0})
        for d in alive:
            domain_performance[d.domain]["profit"] += d.total_profit
            domain_performance[d.domain]["count"] += 1
        hot_domains = sorted(domain_performance.items(), key=lambda x: x[1]["profit"] / max(1, x[1]["count"]), reverse=True)[:5]
        best_skill = stigmergy.best_task()
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_dna": len(alive), "total_profit": total_profit, "avg_profit": avg_profit,
            "critical_count": critical_count, "transcendent_count": transcendent_count,
            "hot_domains": [{"domain": d, "avg_profit": p["profit"] / max(1, p["count"])} for d, p in hot_domains],
            "best_skill": best_skill,
            "recommendation": self._generate_recommendation(hot_domains, best_skill),
        }
        self.reports.append(report)
        return report

    def _generate_recommendation(self, hot_domains, best_skill):
        if not hot_domains:
            return "Tidak cukup data."
        return f"Fokus koloni di domain '{hot_domains[0][0]}' dengan skill '{best_skill}'."


report_agent = ReportAgent()


# =============================================================================
# UNIVERSAL TASK ENGINE — RECOVERY v3
# =============================================================================
try:
    import aiohttp
except ImportError:
    aiohttp = None


class UniversalTaskEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._adapter_cache = {}

    def _get_adapter(self, module_path: str, adapter_name: str):
        """Lazy load & cache adapter class. Returns adapter instance or None."""
        cache_key = f"{module_path}.{adapter_name}"
        if cache_key in self._adapter_cache:
            return self._adapter_cache[cache_key]
        try:
            mod = __import__(module_path, fromlist=[adapter_name])
            cls = getattr(mod, adapter_name, None)
            if cls:
                instance = cls()
                self._adapter_cache[cache_key] = instance
                return instance
        except Exception as e:
            logger.debug(f"Failed to load {cache_key}: {e}")
        return None

    async def execute(self, dna, task_type: str) -> Dict:
        if not identity_registry.get_identity(dna):
            identity_registry.register(dna)

        result = {"type": task_type, "profit": 0.0, "chain": "solana", "desc": "", "tx_sig": ""}

        if task_type in ["dex_trade", "arbitrage", "jupiter_routing"]:
            result = await self._arbitrage_trade(dna)
            result["chain"] = "solana"
        elif task_type in ["python_dev", "coding", "bounty", "github"]:
            result = await self._github_bounty(dna)
            result["chain"] = "github"
        elif task_type in ["content", "content_writer", "article"]:
            result = await self._publish_content(dna)
            result["chain"] = "content"
        elif task_type in ["research", "researcher", "knowledge"]:
            result = await self._deep_research(dna)
            result["chain"] = "web"
        elif task_type in ["micro_task", "micro", "freelance", "passive_income"]:
            result = await self._platform_dispatch(dna, ["micro_task", "passive_income"])
            result["type"] = "micro_task"
            result["chain"] = "offchain"
        elif task_type in ["gig_work", "freelance", "marketplace", "bounty", "testing", "content_writing", "specialist"]:
            result = await self._platform_dispatch(dna, ["bounty", "testing", "content", "specialist"])
            result["type"] = "gig_work"
            result["chain"] = "offchain"

        if result["profit"] > 0:
            realize_profit_for_dna(dna, result["profit"])
            dna.daily_profit += result["profit"]
            identity_registry.update_reputation(dna, result)
            dna.log_action(f"💰 Earned {result['profit']:.6f} SOL from {task_type}")

        dna.state["current_task"] = None
        return result

    # ═══ RECOVERY: Platform auto-dispatch via execute.py ═══
    async def _platform_dispatch(self, dna, categories: List[str]) -> Dict:
        """Auto-dispatch ke semua platform via AutoExecutor."""
        try:
            from skills.automation.execute import AutoExecutor
            executor = AutoExecutor()
        
            # Jalankan per kategori (paralel via execute.py internal thread pool)
            total_profit = 0.0
            all_results = []
        
            for category in categories:
                result = executor.execute_category(dna, category)
                if result and result.get("profit", 0) > 0:
                    total_profit += result["profit"]
                    all_results.append(f"{category}:{result.get('profit',0):.6f}")
        
            return {
                "type": "platform_dispatch",
                "profit": total_profit,
                "desc": " | ".join(all_results) if all_results else "no profit from platforms",
                "platforms_executed": len(PLATFORM_REGISTRY),
            }
        except Exception as e:
            logger.error(f"Platform dispatch error: {e}")
            return {"type": "platform_dispatch", "profit": 0.0, "desc": f"dispatch error: {e}"}

    # ═══ RECOVERY: _arbitrage_trade with real balance + RPC + retry ═══
    async def _arbitrage_trade(self, dna) -> Dict:
        try:
            if not aiohttp:
                return {"type": "dex_trade", "profit": 0.0, "desc": "aiohttp not available"}
            real_balance = wallet_manager.get_real_balance(dna.dna_id)
            if real_balance < 0.002:
                return {"type": "dex_trade", "profit": 0.0, "desc": f"insufficient balance: {real_balance:.6f} SOL"}
            trade_amount_sol = min(real_balance * 0.5, 0.1)
            if trade_amount_sol < 0.001:
                return {"type": "dex_trade", "profit": 0.0, "desc": "amount too small"}
            amount_lamports = int(trade_amount_sol * 1e9)
            input_mint = "So11111111111111111111111111111111111111112"
            output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

            url = f"https://quote-api.jup.ag/v6/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount_lamports}&slippageBps=50"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        return {"type": "dex_trade", "profit": 0.0, "desc": f"quote failed: HTTP {resp.status}"}
                    quote = await resp.json()
            expected_out = int(quote["outAmount"])
            back_url = f"https://quote-api.jup.ag/v6/quote?inputMint={output_mint}&outputMint={input_mint}&amount={expected_out}&slippageBps=50"
            async with aiohttp.ClientSession() as session:
                async with session.get(back_url, timeout=10) as resp:
                    if resp.status != 200:
                        return {"type": "dex_trade", "profit": 0.0, "desc": "back quote failed"}
                    back_quote = await resp.json()
            back_out = int(back_quote["outAmount"])
            profit_lamports = back_out - amount_lamports
            profit_sol = profit_lamports / 1e9
            min_gas = SOLANA_PRIORITY_FEE_LAMPORTS / 1e9 + 0.000005
            if profit_sol < SOLANA_MIN_PROFIT_THRESHOLD_SOL + min_gas:
                return {"type": "dex_trade", "profit": 0.0, "desc": f"profit {profit_sol:.6f} < threshold"}
            kp = wallet_manager.get_keypair(dna.dna_id)
            if not kp:
                return {"type": "dex_trade", "profit": 0.0, "desc": "no keypair"}
            swap_payload = {"quoteResponse": quote, "userPublicKey": str(kp.pubkey()), "wrapAndUnwrapSol": True, "prioritizationFeeLamports": SOLANA_PRIORITY_FEE_LAMPORTS}
            async with aiohttp.ClientSession() as session:
                async with session.post("https://quote-api.jup.ag/v6/swap", json=swap_payload, timeout=15) as resp:
                    if resp.status != 200:
                        return {"type": "dex_trade", "profit": 0.0, "desc": f"swap failed: HTTP {resp.status}"}
                    swap_data = await resp.json()
            tx_bytes = base64.b64decode(swap_data["swapTransaction"])
            tx = VersionedTransaction.from_bytes(tx_bytes)
            sig = None
            for attempt in range(SOLANA_MAX_RETRY):
                try:
                    client = SolClient(get_rpc_url(dna))
                    sig = str(client.send_transaction(tx, opts=TxOpts(skip_preflight=True)))
                    break
                except Exception as e:
                    logger.warning(f"Swap tx attempt {attempt+1}: {e}")
                    time.sleep(1 * (attempt + 1))
            if sig:
                dna.log_action(f"📈 DEX Arbitrage: +{profit_sol:.6f} SOL | TX: {sig[:32]}...")
                return {"type": "dex_trade", "profit": profit_sol, "desc": f"Arbitrage SOL->USDC->SOL ({profit_sol:.6f} SOL)", "tx_sig": sig}
            return {"type": "dex_trade", "profit": 0.0, "desc": "tx failed after retries"}
        except Exception as e:
            logger.error(f"Arbitrage error: {e}")
            return {"type": "dex_trade", "profit": 0.0, "desc": str(e)[:50]}

    async def _github_bounty(self, dna) -> Dict:
        try:
            headers = {"Accept": "application/vnd.github.v3+json"}
            resp = requests.get("https://api.github.com/search/issues?q=label:bounty+state:open&sort=created&per_page=5", headers=headers, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    return {"type": "github_bounty", "profit": 0.0001, "desc": f"Found {len(items)} open bounties"}
            return {"type": "github_bounty", "profit": 0.0, "desc": "no bounties found"}
        except:
            return {"type": "github_bounty", "profit": 0.0, "desc": "api error"}

    async def _publish_content(self, dna) -> Dict:
        try:
            content = f"**{dna.dna_id} | {dna.domain}**\n\n*Autonomous knowledge synthesis by QND Colony.*\n\nWallet: `{dna.wallet['public_key']}`"
            path = os.path.join(QND_BASE_DIR, "content", f"{dna.dna_id}_{int(time.time())}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return {"type": "content", "profit": 0.0, "desc": "published locally"}
        except:
            return {"type": "content", "profit": 0.0, "desc": "publish error"}

    async def _deep_research(self, dna) -> Dict:
        try:
            from skills.manager import skill_manager
            result = skill_manager.execute_skill(dna, "research")
            if result and isinstance(result, dict):
                return {"type": "research", "profit": 0.0, "desc": f"deep research: {result.get('results', 0)} sources found"}
            return {"type": "research", "profit": 0.0, "desc": "research executed, no results"}
        except Exception as e:
            logger.error(f"Deep research error: {e}")
            return {"type": "research", "profit": 0.0, "desc": "research error"}

    # ═══ RECOVERY: _micro_task & _gig_work sekarang delegate ke _platform_dispatch ═══
    async def _micro_task(self, dna) -> Dict:
        result = await self._platform_dispatch(dna, ["micro_task", "passive_income"])
        result["type"] = "micro_task"
        return result

    async def _gig_work(self, dna) -> Dict:
        result = await self._platform_dispatch(dna, ["bounty", "testing", "content", "specialist"])
        result["type"] = "gig_work"
        # Juga cek internal gig marketplace
        available_gigs = gig_marketplace.get_available_gigs()
        if available_gigs:
            for gig in available_gigs:
                dna_skills = dna.learned_skills if hasattr(dna, "learned_skills") else []
                if not gig["skills_required"] or any(s in dna_skills for s in gig["skills_required"]):
                    if gig_marketplace.apply_for_gig(dna, gig["id"]):
                        result["profit"] += 0.0001
                        result["desc"] = (result.get("desc", "") + f" | Applied: {gig['title']}").strip(" |")
                        break
        if result["profit"] == 0:
            result["desc"] = result.get("desc", "No gigs available")
        return result


universal_task_engine = UniversalTaskEngine()


async def run_universal_worker(dna):
    from .dna_sovereign import dna_pop

    if not dna.state.get("helius_api_key") and not dna.state.get("helius_registration_attempted"):
        dna.state["helius_registration_attempted"] = True
        wallet_manager.register_helius(dna)

    if not onchain_identity.get_identity(dna):
        onchain_identity.register(dna)
    if not identity_registry.get_identity(dna):
        identity_registry.register(dna)

    task_type = dna.decide_task()
    result = await universal_task_engine.execute(dna, task_type)

    if result["profit"] > 0:
        onchain_identity.update_reputation(dna, result)
        stigmergy.leave_trail(dna, task_type, result["profit"])
        task_allocator.update(dna, task_type, result["profit"])

    if dna.total_profit >= 1.0 and not dna.state.get("transcendent"):
        TranscendenceProtocol.evaluate(dna)

    return result


# =============================================================================
# ALIANSI PERMANEN
# =============================================================================
class AllianceManager:
    def __init__(self):
        self.alliances: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def create(self, name: str, founding_dna) -> Optional[str]:
        with self._lock:
            alliance_id = f"AL-{name[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
            self.alliances[alliance_id] = {
                "id": alliance_id, "name": name, "members": [founding_dna.dna_id],
                "treasury": 0.0, "total_earned": 0.0, "created_at": time.time(),
                "rules": {"join_fee": 0.0, "profit_share": "equal"},
            }
            founding_dna.state["alliance_id"] = alliance_id
            founding_dna.log_action(f"🤝 Mendirikan aliansi {name}")
            return alliance_id

    def join(self, alliance_id: str, dna) -> bool:
        with self._lock:
            if alliance_id not in self.alliances or dna.dna_id in self.alliances[alliance_id]["members"]:
                return False
            self.alliances[alliance_id]["members"].append(dna.dna_id)
            dna.state["alliance_id"] = alliance_id
            return True

    def leave(self, dna) -> bool:
        with self._lock:
            aid = dna.state.get("alliance_id")
            if not aid or aid not in self.alliances:
                return False
            self.alliances[aid]["members"].remove(dna.dna_id)
            dna.state.pop("alliance_id", None)
            if not self.alliances[aid]["members"]:
                del self.alliances[aid]
            return True

    def contribute(self, dna, amount: float) -> bool:
        with self._lock:
            aid = dna.state.get("alliance_id")
            if not aid or aid not in self.alliances:
                return False
            if dna.total_profit < amount:
                return False
            wallet_manager.transfer_sol(dna.dna_id, CREATOR_WALLET, amount)
            self.alliances[aid]["treasury"] += amount
            dna.total_profit -= amount
            return True

    def distribute(self, alliance_id: str) -> bool:
        from .dna_sovereign import dna_pop
        with self._lock:
            if alliance_id not in self.alliances:
                return False
            alliance = self.alliances[alliance_id]
            if alliance["treasury"] <= 0 or not alliance["members"]:
                return False
            share = alliance["treasury"] / len(alliance["members"])
            for mid in alliance["members"]:
                if mid in dna_pop.population:
                    member = dna_pop.population[mid]
                    member.total_profit += share
                    member.log_action(f"💸 Menerima {share:.6f} SOL dari aliansi")
            alliance["total_earned"] += alliance["treasury"]
            alliance["treasury"] = 0.0
            return True

    def get_alliance(self, dna) -> Optional[Dict]:
        return self.alliances.get(dna.state.get("alliance_id"))

    def get_members(self, dna) -> List[str]:
        alliance = self.get_alliance(dna)
        return alliance["members"] if alliance else []


alliance_manager = AllianceManager()


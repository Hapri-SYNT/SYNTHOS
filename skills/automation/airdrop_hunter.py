import time, random, json, os
from typing import Dict
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc.core import RPCException
from solders.system_program import transfer, TransferParams
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
import base64

class AirdropHunter:
    def __init__(self):
        self.testnet_client = Client("https://api.testnet.solana.com")
        self.devnet_client = Client("https://api.devnet.solana.com")
        self.testnet_programs = {
            "jupiter": "JUP4Fb2cqiRUcaTH9wfvL1YCaiibpMPVRveqLxEAGPU",
            "drift": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
            "marginfi": "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA",
        }
        self.airdrop_history = []

    def execute(self, dna) -> Dict:
        wallet = dna.wallet.get("public_key", "")
        try:
            kp = self._get_keypair(dna)
            if not kp: return {"profit": 0, "desc": "No keypair"}

            pubkey = kp.pubkey()
            results = []
            
            # 1. Minta SOL testnet gratis
            dna.log_action("💧 Requesting SOL airdrop...")
            try:
                tx_sig = self.devnet_client.request_airdrop(pubkey, 1_000_000_000).value
                dna.log_action(f"💧 Airdrop: {str(tx_sig)[:16]}...")
                results.append("sol_airdrop")
            except Exception as e:
                dna.log_action(f"⚠️ Airdrop: {e}")

            # 2. Kirim transaksi ke diri sendiri (testnet)
            dna.log_action("📤 Sending test transaction...")
            try:
                bh = self.testnet_client.get_latest_blockhash().value.blockhash
                ix = transfer(TransferParams(from_pubkey=pubkey, to_pubkey=pubkey, lamports=1000))
                msg = MessageV0.try_compile(payer=pubkey, instructions=[ix], address_lookup_table_accounts=[], recent_blockhash=bh)
                tx = VersionedTransaction(msg, [kp])
                sig = self.testnet_client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value
                dna.log_action(f"📤 TX: {str(sig)[:16]}...")
                results.append("test_transaction")
            except Exception as e:
                dna.log_action(f"⚠️ TX: {e}")

            # 3. Interaksi dengan program testnet (Jupiter)
            dna.log_action("🔁 Interacting with Jupiter testnet...")
            try:
                bh = self.testnet_client.get_latest_blockhash().value.blockhash
                jup_program = Pubkey.from_string(self.testnet_programs["jupiter"])
                ix = transfer(TransferParams(from_pubkey=pubkey, to_pubkey=jup_program, lamports=1))
                msg = MessageV0.try_compile(payer=pubkey, instructions=[ix], address_lookup_table_accounts=[], recent_blockhash=bh)
                tx = VersionedTransaction(msg, [kp])
                sig = self.testnet_client.send_transaction(tx, opts=TxOpts(skip_preflight=True)).value
                dna.log_action(f"🔁 Jupiter: {str(sig)[:16]}...")
                results.append("jupiter_interaction")
            except Exception as e:
                dna.log_action(f"⚠️ Jupiter: {e}")

            self.airdrop_history.append({"time": time.time(), "results": results, "wallet": str(pubkey)})
            
            return {
                "type": "airdrop_hunting",
                "profit": 0,
                "actions": len(results),
                "desc": f"Real testnet: {', '.join(results)}",
                "chain": "solana-testnet",
                "real": True,
            }
        except Exception as e:
            dna.log_action(f"❌ Airdrop error: {e}")
            return {"profit": 0, "desc": str(e)[:50]}

    def _get_keypair(self, dna):
        try:
            from core.economy import wallet_manager
            return wallet_manager.get_keypair(dna.dna_id)
        except:
            return None

airdrop_hunter = AirdropHunter()

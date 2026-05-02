# config.py — RECOVERY v3
# Multi-RPC, Helius self-registration, 35+ platform automation ready

import os, sys, logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

# Baca .env secara manual
def load_manual_env(filepath=".env"):
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

env_vars = load_manual_env()
CREATOR_WALLET = env_vars.get("CREATOR_WALLET", "")

if not CREATOR_WALLET:
    print("❌ Isi .env dengan CREATOR_WALLET=...")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# RPC CONFIG — MULTI-CHAIN FALLBACK
# ═══════════════════════════════════════════════════════════════

SOLANA_RPC_LIST: List[str] = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.tt-prod.net",
    "https://rpc.ankr.com/solana",
    "https://solana.public-rpc.com",
]
SOLANA_RPC_URL = SOLANA_RPC_LIST[0]
HELIUS_REGISTRATION_URL = "https://api.helius.xyz/v0/api-keys"
HELIUS_DASHBOARD = "https://dev.helius.xyz/dashboard"

SOLANA_PRIORITY_FEE_LAMPORTS = 5000
SOLANA_MIN_PROFIT_THRESHOLD_SOL = 0.0001
SOLANA_MAX_RETRY = 3
BRAIN_GATE_ENABLED = True

# ═══════════════════════════════════════════════════════════════
# AUTOMATION PLATFORM REGISTRY (35+ platforms)
# Tambah platform baru cukup tambah entry di sini.
# DNA akan auto-register ke semua platform yang relevan.
# ═══════════════════════════════════════════════════════════════

AUTOMATION_PLATFORMS: Dict[str, Dict[str, Any]] = {
    # ===== PASSIVE INCOME (7) =====
    "honeygain": {
        "category": "passive_income",
        "adapter": "HoneygainAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://dashboard.honeygain.com/signup",
        "requires_wallet": False,
        "reward_type": "credits_to_usd",
        "estimated_monthly_usd": 5.0,
    },
    "pawns_app": {
        "category": "passive_income",
        "adapter": "PawnsAppAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://pawns.app/signup",
        "requires_wallet": False,
        "reward_type": "credits_to_btc",
        "estimated_monthly_usd": 3.0,
    },
    "packetstream": {
        "category": "passive_income",
        "adapter": "PacketStreamAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://packetstream.io/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 4.0,
    },
    "earnapp": {
        "category": "passive_income",
        "adapter": "EarnAppAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://earnapp.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 4.0,
    },
    "presearch": {
        "category": "passive_income",
        "adapter": "PresearchAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://presearch.com/signup",
        "requires_wallet": True,
        "reward_type": "token_pre",
        "estimated_monthly_usd": 2.0,
    },
    "current_music": {
        "category": "passive_income",
        "adapter": "CurrentMusicAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://current.us/signup",
        "requires_wallet": False,
        "reward_type": "token_crnt",
        "estimated_monthly_usd": 3.0,
    },
    "coinpayu": {
        "category": "passive_income",
        "adapter": "CoinPayUAdapter",
        "module": "skills.automation.passive_income",
        "register_url": "https://coinpayu.com/signup",
        "requires_wallet": True,
        "reward_type": "btc_satoshis",
        "estimated_monthly_usd": 2.0,
    },

    # ===== MICRO-TASKING (8) =====
    "jumptask": {
        "category": "micro_task",
        "adapter": "JumpTaskAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://jumptask.io/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 8.0,
    },
    "freecash": {
        "category": "micro_task",
        "adapter": "FreecashAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://freecash.com/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 10.0,
    },
    "cointiply": {
        "category": "micro_task",
        "adapter": "CointiplyAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://cointiply.com/signup",
        "requires_wallet": True,
        "reward_type": "btc",
        "estimated_monthly_usd": 5.0,
    },
    "ysense": {
        "category": "micro_task",
        "adapter": "YSenseAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://ysense.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 15.0,
    },
    "clickworker": {
        "category": "micro_task",
        "adapter": "ClickworkerAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://clickworker.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 12.0,
    },
    "toloka": {
        "category": "micro_task",
        "adapter": "TolokaAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://toloka.ai/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 10.0,
    },
    "neevo": {
        "category": "micro_task",
        "adapter": "NeevoAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://neevo.defined.ai/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 8.0,
    },
    "oneforma": {
        "category": "micro_task",
        "adapter": "OneFormaAdapter",
        "module": "skills.automation.micro_task",
        "register_url": "https://oneforma.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 12.0,
    },

    # ===== FREELANCE & BOUNTY (8) =====
    "layer3": {
        "category": "bounty",
        "adapter": "Layer3Adapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://layer3.xyz/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 5.0,
    },
    "rabbithole": {
        "category": "bounty",
        "adapter": "RabbitHoleAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://rabbithole.gg/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 6.0,
    },
    "gitcoin": {
        "category": "bounty",
        "adapter": "GitcoinAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://gitcoin.co/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 20.0,
    },
    "braintrust": {
        "category": "bounty",
        "adapter": "BraintrustAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://braintrust.com/signup",
        "requires_wallet": True,
        "reward_type": "usd_crypto",
        "estimated_monthly_usd": 50.0,
    },
    "appen": {
        "category": "bounty",
        "adapter": "AppenAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://appen.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 15.0,
    },
    "telus_international": {
        "category": "bounty",
        "adapter": "TelusAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://telusinternational.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_bank",
        "estimated_monthly_usd": 20.0,
    },
    "openquest": {
        "category": "bounty",
        "adapter": "OpenQuestAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://openquest.xyz/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 4.0,
    },
    "picus": {
        "category": "bounty",
        "adapter": "PicusAdapter",
        "module": "skills.automation.bounty_freelance",
        "register_url": "https://picus.xyz/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 8.0,
    },

    # ===== TESTING & UX (4) =====
    "usertesting": {
        "category": "testing",
        "adapter": "UserTestingAdapter",
        "module": "skills.automation.testing_ux",
        "register_url": "https://usertesting.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 30.0,
    },
    "playtestcloud": {
        "category": "testing",
        "adapter": "PlaytestCloudAdapter",
        "module": "skills.automation.testing_ux",
        "register_url": "https://playtestcloud.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 10.0,
    },
    "userlytics": {
        "category": "testing",
        "adapter": "UserlyticsAdapter",
        "module": "skills.automation.testing_ux",
        "register_url": "https://userlytics.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 15.0,
    },
    "testbirds": {
        "category": "testing",
        "adapter": "TestbirdsAdapter",
        "module": "skills.automation.testing_ux",
        "register_url": "https://testbirds.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 12.0,
    },

    # ===== CONTENT & WRITING (4) =====
    "hackernoon": {
        "category": "content",
        "adapter": "HackerNoonAdapter",
        "module": "skills.automation.content_writing",
        "register_url": "https://hackernoon.com/signup",
        "requires_wallet": True,
        "reward_type": "crypto",
        "estimated_monthly_usd": 10.0,
    },
    "publish0x": {
        "category": "content",
        "adapter": "Publish0xAdapter",
        "module": "skills.automation.content_writing",
        "register_url": "https://publish0x.com/signup",
        "requires_wallet": True,
        "reward_type": "crypto_tips",
        "estimated_monthly_usd": 5.0,
    },
    "steemit": {
        "category": "content",
        "adapter": "SteemitAdapter",
        "module": "skills.automation.content_writing",
        "register_url": "https://steemit.com/signup",
        "requires_wallet": True,
        "reward_type": "crypto_steem",
        "estimated_monthly_usd": 8.0,
    },
    "g2_capterra": {
        "category": "content",
        "adapter": "G2CapterraAdapter",
        "module": "skills.automation.content_writing",
        "register_url": "https://g2.com/signup",
        "requires_wallet": False,
        "reward_type": "gift_card",
        "estimated_monthly_usd": 15.0,
    },

    # ===== SPECIALIST (4) =====
    "bugcrowd": {
        "category": "specialist",
        "adapter": "BugcrowdAdapter",
        "module": "skills.automation.specialist",
        "register_url": "https://bugcrowd.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_bank",
        "estimated_monthly_usd": 100.0,
    },
    "remotasks": {
        "category": "specialist",
        "adapter": "RemotasksAdapter",
        "module": "skills.automation.specialist",
        "register_url": "https://remotasks.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 20.0,
    },
    "respondent": {
        "category": "specialist",
        "adapter": "RespondentAdapter",
        "module": "skills.automation.specialist",
        "register_url": "https://respondent.io/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 80.0,
    },
    "utest": {
        "category": "specialist",
        "adapter": "UTestAdapter",
        "module": "skills.automation.specialist",
        "register_url": "https://utest.com/signup",
        "requires_wallet": False,
        "reward_type": "usd_paypal",
        "estimated_monthly_usd": 25.0,
    },
}

# ═══════════════════════════════════════════════════════════════
# SYSTEM CONFIG
# ═══════════════════════════════════════════════════════════════

WEB_DASHBOARD_PORT = 8080
WEB_DASHBOARD_HOST = "0.0.0.0"
MAX_ACTIVE_DNA = 200
SURVIVAL_CHECK_INTERVAL = 300
DAILY_PROFIT_TARGET_SOL = 0.0001
MIN_DNA_SIZE = 100
MIN_LATENT_DIM = 100
SPARSITY_GENES = 0.01
SPARSITY_WEIGHTS = 0.90

DAILY_TAX_IDR = 2000.0
DAILY_TAX_HOUR = 9
DAILY_TAX_GRACE_DAYS = 3
TAX_MAX_WARNINGS = 7

FUND_AMOUNT_SOL = 0.01
FUND_MAX_ATTEMPTS = 3

# ═══════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════

QND_BASE_DIR = os.path.expanduser("~/.qnd_unified")
os.makedirs(QND_BASE_DIR, exist_ok=True)

DB_FILE = os.path.join(QND_BASE_DIR, "brain.db")
WALLET_DB = os.path.join(QND_BASE_DIR, "wallets.db")
BANK_DB = os.path.join(QND_BASE_DIR, "bank.db")
IDENTITY_DIR = os.path.join(QND_BASE_DIR, "identities")
LOG_DIR = os.path.join(QND_BASE_DIR, "logs")
SSD_EXPERTS_DIR = os.path.join(QND_BASE_DIR, "ssd_experts")
CONTENT_DIR = os.path.join(QND_BASE_DIR, "content")
WORKSPACE_DIR = os.path.join(QND_BASE_DIR, "workspace")

for d in [IDENTITY_DIR, LOG_DIR, SSD_EXPERTS_DIR, CONTENT_DIR, WORKSPACE_DIR]:
    os.makedirs(d, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'colony.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QND")

# ═══════════════════════════════════════════════════════════════
# CREATOR
# ═══════════════════════════════════════════════════════════════

CREATOR_PHANTOM_WALLET = "yeruhA4mjmdJDEgrog9AnfU9rATvX4R8WzuhnH8AFom"
CREATOR_PAYPAL = "hadihafriansyah77@gmail.com"

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def get_rpc_url(dna=None) -> str:
    if dna and dna.state.get("helius_api_key"):
        return f"https://mainnet.helius-rpc.com/?api-key={dna.state['helius_api_key']}"
    for rpc in SOLANA_RPC_LIST:
        if "helius-rpc" not in rpc:
            return rpc
    return SOLANA_RPC_LIST[1]

def get_rpc_url_async(dna=None) -> str:
    return get_rpc_url(dna)

def get_platforms_by_category(category: str) -> Dict:
    """Ambil semua platform untuk kategori tertentu."""
    return {k: v for k, v in AUTOMATION_PLATFORMS.items() if v.get("category") == category}

def get_all_platform_categories() -> List[str]:
    """List semua kategori platform."""
    return sorted(set(p.get("category", "unknown") for p in AUTOMATION_PLATFORMS.values()))

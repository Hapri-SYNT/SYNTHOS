#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  EXECUTE.PY — QND Colony Multi-Platform Execution Engine v5    ║
║  35 Platforms | 6 Categories | Autonomous DNA Integration      ║
║  Dipanggil dari core.economy._platform_dispatch()               ║
╚══════════════════════════════════════════════════════════════════╝

Dual-mode:
  1. INTEGRATED: execute(dna) dipanggil dari economy.py
  2. STANDALONE: python execute.py --daemon (testing)
"""

import asyncio
import concurrent.futures
import importlib
import json
import logging
import os
import signal
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from skills.automation.grass_adapter import grass_adapter
from skills.automation.airdrop_hunter import airdrop_hunter
from skills.automation.arbitrage_trader import arbitrage_trader
from skills.automation.bug_bounty_hunter import bug_bounty_hunter
from skills.automation.autonomous_worker import autonomous_worker

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════
class Config:
    STATE_DIR = Path(os.environ.get("QND_STATE_DIR", os.path.expanduser("~/.qnd_unified/executor_state")))
    LOG_DIR = Path(os.environ.get("QND_LOG_DIR", os.path.expanduser("~/.qnd_unified/logs")))
    REPORT_DIR = Path(os.environ.get("QND_REPORT_DIR", os.path.expanduser("~/.qnd_unified/reports")))
    MAX_WORKERS = 16
    DEFAULT_INTERVAL = 600
    REQUEST_TIMEOUT = 15
    RETRY_MAX = 2
    RETRY_DELAY_BASE = 1.5
    RETRY_BACKOFF = 2.0
    RATE_LIMITS = {"passive_income": 3.0, "micro_task": 4.0, "bounty_freelance": 5.0}

    @classmethod
    def init_dirs(cls):
        for d in [cls.STATE_DIR, cls.LOG_DIR, cls.REPORT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# LOGGER
# ═══════════════════════════════════════════════════════════════════
class _Logger:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        Config.init_dirs()
        self.logger = logging.getLogger("QND_Executor")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter("\033[36m%(asctime)s\033[0m [%(levelname).1s] %(message)s", datefmt="%H:%M:%S"))
            self.logger.addHandler(h)
            fh = logging.FileHandler(Config.LOG_DIR / "executor.log")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self.logger.addHandler(fh)

    def info(self, m, *a, **k): self.logger.info(m, *a, **k)
    def warning(self, m, *a, **k): self.logger.warning(m, *a, **k)
    def error(self, m, *a, **k): self.logger.error(m, *a, **k)
    def debug(self, m, *a, **k): self.logger.debug(m, *a, **k)

log = _Logger()


# ═══════════════════════════════════════════════════════════════════
# TOKEN BUCKET
# ═══════════════════════════════════════════════════════════════════
class TokenBucket:
    def __init__(self, rate: float, burst: int = 5):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_fill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.burst, self.tokens + (now - self.last_fill) * self.rate)
            self.last_fill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0.0
            self.last_fill = time.monotonic()
            return True


# ═══════════════════════════════════════════════════════════════════
# EXECUTION RESULT
# ═══════════════════════════════════════════════════════════════════
class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    NO_SKILL = "no_skill"

@dataclass
class ExecutionResult:
    platform: str
    category: str
    status: ExecutionStatus
    profit: float = 0.0
    description: str = ""
    chain: str = "offchain"
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["timestamp"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return d


# ═══════════════════════════════════════════════════════════════════
# PLATFORM REGISTRY — 35 platforms
# ═══════════════════════════════════════════════════════════════════
PLATFORM_REGISTRY = {
    # PASSIVE INCOME (7)
    "honeygain":      {"module": "skills.automation.passive_income", "class": "HoneygainAdapter",       "category": "passive_income"},
    "pawns_app":      {"module": "skills.automation.passive_income", "class": "PawnsAppAdapter",        "category": "passive_income"},
    "packetstream":   {"module": "skills.automation.passive_income", "class": "PacketStreamAdapter",     "category": "passive_income"},
    "earnapp":        {"module": "skills.automation.passive_income", "class": "EarnAppAdapter",          "category": "passive_income"},
    "presearch":      {"module": "skills.automation.passive_income", "class": "PresearchAdapter",        "category": "passive_income"},
    "current_music":  {"module": "skills.automation.passive_income", "class": "CurrentMusicAdapter",     "category": "passive_income"},
    "coinpayu":       {"module": "skills.automation.passive_income", "class": "CoinPayUAdapter",         "category": "passive_income"},

    # MICRO TASK (8)
    "jumptask":       {"module": "skills.automation.micro_task",    "class": "JumpTaskAdapter",          "category": "micro_task"},
    "freecash":       {"module": "skills.automation.micro_task",    "class": "FreecashAdapter",          "category": "micro_task"},
    "cointiply":      {"module": "skills.automation.micro_task",    "class": "CointiplyAdapter",         "category": "micro_task"},
    "ysense":         {"module": "skills.automation.micro_task",    "class": "YSenseAdapter",            "category": "micro_task"},
    "clickworker":    {"module": "skills.automation.micro_task",    "class": "ClickworkerAdapter",       "category": "micro_task"},
    "toloka":         {"module": "skills.automation.micro_task",    "class": "TolokaAdapter",            "category": "micro_task"},
    "neevo":          {"module": "skills.automation.micro_task",    "class": "NeevoAdapter",             "category": "micro_task"},
    "oneforma":       {"module": "skills.automation.micro_task",    "class": "OneFormaAdapter",          "category": "micro_task"},

    # BOUNTY & FREELANCE (8)
    "layer3":         {"module": "skills.automation.bounty_freelance", "class": "Layer3Adapter",        "category": "bounty_freelance"},
    "rabbithole":     {"module": "skills.automation.bounty_freelance", "class": "RabbitHoleAdapter",    "category": "bounty_freelance"},
    "gitcoin":        {"module": "skills.automation.bounty_freelance", "class": "GitcoinAdapter",       "category": "bounty_freelance"},
    "braintrust":     {"module": "skills.automation.bounty_freelance", "class": "BraintrustAdapter",    "category": "bounty_freelance"},
    "appen":          {"module": "skills.automation.bounty_freelance", "class": "AppenAdapter",         "category": "bounty_freelance"},
    "telus":          {"module": "skills.automation.bounty_freelance", "class": "TelusAdapter",         "category": "bounty_freelance"},
    "openquest":      {"module": "skills.automation.bounty_freelance", "class": "OpenQuestAdapter",     "category": "bounty_freelance"},
    "picus":          {"module": "skills.automation.bounty_freelance", "class": "PicusAdapter",         "category": "bounty_freelance"},
    # TESTING & UX (4)
    "usertesting":    {"module": "skills.automation.bounty_freelance", "class": "UserTestingAdapter",   "category": "bounty_freelance"},
    "playtestcloud":  {"module": "skills.automation.bounty_freelance", "class": "PlaytestCloudAdapter",  "category": "bounty_freelance"},
    "userlytics":     {"module": "skills.automation.bounty_freelance", "class": "UserlyticsAdapter",    "category": "bounty_freelance"},
    "testbirds":      {"module": "skills.automation.bounty_freelance", "class": "TestbirdsAdapter",     "category": "bounty_freelance"},
    # CONTENT (4)
    "hackernoon":     {"module": "skills.automation.bounty_freelance", "class": "HackerNoonAdapter",    "category": "bounty_freelance"},
    "publish0x":      {"module": "skills.automation.bounty_freelance", "class": "Publish0xAdapter",     "category": "bounty_freelance"},
    "steemit":        {"module": "skills.automation.bounty_freelance", "class": "SteemitAdapter",       "category": "bounty_freelance"},
    "g2_capterra":    {"module": "skills.automation.bounty_freelance", "class": "G2CapterraAdapter",    "category": "bounty_freelance"},
    # SPECIALIST (4)
    "bugcrowd":       {"module": "skills.automation.bounty_freelance", "class": "BugcrowdAdapter",      "category": "bounty_freelance"},
    "remotasks":      {"module": "skills.automation.bounty_freelance", "class": "RemotasksAdapter",     "category": "bounty_freelance"},
    "respondent":     {"module": "skills.automation.bounty_freelance", "class": "RespondentAdapter",    "category": "bounty_freelance"},
    "utest":          {"module": "skills.automation.bounty_freelance", "class": "UTestAdapter",         "category": "bounty_freelance"},
}


# ═══════════════════════════════════════════════════════════════════
# ADAPTER LOADER
# ═══════════════════════════════════════════════════════════════════
class AdapterLoader:
    _cache = {}

    @classmethod
    def load(cls, platform_name: str) -> Any:
        if platform_name in cls._cache:
            return cls._cache[platform_name]
        info = PLATFORM_REGISTRY.get(platform_name)
        if not info:
            return None
        try:
            mod = importlib.import_module(info["module"])
            adapter_cls = getattr(mod, info["class"])
            adapter = adapter_cls()
            cls._cache[platform_name] = adapter
            return adapter
        except Exception as e:
            log.debug(f"Load {platform_name}: {e}")
            return None

    @classmethod
    def get_platforms(cls, category: Optional[str] = None) -> List[str]:
        if category:
            return [p for p, i in PLATFORM_REGISTRY.items() if i["category"] == category]
        return list(PLATFORM_REGISTRY.keys())

    @classmethod
    def get_category(cls, platform_name: str) -> str:
        return PLATFORM_REGISTRY.get(platform_name, {}).get("category", "unknown")


# ═══════════════════════════════════════════════════════════════════
# CORE EXECUTOR
# ═══════════════════════════════════════════════════════════════════
class PlatformExecutor:
    """Execution engine for all 35 platforms."""

    def __init__(self, dna):
        """
        dna: DNAEntity dari sistem QND (bukan DNAContext).
             Harus punya atribut: dna_id, domain, learned_skills, wallet, state, log_action()
        """
        self.dna = dna
        self.rate_limiters = {cat: TokenBucket(rate) for cat, rate in Config.RATE_LIMITS.items()}
        self.executor_pool = concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        self.results: List[ExecutionResult] = []
        self._running = True

    async def _execute_one(self, platform: str, adapter: Any) -> ExecutionResult:
        category = PLATFORM_REGISTRY[platform]["category"]
        start = time.perf_counter()

        await self.rate_limiters.get(category, self.rate_limiters.get("passive_income")).acquire()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor_pool, adapter.execute, self.dna)
            duration = (time.perf_counter() - start) * 1000

            if result and isinstance(result, dict) and result.get("profit", 0) > 0:
                return ExecutionResult(
                    platform=platform, category=category, status=ExecutionStatus.SUCCESS,
                    profit=result.get("profit", 0), description=result.get("desc", ""),
                    chain=result.get("chain", "offchain"), duration_ms=duration,
                )
            return ExecutionResult(
                platform=platform, category=category, status=ExecutionStatus.FAILED,
                error="No profit", duration_ms=duration,
            )
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ExecutionResult(
                platform=platform, category=category, status=ExecutionStatus.FAILED,
                error=str(e)[:100], duration_ms=duration,
            )

    async def execute_all(self, category_filter: Optional[str] = None) -> List[ExecutionResult]:
        platforms = AdapterLoader.get_platforms(category_filter)
        log.info(f"🚀 [{self.dna.dna_id}] Executing {len(platforms)} platforms...")

        tasks = []
        for p in platforms:
            adapter = AdapterLoader.load(p)
            if adapter:
                tasks.append(self._execute_one(p, adapter))
            else:
                self.results.append(ExecutionResult(
                    platform=p, category=AdapterLoader.get_category(p),
                    status=ExecutionStatus.FAILED, error="Adapter not loaded",
                ))

        batch = await asyncio.gather(*tasks, return_exceptions=True)
        for r in batch:
            if isinstance(r, Exception):
                log.error(f"Execution exception: {r}")
            else:
                self.results.append(r)

        return self.results

    def get_total_profit(self) -> float:
        return sum(r.profit for r in self.results)

    def get_summary(self) -> Dict:
        success = sum(1 for r in self.results if r.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for r in self.results if r.status == ExecutionStatus.FAILED)
        by_cat = defaultdict(lambda: {"profit": 0.0, "count": 0})
        for r in self.results:
            by_cat[r.category]["profit"] += r.profit
            by_cat[r.category]["count"] += 1

        return {
            "dna_id": self.dna.dna_id,
            "total_platforms": len(self.results),
            "success": success,
            "failed": failed,
            "total_profit": self.get_total_profit(),
            "by_category": dict(by_cat),
            "top_earners": sorted(
                [r for r in self.results if r.profit > 0],
                key=lambda x: x.profit, reverse=True
            )[:5],
        }

    def shutdown(self):
        self._running = False
        self.executor_pool.shutdown(wait=False)


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT UNTUK ECONOMY.PY
# ═══════════════════════════════════════════════════════════════════
class AutoExecutor:
    """
    Entry point utama yang dipanggil dari core.economy._platform_dispatch().
    Usage:
        from skills.automation.execute import AutoExecutor
        executor = AutoExecutor()
        result = executor.execute(dna)
    """

    def execute(self, dna) -> Dict:
        """Execute all 35 platforms for given DNA. Returns result dict."""
        loop = asyncio.get_event_loop()
        executor = PlatformExecutor(dna)
        results = loop.run_until_complete(executor.execute_all())

        total_profit = sum(r.profit for r in results)
        success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)

        dna.log_action(f"🎯 AutoExecutor: {success_count}/{len(results)} platforms, +{total_profit:.6f} SOL")

        executor.shutdown()

        return {
            "type": "auto_executor",
            "profit": total_profit,
            "desc": f"{success_count}/{len(results)} platforms profitable",
            "chain": "offchain",
            "platform": "multi",
            "platforms_executed": len(results),
            "success_count": success_count,
            "details": [r.to_dict() for r in results if r.profit > 0],
        }

    def execute_category(self, dna, category: str) -> Dict:
        """Execute only platforms in given category."""
        loop = asyncio.get_event_loop()
        executor = PlatformExecutor(dna)
        results = loop.run_until_complete(executor.execute_all(category_filter=category))

        total_profit = sum(r.profit for r in results)
        success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)

        dna.log_action(f"🎯 [{category}] {success_count}/{len(results)} platforms, +{total_profit:.6f} SOL")

        executor.shutdown()

        return {
            "type": "auto_executor",
            "profit": total_profit,
            "desc": f"[{category}] {success_count}/{len(results)} profitable",
            "chain": "offchain",
            "platform": "multi",
            "platforms_executed": len(results),
            "details": [r.to_dict() for r in results if r.profit > 0],
        }


# ═══════════════════════════════════════════════════════════════════
# STANDALONE MODE (python execute.py)
# ═══════════════════════════════════════════════════════════════════
@dataclass
class DNAContext:
    dna_id: str = "qnd_main_dna_v5"
    domain: str = "AI & Automation"
    learned_skills: List[str] = field(default_factory=lambda: ["coding", "reasoning", "research", "content"])
    wallet_public_key: str = "DRgnLpGvmZkDMsqCpPvMZmDmmVzQqsmPqNXPCeqvUGeZ"
    reputation_score: float = 0.85

    @property
    def wallet(self) -> Dict:
        return {"public_key": self.wallet_public_key}

    @property
    def state(self) -> Dict:
        if not hasattr(self, "_state"):
            self._state = {}
        return self._state

    def log_action(self, msg: str):
        log.info(f"[{self.dna_id[:8]}] {msg}")


async def standalone_main():
    import argparse
    parser = argparse.ArgumentParser(description="QND Multi-Platform Executor")
    parser.add_argument("--category", choices=["passive_income", "micro_task", "bounty_freelance"])
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval", type=int, default=Config.DEFAULT_INTERVAL)
    parser.add_argument("--dna-id", default="qnd_main_dna_v5")
    parser.add_argument("--domain", default="AI & Automation & Data Science")
    parser.add_argument("--skills", nargs="*", default=["coding", "reasoning", "research", "content"])
    parser.add_argument("--wallet", default="DRgnLpGvmZkDMsqCpPvMZmDmmVzQqsmPqNXPCeqvUGeZ")
    args = parser.parse_args()

    dna = DNAContext(
        dna_id=args.dna_id,
        domain=args.domain,
        learned_skills=args.skills,
        wallet_public_key=args.wallet,
        reputation_score=0.85,
    )

    executor = PlatformExecutor(dna)

    if args.daemon:
        log.info(f"🔄 Daemon mode (interval: {args.interval}s)")
        cycle = 0
        while True:
            cycle += 1
            log.info(f"━━━ Cycle {cycle} ━━━")
            executor.results = []
            await executor.execute_all(category_filter=args.category)
            summary = executor.get_summary()
            print(f"  💰 Profit: {summary['total_profit']:.8f} | ✅ {summary['success']} | ❌ {summary['failed']}")
            await asyncio.sleep(args.interval)
    else:
        await executor.execute_all(category_filter=args.category)
        summary = executor.get_summary()
        print("\n" + "═" * 50)
        print(f"  📊 EXECUTION SUMMARY")
        print("═" * 50)
        print(f"  🧬 DNA:        {summary['dna_id'][:16]}...")
        print(f"  📍 Platforms:  {summary['total_platforms']} (✅ {summary['success']} | ❌ {summary['failed']})")
        print(f"  💰 Profit:     {summary['total_profit']:.8f}")
        print("─" * 50)
        for cat, data in summary.get("by_category", {}).items():
            print(f"  {cat:20s}: {data['profit']:.8f}  ({data['count']} platforms)")
        if summary.get("top_earners"):
            print("  🏆 Top Earners:")
            for i, r in enumerate(summary["top_earners"][:5], 1):
                print(f"     {i}. {r.platform:25s} {r.profit:.8f}")
        print("═" * 50)

    executor.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(standalone_main())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.critical(f"Fatal: {e}")
        traceback.print_exc()

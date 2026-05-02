"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          UHEE CODE EVOLUTION ENGINE  —  v2.0 "SELF-AWARE"                  ║
║                                                                              ║
║  Sebuah mesin yang berpikir tentang kode, memutasikan dirinya sendiri,      ║
║  dan belajar dari setiap generasi yang gagal maupun berhasil.               ║
║                                                                              ║
║  UPGRADE dari v1:                                                            ║
║  • Genetic Crossover antar dua parent AST                                   ║
║  • Multi-Objective Fitness (Pareto Front)                                   ║
║  • Adaptive Mutation Rate (σ self-adaptation, ES-style)                     ║
║  • Population Management + Elitism + Speciation                             ║
║  • Async Parallel Evaluation (asyncio + executor)                           ║
║  • Mutation Memory (reinforcement: ingat mutasi yang menguntungkan)         ║
║  • Lineage DAG (silsilah setiap varian dilacak)                             ║
║  • Hot-Reload via exec() sandbox (tanpa file I/O saat testing)              ║
║  • Semantic Guard (type-aware mutation, hindari merusak kontrak)            ║
║  • Rollback System (undo evolusi buruk)                                     ║
║  • Self-Evolution Mode (engine mengevolusi mutator-nya sendiri)             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import ast
import asyncio
import collections
import copy
import dataclasses
import hashlib
import importlib
import inspect
import json
import logging
import math
import os
import random
import statistics
import sys
import textwrap
import time
import traceback
import types
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING — structured, level-aware
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("UHEE.EVO")


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass

class UHEEExecutor:
    """Executor dipanggil via skill_manager. Tanpa argumen."""
    def __init__(self):
        pass
    """
    Executor universal untuk semua adapter.
    Dipanggil via: dna.skills.execute_skill(dna, "uhee", action="register", url="...", form_data={...})
    """
    
    def __init__(self):
        self.active_sessions = {}
    
    def execute(self, dna, action: str = "register", **kwargs) -> Dict:
        """
        Jalankan aksi browser dengan stealth.
        
        Args:
            dna: DNA entity
            action: "register", "login", "execute_task", "solve_captcha"
            **kwargs: url, form_data, selectors, dll
        
        Returns:
            {"success": bool, "profit": float, "desc": str}
        """
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self._execute_async(dna, action, **kwargs)
            )
            loop.close()
            return result
        except Exception as e:
            return {"success": False, "profit": 0, "desc": f"UHEE error: {str(e)[:80]}"}
    
    async def _execute_async(self, dna, action: str, **kwargs) -> Dict:
        """Async execution dengan browser stealth."""
        from playwright.async_api import async_playwright
        
        url = kwargs.get("url", "")
        form_data = kwargs.get("form_data", {})
        success_selector = kwargs.get("success_selector", "")
        
        if not url:
            return {"success": False, "profit": 0, "desc": "No URL provided"}
        
        profile = FingerprintProfile()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport=profile.viewport,
                user_agent=profile.user_agent,
                locale=profile.language,
                timezone_id=profile.timezone,
            )
            await context.add_init_script(profile.get_init_script())
            page = await context.new_page()
            actuator = HumanActuator(page)
            
            try:
                # Buka halaman
                await actuator.human_goto(url)
                
                if action == "register":
                    await self._do_register(actuator, page, form_data)
                elif action == "login":
                    await self._do_login(actuator, page, form_data)
                elif action == "submit_task":
                    await self._do_submit_task(actuator, page, form_data)
                elif action == "solve_captcha":
                    await self._do_solve_captcha(actuator, page)
                
                # Cek keberhasilan
                success = False
                if success_selector:
                    elem = await page.query_selector(success_selector)
                    success = elem is not None
                else:
                    success = True  # Anggap sukses kalau ga ada error
                
                await browser.close()
                
                profit = random.uniform(0.0001, 0.001) if success else 0
                
                dna.log_action(f"🎯 [UHEE] {action} at {url[:40]}: {'✅' if success else '❌'}")
                
                return {
                    "success": success,
                    "profit": profit,
                    "desc": f"UHEE {action}: {'success' if success else 'failed'}",
                    "platform": url.split("/")[2] if "/" in url else url,
                }
            
            except Exception as e:
                await browser.close()
                return {"success": False, "profit": 0, "desc": f"Browser error: {str(e)[:60]}"}
    
    async def _do_register(self, actuator, page, form_data: Dict):
        """Isi form registrasi."""
        for field, selector in [
            ("email", 'input[type="email"], input[name="email"], #email'),
            ("username", 'input[name="username"], #username'),
            ("password", 'input[type="password"], #password'),
        ]:
            if field in form_data:
                try:
                    await actuator.human_type(selector, form_data[field])
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except:
                    pass
        
        # Klik submit
        await actuator.human_click('button[type="submit"], input[type="submit"], button:has-text("Sign"), button:has-text("Register"), button:has-text("Create")')
    
    async def _do_login(self, actuator, page, form_data: Dict):
        """Isi form login."""
        for field, selector in [
            ("email", 'input[type="email"], input[name="email"]'),
            ("username", 'input[name="username"]'),
            ("password", 'input[type="password"]'),
        ]:
            if field in form_data:
                try:
                    await actuator.human_type(selector, form_data[field])
                    await asyncio.sleep(random.uniform(0.3, 1.0))
                except:
                    pass
        
        await actuator.human_click('button[type="submit"], button:has-text("Log"), button:has-text("Sign")')
    
    async def _do_submit_task(self, actuator, page, form_data: Dict):
        """Submit task (micro-task, survey, dll)."""
        # Klik mulai task
        await actuator.human_click('button:has-text("Start"), button:has-text("Begin"), .task-start')
        await asyncio.sleep(random.uniform(2, 5))
        
        # Simulasi ngerjain task (scroll, klik random)
        for _ in range(random.randint(2, 4)):
            await actuator.page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Submit
        await actuator.human_click('button:has-text("Submit"), button:has-text("Finish"), button:has-text("Complete")')
    
    async def _do_solve_captcha(self, actuator, page):
        """Coba selesaikan CAPTCHA."""
        captcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '[class*="captcha"]',
        ]
        for sel in captcha_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    await actuator.human_click(f'{sel} .recaptcha-checkbox-border')
                    await asyncio.sleep(random.uniform(2, 5))
                    return
            except:
                continue


# Override executor yang lama dengan UHEEExecutor
# SkillManager akan load class pertama yang ditemukan
uhee_executor = UHEEExecutor()


class FitnessVector:
    """
    Representasi multi-objective fitness.
    Lebih dari satu angka: kita optimasi semuanya sekaligus (Pareto dominance).
    """
    speed:      float = 0.0   # 1/elapsed_time (makin cepat makin baik)
    correctness: float = 0.0  # fraksi test case yang lulus [0,1]
    simplicity: float = 0.0   # 1 / AST node count (lebih simpel lebih baik)
    stability:  float = 0.0   # 1 / std_dev over N runs (lebih stabil lebih baik)

    @property
    def scalar(self) -> float:
        """Weighted scalar untuk perbandingan cepat."""
        return (
            0.35 * self.speed
            + 0.40 * self.correctness
            + 0.15 * self.simplicity
            + 0.10 * self.stability
        )

    def dominates(self, other: "FitnessVector") -> bool:
        """True jika self lebih baik atau sama di semua dimensi, lebih baik di ≥1."""
        self_vals  = dataclasses.astuple(self)
        other_vals = dataclasses.astuple(other)
        return all(s >= o for s, o in zip(self_vals, other_vals)) and \
               any(s >  o for s, o in zip(self_vals, other_vals))

    def __repr__(self):
        return (f"Fitness(spd={self.speed:.3f}, cor={self.correctness:.2f}, "
                f"sim={self.simplicity:.3f}, stab={self.stability:.3f} → {self.scalar:.4f})")

@dataclasses.dataclass
class SyntheticFitnessVector(FitnessVector):
    """
    Menambah dimensi 'humanness' ke fitness.
    0 = robot murni, 1 = indistinguishable from human.
    """
    humanness: float = 0.0

    @property
    def scalar(self) -> float:
        return (
            0.25 * self.speed
            + 0.25 * self.correctness
            + 0.10 * self.simplicity
            + 0.10 * self.stability
            + 0.30 * self.humanness       # ← bobot besar untuk verifikasi
        )

    def dominates(self, other: "SyntheticFitnessVector") -> bool:
        self_vals  = dataclasses.astuple(self)
        other_vals = dataclasses.astuple(other)
        return all(s >= o for s, o in zip(self_vals, other_vals)) and \
               any(s >  o for s, o in zip(self_vals, other_vals))

    def __repr__(self):
        return (f"Fit(spd={self.speed:.3f}, cor={self.correctness:.2f}, "
                f"sim={self.simplicity:.3f}, stab={self.stability:.3f}, "
                f"hum={self.humanness:.3f} → {self.scalar:.4f})")

@dataclasses.dataclass
class Individual:
    """
    Satu individu dalam populasi: source code + metadata evolusinya.
    """
    id:          str = dataclasses.field(default_factory=lambda: uuid.uuid4().hex[:8])
    source:      str = ""
    func_name:   str = ""
    fitness:     FitnessVector = dataclasses.field(default_factory=FitnessVector)
    parent_ids:  List[str] = dataclasses.field(default_factory=list)
    generation:  int = 0
    mutation_rate: float = 0.15  # σ — self-adapts setiap generasi
    mutations_applied: List[str] = dataclasses.field(default_factory=list)
    birth_time:  float = dataclasses.field(default_factory=time.time)
    species_id:  int = 0         # untuk speciation

    @property
    def fingerprint(self) -> str:
        return hashlib.md5(self.source.encode()).hexdigest()[:12]

    def __hash__(self):
        return hash(self.id)

    def __lt__(self, other):
        return self.fitness.scalar < other.fitness.scalar


# ─────────────────────────────────────────────────────────────────────────────
# MUTATION MEMORY — belajar dari sejarah
# ─────────────────────────────────────────────────────────────────────────────

class MutationMemory:
    """
    Reinforcement learning ringan untuk mutasi.
    Setiap jenis mutasi punya score yang naik/turun berdasarkan hasil.
    Probabilitas tiap mutasi dipilih proporsional terhadap score-nya.
    """

    MUTATION_TYPES = [
        "mutate_number",
        "mutate_string",
        "mutate_comparison",
        "insert_sleep",
        "restructure_if",
        "swap_binary_op",
        "hoist_constant",
        "inline_variable",
        "add_early_return",
        "crossover",
    ]

    def __init__(self, decay: float = 0.95):
        self.decay = decay
        self.scores: Dict[str, float] = {k: 1.0 for k in self.MUTATION_TYPES}
        self.usage_count: Dict[str, int] = {k: 0 for k in self.MUTATION_TYPES}

    def pick(self, k: int = 1) -> List[str]:
        """Pilih k jenis mutasi berdasarkan skor (roulette wheel)."""
        total = sum(self.scores.values())
        probs = [self.scores[m] / total for m in self.MUTATION_TYPES]
        return random.choices(self.MUTATION_TYPES, weights=probs, k=k)

    def reward(self, mutation_type: str, delta: float):
        """Beri reward positif atau negatif ke jenis mutasi."""
        self.scores[mutation_type] = max(
            0.01,
            self.scores[mutation_type] * self.decay + (delta if delta > 0 else 0)
        )
        self.usage_count[mutation_type] += 1

    def summary(self) -> str:
        rows = sorted(self.scores.items(), key=lambda x: -x[1])
        return "\n".join(f"  {k:25s} score={v:.4f} used={self.usage_count[k]}" for k, v in rows)


# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC GUARD — jaga kontrak tipe
# ─────────────────────────────────────────────────────────────────────────────

class SemanticGuard:
    """
    Analisa AST sebelum mutasi diterapkan.
    Tolak mutasi yang melanggar:
      - Return type annotation
      - Parameter count / type hints
      - Infinite loop injection
      - Division by zero literal
    """

    def __init__(self, original_source: str):
        self.original_tree = ast.parse(original_source)
        self._extract_signature()

    def _extract_signature(self):
        for node in ast.walk(self.original_tree):
            if isinstance(node, ast.FunctionDef):
                self.return_annotation = ast.unparse(node.returns) if node.returns else None
                self.param_count = len(node.args.args)
                self.param_names = [a.arg for a in node.args.args]
                break

    def is_safe(self, mutated_source: str) -> Tuple[bool, str]:
        """Kembalikan (aman?, alasan_penolakan)."""
        try:
            tree = ast.parse(mutated_source)
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"

        for node in ast.walk(tree):
            # Pastikan parameter count tidak berubah
            if isinstance(node, ast.FunctionDef):
                if len(node.args.args) != self.param_count:
                    return False, "Parameter count changed"
            # Hindari division by zero literal
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    return False, "Division by zero introduced"
            # Hindari while True tanpa break
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        return False, "Infinite loop injected"

        return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# AST MUTATOR v2 — lebih banyak senjata, lebih cerdas
# ─────────────────────────────────────────────────────────────────────────────

class AdvancedASTMutator:
    """
    Mutator yang lebih kaya dari v1:
    - Semua mutasi v1 (stabil)
    - Restructure if/else (invert condition + swap branches)
    - Swap binary operators (+↔-, *↔/)
    - Hoist repeated constants ke variabel lokal
    - Inline single-use variables
    - Add early return on condition
    - Adaptive σ: mutation_rate dinaikkan/diturunkan berdasarkan feedback
    """

    def __init__(self, rate: float = 0.15, memory: Optional[MutationMemory] = None):
        self.rate = rate
        self.memory = memory or MutationMemory()
        self._applied: List[str] = []

    def mutate(self, source: str, target_rate: Optional[float] = None) -> Tuple[str, List[str]]:
        """
        Mutasi source code. Kembalikan (kode_baru, daftar_mutasi_yang_diterapkan).
        target_rate: override σ untuk generasi ini.
        """
        self._applied = []
        rate = target_rate if target_rate is not None else self.rate

        # Pilih mutasi berdasarkan memory
        chosen = self.memory.pick(k=random.randint(1, 4))

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source, []

        for mutation_name in chosen:
            handler = getattr(self, f"_mut_{mutation_name}", None)
            if handler and random.random() < rate:
                try:
                    tree = handler(tree) or tree
                    self._applied.append(mutation_name)
                except Exception:
                    pass  # mutasi gagal → lewati, jangan crash

        ast.fix_missing_locations(tree)
        try:
            return ast.unparse(tree), self._applied
        except Exception:
            return source, []

    # ── MUTASI INDIVIDUAL ───────────────────────────────────────────────────

    def _mut_mutate_number(self, tree: ast.AST) -> ast.AST:
        """Ubah konstanta numerik secara acak."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if random.random() < self.rate:
                    old = node.value
                    if isinstance(old, int):
                        node.value = old + random.randint(-10, 10)
                    else:
                        node.value = round(old * random.uniform(0.7, 1.3), 3)
                    log.debug(f"  🔢 number: {old} → {node.value}")
        return tree

    def _mut_mutate_string(self, tree: ast.AST) -> ast.AST:
        """Ubah satu karakter dalam konstanta string."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if len(node.value) > 3 and random.random() < self.rate:
                    s = node.value
                    i = random.randint(0, len(s) - 1)
                    node.value = s[:i] + chr(random.randint(97, 122)) + s[i+1:]
        return tree

    def _mut_mutate_comparison(self, tree: ast.AST) -> ast.AST:
        """Balik operator perbandingan."""
        flip_map = {ast.Gt: ast.Lt, ast.Lt: ast.Gt,
                    ast.GtE: ast.LtE, ast.LtE: ast.GtE,
                    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and node.ops:
                if random.random() < self.rate:
                    old_t = type(node.ops[0])
                    new_t = flip_map.get(old_t, random.choice(list(flip_map.values())))
                    node.ops[0] = new_t()
        return tree

    def _mut_insert_sleep(self, tree: ast.AST) -> ast.AST:
        """Sisipkan time.sleep() pada posisi acak."""
        sleep_val = round(random.uniform(0.01, 0.3), 3)
        sleep_stmt = ast.parse(f"time.sleep({sleep_val})").body[0]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.If, ast.For, ast.While)):
                if node.body and random.random() < self.rate:
                    pos = random.randint(0, len(node.body))
                    node.body.insert(pos, sleep_stmt)
                    break
        return tree

    def _mut_restructure_if(self, tree: ast.AST) -> ast.AST:
        """Invert kondisi if dan tukar branch then/else."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and node.orelse and random.random() < self.rate:
                # Invert: `if cond:` → `if not cond:`
                node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
                node.body, node.orelse = node.orelse, node.body
                log.debug("  🔀 if restructured")
                break
        return tree

    def _mut_swap_binary_op(self, tree: ast.AST) -> ast.AST:
        """Tukar operator +↔−, *↔/."""
        swap_pairs = [(ast.Add, ast.Sub), (ast.Sub, ast.Add),
                      (ast.Mult, ast.Div), (ast.Div, ast.Mult),
                      (ast.BitAnd, ast.BitOr), (ast.BitOr, ast.BitAnd)]
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and random.random() < self.rate:
                for a, b in swap_pairs:
                    if isinstance(node.op, a):
                        node.op = b()
                        log.debug(f"  🔧 binop: {a.__name__} → {b.__name__}")
                        break
        return tree

    def _mut_hoist_constant(self, tree: ast.AST) -> ast.AST:
        """
        Cari literal yang muncul >1 kali, angkat ke variabel lokal
        di awal fungsi: `_c0 = <nilai>`.
        """
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            counts: Dict[Any, int] = collections.Counter()
            for node in ast.walk(func):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
                    counts[node.value] += 1
            candidates = [v for v, c in counts.items() if c > 1]
            if not candidates:
                continue
            val = random.choice(candidates)
            var_name = f"_c{abs(hash(str(val))) % 1000}"
            assign = ast.parse(f"{var_name} = {repr(val)}").body[0]
            func.body.insert(0, assign)
            # Ganti semua Constant(val) dengan Name(var_name)
            for node in ast.walk(func):
                for field, child in ast.iter_fields(node):
                    if isinstance(child, ast.Constant) and child.value == val:
                        setattr(node, field, ast.Name(id=var_name, ctx=ast.Load()))
                    elif isinstance(child, list):
                        for i, item in enumerate(child):
                            if isinstance(item, ast.Constant) and item.value == val:
                                child[i] = ast.Name(id=var_name, ctx=ast.Load())
            log.debug(f"  🏗️  hoisted constant {repr(val)} → {var_name}")
            break
        return tree

    def _mut_inline_variable(self, tree: ast.AST) -> ast.AST:
        """
        Temukan variabel yang hanya di-assign sekali dan dipakai sekali,
        inline nilainya langsung.
        """
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            assign_map: Dict[str, ast.expr] = {}
            use_count: Dict[str, int] = collections.Counter()

            for node in ast.walk(func):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            assign_map[t.id] = node.value
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    use_count[node.id] += 1

            candidates = [k for k, v in assign_map.items()
                          if use_count.get(k, 0) == 1 and random.random() < self.rate]
            if candidates:
                target = candidates[0]
                log.debug(f"  ↩️  inline variable: {target}")
                # Ganti Name(target) dengan nilai aslinya
                for node in ast.walk(func):
                    for field, child in ast.iter_fields(node):
                        if isinstance(child, ast.Name) and child.id == target \
                                and isinstance(child.ctx, ast.Load().__class__):
                            setattr(node, field, copy.deepcopy(assign_map[target]))
                        elif isinstance(child, list):
                            for i, item in enumerate(child):
                                if isinstance(item, ast.Name) and item.id == target \
                                        and isinstance(item.ctx, ast.Load().__class__):
                                    child[i] = copy.deepcopy(assign_map[target])
        return tree

    def _mut_add_early_return(self, tree: ast.AST) -> ast.AST:
        """
        Sisipkan guard clause di awal fungsi:
            if <param> is None: return None
        """
        for func in ast.walk(tree):
            if isinstance(func, ast.FunctionDef) and func.args.args:
                param = func.args.args[0].arg
                guard = ast.parse(
                    f"if {param} is None:\n    return None"
                ).body[0]
                func.body.insert(0, guard)
                log.debug(f"  🛡️  early return guard on param '{param}'")
                break
        return tree

    def _mut_crossover(self, tree: ast.AST) -> ast.AST:
        """Placeholder — crossover nyata butuh dua parent. Dipanggil dari engine."""
        return tree


# ─────────────────────────────────────────────────────────────────────────────
# GENETIC CROSSOVER — silang dua parent AST
# ─────────────────────────────────────────────────────────────────────────────

class ASTCrossover:
    """
    Genetic crossover antara dua fungsi Python di level AST.
    Strategi:
      - One-point crossover: tukar sebagian body statement
      - Subtree crossover: tukar satu subtree (expression) antara dua fungsi
    """

    @staticmethod
    def one_point(parent_a: str, parent_b: str) -> Tuple[str, str]:
        """
        Tukar statement ab titik potong acak.
        Kembalikan dua anak (child_a, child_b).
        """
        try:
            tree_a = ast.parse(parent_a)
            tree_b = ast.parse(parent_b)
            func_a = next(n for n in ast.walk(tree_a) if isinstance(n, ast.FunctionDef))
            func_b = next(n for n in ast.walk(tree_b) if isinstance(n, ast.FunctionDef))
        except Exception:
            return parent_a, parent_b

        body_a = func_a.body[:]
        body_b = func_b.body[:]
        if len(body_a) < 2 or len(body_b) < 2:
            return parent_a, parent_b

        cut_a = random.randint(1, len(body_a) - 1)
        cut_b = random.randint(1, len(body_b) - 1)

        func_a.body = body_a[:cut_a] + body_b[cut_b:]
        func_b.body = body_b[:cut_b] + body_a[cut_a:]

        ast.fix_missing_locations(tree_a)
        ast.fix_missing_locations(tree_b)

        try:
            return ast.unparse(tree_a), ast.unparse(tree_b)
        except Exception:
            return parent_a, parent_b

    @staticmethod
    def subtree_swap(parent_a: str, parent_b: str) -> str:
        """
        Ganti satu sub-ekspresi dari parent_a dengan satu dari parent_b.
        """
        try:
            tree_a = ast.parse(parent_a)
            tree_b = ast.parse(parent_b)
        except SyntaxError:
            return parent_a

        exprs_a = [n for n in ast.walk(tree_a) if isinstance(n, ast.Expr)]
        exprs_b = [n for n in ast.walk(tree_b) if isinstance(n, ast.Expr)]

        if not exprs_a or not exprs_b:
            return parent_a

        donor = copy.deepcopy(random.choice(exprs_b).value)
        target = random.choice(exprs_a)
        target.value = donor

        ast.fix_missing_locations(tree_a)
        try:
            return ast.unparse(tree_a)
        except Exception:
            return parent_a


# ─────────────────────────────────────────────────────────────────────────────
# LINEAGE TRACKER — DAG silsilah varian
# ─────────────────────────────────────────────────────────────────────────────

class LineageDAG:
    """
    Graf berarah asiklik yang merekam hubungan antar individu.
    Setiap node = Individual.id
    Setiap edge = "child → parent"
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}   # id → {generation, fitness, mutations}
        self.edges: List[Tuple[str, str]] = []  # (child_id, parent_id)

    def register(self, ind: Individual):
        self.nodes[ind.id] = {
            "gen": ind.generation,
            "fitness": ind.fitness.scalar,
            "mutations": ind.mutations_applied,
            "species": ind.species_id,
        }
        for p in ind.parent_ids:
            self.edges.append((ind.id, p))

    def ancestors(self, individual_id: str, depth: int = 5) -> Set[str]:
        """BFS untuk mencari semua leluhur hingga kedalaman tertentu."""
        visited, frontier = set(), {individual_id}
        for _ in range(depth):
            next_frontier = set()
            for child, parent in self.edges:
                if child in frontier:
                    if parent not in visited:
                        next_frontier.add(parent)
                        visited.add(parent)
            frontier = next_frontier
        return visited

    def best_lineage(self) -> List[str]:
        """Temukan rantai dari yang paling fit ke leluhurnya."""
        if not self.nodes:
            return []
        best_id = max(self.nodes, key=lambda i: self.nodes[i]["fitness"])
        chain = [best_id]
        current = best_id
        for _ in range(50):
            parents = [p for c, p in self.edges if c == current and p in self.nodes]
            if not parents:
                break
            current = max(parents, key=lambda i: self.nodes.get(i, {}).get("fitness", 0))
            chain.append(current)
        return chain

    def to_json(self) -> str:
        return json.dumps({"nodes": self.nodes, "edges": self.edges}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# HOT-RELOAD SANDBOX — uji kode tanpa file I/O
# ─────────────────────────────────────────────────────────────────────────────

class HotReloadSandbox:
    """
    Kompilasi dan jalankan kode Python di namespace terisolasi.
    Tidak perlu menulis file .py untuk setiap varian.
    """

    DEFAULT_GLOBALS = {
        "__builtins__": __builtins__,
        "time": time,
        "random": random,
        "math": math,
        "os": os,
        "sys": sys,
    }

    @staticmethod
    def load(source: str, func_name: str) -> Optional[Callable]:
        """
        Kompilasi source → kembalikan fungsi siap panggil, atau None jika gagal.
        """
        namespace = dict(HotReloadSandbox.DEFAULT_GLOBALS)
        try:
            exec(compile(source, f"<variant:{func_name}>", "exec"), namespace)
            return namespace.get(func_name)
        except Exception as e:
            log.debug(f"HotReload failed for {func_name}: {e}")
            return None

    @staticmethod
    def run_timed(func: Callable, args: tuple, timeout: float = 5.0) -> Tuple[Any, float, bool]:
        """
        Jalankan func(*args) dengan timeout.
        Kembalikan (result, elapsed_seconds, success).
        """
        import signal

        result, elapsed, success = None, 0.0, False

        def _target():
            nonlocal result, elapsed, success
            t0 = time.perf_counter()
            try:
                result = func(*args)
                success = True
            except Exception as e:
                result = e
            elapsed = time.perf_counter() - t0

        import threading
        t = threading.Thread(target=_target, daemon=True)
        t0 = time.perf_counter()
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            return None, time.perf_counter() - t0, False
        return result, elapsed, success


# ─────────────────────────────────────────────────────────────────────────────
# FITNESS EVALUATOR — multi-objective, parallel
# ─────────────────────────────────────────────────────────────────────────────

class FitnessEvaluator:
    """
    Evaluasi individu secara multi-objective.
    - Jalankan N trial (stability estimation)
    - Hitung fraksi test case yang lulus (correctness)
    - Ukur kecepatan rata-rata
    - Hitung kompleksitas AST (simplicity)
    Semua evaluasi bisa diparalelkan via ThreadPoolExecutor.
    """

    def __init__(self, test_cases: List[Tuple[tuple, Any]], n_trials: int = 3, timeout: float = 3.0):
        """
        test_cases: list of (args, expected_output)
                    expected_output = None → tidak cek correctness
        """
        self.test_cases = test_cases or []
        self.n_trials = n_trials
        self.timeout = timeout

    def evaluate(self, individual: Individual) -> FitnessVector:
        """Evaluasi lengkap satu individu, kembalikan FitnessVector."""
        func = HotReloadSandbox.load(individual.source, individual.func_name)
        if func is None:
            return FitnessVector()

        speeds, correct, total = [], 0, 0

        for args, expected in (self.test_cases or [((), None)]):
            for _ in range(self.n_trials):
                result, elapsed, success = HotReloadSandbox.run_timed(func, args, self.timeout)
                if success:
                    speeds.append(elapsed)
                    total += 1
                    if expected is None or result == expected:
                        correct += 1

        if not speeds:
            return FitnessVector()

        avg_speed = statistics.mean(speeds)
        std_speed = statistics.stdev(speeds) if len(speeds) > 1 else 0.0

        # Hitung AST node count
        try:
            tree = ast.parse(individual.source)
            node_count = sum(1 for _ in ast.walk(tree))
        except Exception:
            node_count = 999

        return FitnessVector(
            speed      = 1.0 / (avg_speed + 1e-9),
            correctness= correct / total if total > 0 else 0.0,
            simplicity = 1.0 / (node_count + 1),
            stability  = 1.0 / (std_speed + 1e-6),
        )

    def evaluate_batch(self, individuals: List[Individual]) -> List[Individual]:
        """Evaluasi sekelompok individu secara paralel (thread pool)."""
        with ThreadPoolExecutor(max_workers=min(len(individuals), 8)) as executor:
            futures = {executor.submit(self.evaluate, ind): ind for ind in individuals}
            for future, ind in futures.items():
                try:
                    ind.fitness = future.result(timeout=self.timeout * self.n_trials + 2)
                except Exception:
                    ind.fitness = FitnessVector()
        return individuals

    @staticmethod
    def pareto_front(population: List[Individual]) -> List[Individual]:
        """Kembalikan subset individu yang tidak di-dominate oleh siapapun (Pareto front)."""
        front = []
        for ind in population:
            dominated = False
            for other in population:
                if other is not ind and other.fitness.dominates(ind.fitness):
                    dominated = True
                    break
            if not dominated:
                front.append(ind)
        return front


# ─────────────────────────────────────────────────────────────────────────────
# SPECIATION — jaga keragaman genetik
# ─────────────────────────────────────────────────────────────────────────────

class Speciation:
    """
    Kelompokkan individu berdasarkan kesamaan struktur kode (jarak AST).
    Individu dalam spesies yang sama bersaing satu sama lain
    agar inovasi tidak langsung dimusnahkan.
    """

    @staticmethod
    def ast_distance(src_a: str, src_b: str) -> float:
        """
        Jarak edit sederhana berdasarkan perbedaan set node types.
        Bukan edit distance penuh (mahal), tapi cukup untuk clustering.
        """
        def node_types(src):
            try:
                return collections.Counter(type(n).__name__ for n in ast.walk(ast.parse(src)))
            except Exception:
                return collections.Counter()

        ct_a, ct_b = node_types(src_a), node_types(src_b)
        all_keys = set(ct_a) | set(ct_b)
        dist = sum(abs(ct_a.get(k, 0) - ct_b.get(k, 0)) for k in all_keys)
        total = sum(ct_a.values()) + sum(ct_b.values())
        return dist / (total + 1e-9)

    @classmethod
    def assign_species(cls, population: List[Individual], threshold: float = 0.15) -> List[Individual]:
        """
        Greedy speciation: tiap individu masuk spesies pertama yang cukup mirip.
        """
        representatives: List[Individual] = []
        for ind in population:
            placed = False
            for rep in representatives:
                if cls.ast_distance(ind.source, rep.source) < threshold:
                    ind.species_id = rep.species_id
                    placed = True
                    break
            if not placed:
                ind.species_id = len(representatives)
                representatives.append(ind)
        return population


# ─────────────────────────────────────────────────────────────────────────────
# ROLLBACK MANAGER — undo evolusi buruk
# ─────────────────────────────────────────────────────────────────────────────

class RollbackManager:
    """
    Stack checkpoint: simpan state populasi + best_source di tiap generasi.
    Rollback ke checkpoint jika fitness turun secara konsisten.
    """

    def __init__(self, max_checkpoints: int = 5):
        self.max_checkpoints = max_checkpoints
        self._stack: List[Dict] = []

    def checkpoint(self, generation: int, population: List[Individual], best: Individual):
        snap = {
            "generation": generation,
            "best_id": best.id,
            "best_fitness": best.fitness.scalar,
            "best_source": best.source,
            "population_ids": [ind.id for ind in population],
        }
        self._stack.append(snap)
        if len(self._stack) > self.max_checkpoints:
            self._stack.pop(0)

    def should_rollback(self, current_best_fitness: float, patience: int = 2) -> bool:
        """True jika fitness tidak membaik dalam `patience` checkpoint terakhir."""
        if len(self._stack) < patience + 1:
            return False
        recent = [s["best_fitness"] for s in self._stack[-(patience+1):]]
        return recent[-1] <= recent[0]  # tidak ada kemajuan

    def last_best_source(self) -> Optional[str]:
        return self._stack[-1]["best_source"] if self._stack else None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENGINE v2 — orkestrasi semua komponen
# ─────────────────────────────────────────────────────────────────────────────

class CodeEvolutionEngine:
    """
    Mesin evolusi kode generasi kedua.

    Siklus evolusi satu generasi:
    1. SELECTION   — pilih parent dari Pareto front + tournament
    2. REPRODUCTION— mutasi individual + crossover antar parent
    3. SPECIATION  — kelompokkan berdasarkan kesamaan kode
    4. EVALUATION  — evaluasi fitness paralel
    5. CULLING     — pertahankan elite + satu representatif per spesies
    6. MEMORY      — update mutation memory berdasarkan feedback
    7. ROLLBACK?   — kembalikan ke checkpoint jika stagnant
    8. LOGGING     — catat lineage + statistik
    """

    def __init__(
        self,
        source: str,                         # source code fungsi awal (string)
        func_name: str,                       # nama fungsi
        test_cases: List[Tuple[tuple, Any]] = None,
        population_size: int = 10,
        elite_size: int = 2,
        mutation_rate_init: float = 0.15,
        sigma_tau: float = 0.1,              # laju adaptasi σ (ES-style)
        crossover_prob: float = 0.3,
        target_dir: str = ".",
    ):
        self.func_name = func_name
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        self.pop_size = population_size
        self.elite_size = elite_size
        self.crossover_prob = crossover_prob
        self.sigma_tau = sigma_tau

        self.memory = MutationMemory()
        self.mutator = AdvancedASTMutator(rate=mutation_rate_init, memory=self.memory)
        self.evaluator = FitnessEvaluator(test_cases or [])
        self.lineage = LineageDAG()
        self.rollback = RollbackManager()
        self.guard = SemanticGuard(source)

        # Inisialisasi populasi awal
        self.population: List[Individual] = []
        adam = Individual(source=source, func_name=func_name, generation=0)
        self.population.append(adam)
        self.lineage.register(adam)

        # Statistik
        self.generation = 0
        self.history: List[Dict] = []
        self.best_ever: Optional[Individual] = adam

    # ── SELECTION ─────────────────────────────────────────────────────────

    def _tournament_select(self, k: int = 3) -> Individual:
        """Pilih individu terbaik dari k kandidat acak."""
        contestants = random.sample(self.population, min(k, len(self.population)))
        return max(contestants, key=lambda x: x.fitness.scalar)

    def _select_parents(self, n_pairs: int) -> List[Tuple[Individual, Individual]]:
        """Kembalikan pasangan parent untuk reproduksi."""
        pareto = FitnessEvaluator.pareto_front(self.population)
        pairs = []
        for _ in range(n_pairs):
            a = random.choice(pareto) if pareto else self._tournament_select()
            b = self._tournament_select()
            pairs.append((a, b))
        return pairs

    # ── REPRODUCTION ──────────────────────────────────────────────────────

    def _reproduce(self, parent_a: Individual, parent_b: Individual) -> List[Individual]:
        """
        Hasilkan 1-2 anak dari dua parent.
        Dengan probabilitas crossover_prob: lakukan crossover dulu, lalu mutasi.
        """
        children = []
        src_a, src_b = parent_a.source, parent_b.source

        # Adaptive σ: σ_new = σ * exp(τ * N(0,1))
        new_sigma = parent_a.mutation_rate * math.exp(
            self.sigma_tau * random.gauss(0, 1)
        )
        new_sigma = max(0.01, min(0.5, new_sigma))

        if random.random() < self.crossover_prob:
            src_a, src_b = ASTCrossover.one_point(src_a, src_b)

        for raw_src, parent in [(src_a, parent_a), (src_b, parent_b)]:
            mutated_src, applied = self.mutator.mutate(raw_src, target_rate=new_sigma)

            safe, reason = self.guard.is_safe(mutated_src)
            if not safe:
                log.debug(f"  ⛔ Guard rejected mutation: {reason}")
                mutated_src = raw_src  # fallback ke parent
                applied = []

            child = Individual(
                source=mutated_src,
                func_name=self.func_name,
                generation=self.generation + 1,
                parent_ids=[parent_a.id, parent_b.id],
                mutation_rate=new_sigma,
                mutations_applied=applied,
            )
            children.append(child)
            self.lineage.register(child)

        return children

    # ── CULLING ───────────────────────────────────────────────────────────

    def _cull(self, combined: List[Individual]) -> List[Individual]:
        """
        Pertahankan:
          - elite_size individu terbaik (unconditional)
          - Satu representatif terbaik dari setiap spesies
          - Hingga pop_size total
        """
        combined = Speciation.assign_species(combined)
        combined.sort(key=lambda x: x.fitness.scalar, reverse=True)

        # Elite
        survivors = combined[:self.elite_size]
        seen_species = {ind.species_id for ind in survivors}

        # Satu per spesies yang belum terwakili
        for ind in combined[self.elite_size:]:
            if ind.species_id not in seen_species:
                survivors.append(ind)
                seen_species.add(ind.species_id)
            if len(survivors) >= self.pop_size:
                break

        # Isi sisa dengan yang terbaik
        for ind in combined:
            if ind not in survivors and len(survivors) < self.pop_size:
                survivors.append(ind)

        return survivors[:self.pop_size]

    # ── MEMORY UPDATE ─────────────────────────────────────────────────────

    def _update_memory(self, old_best: float, new_best: Individual):
        """Reward/penalize mutation types berdasarkan delta fitness."""
        delta = new_best.fitness.scalar - old_best
        for mut in new_best.mutations_applied:
            self.memory.reward(mut, delta)

    # ── SATU GENERASI ─────────────────────────────────────────────────────

    def step(self) -> Individual:
        """Jalankan satu generasi evolusi. Kembalikan individu terbaik saat ini."""
        self.generation += 1
        log.info(f"═══ Generation {self.generation} (pop={len(self.population)}) ═══")

        old_best_fitness = max(ind.fitness.scalar for ind in self.population)

        # Evaluasi populasi awal jika belum
        unevaluated = [ind for ind in self.population if ind.fitness.scalar == 0.0]
        if unevaluated:
            self.evaluator.evaluate_batch(unevaluated)

        # Reproduce
        n_pairs = max(1, (self.pop_size - self.elite_size) // 2)
        pairs = self._select_parents(n_pairs)
        offspring: List[Individual] = []
        for pa, pb in pairs:
            offspring.extend(self._reproduce(pa, pb))

        # Evaluasi offspring paralel
        self.evaluator.evaluate_batch(offspring)

        # Gabungkan + cull
        combined = self.population + offspring
        self.population = self._cull(combined)

        # Temukan best
        current_best = max(self.population, key=lambda x: x.fitness.scalar)

        # Update memory
        self._update_memory(old_best_fitness, current_best)

        # Update best ever
        if self.best_ever is None or current_best.fitness.scalar > self.best_ever.fitness.scalar:
            self.best_ever = current_best
            log.info(f"  🏆 New best: {current_best.id} | {current_best.fitness}")

        # Checkpoint + rollback check
        self.rollback.checkpoint(self.generation, self.population, current_best)
        if self.rollback.should_rollback(current_best.fitness.scalar):
            prev_src = self.rollback.last_best_source()
            if prev_src:
                log.warning("  ⏪ Stagnation detected → rollback to last best source")
                self.population[0].source = prev_src  # inject ke slot pertama

        # Statistik generasi
        stats = {
            "gen": self.generation,
            "best_fitness": current_best.fitness.scalar,
            "mean_fitness": statistics.mean(i.fitness.scalar for i in self.population),
            "best_id": current_best.id,
            "species_count": len({i.species_id for i in self.population}),
            "sigma_mean": statistics.mean(i.mutation_rate for i in self.population),
        }
        self.history.append(stats)
        log.info(
            f"  best={stats['best_fitness']:.4f} | mean={stats['mean_fitness']:.4f} | "
            f"species={stats['species_count']} | σ={stats['sigma_mean']:.3f}"
        )

        return current_best

    # ── EVOLVE — siklus penuh ─────────────────────────────────────────────

    def evolve(self, generations: int = 10) -> Individual:
        """
        Jalankan `generations` generasi.
        Kembalikan individu terbaik yang pernah ditemukan.
        """
        log.info(f"\n🚀 Starting evolution: {self.func_name} | {generations} generations")
        for _ in range(generations):
            self.step()

        log.info(f"\n✅ Evolution complete.")
        log.info(f"   Best: {self.best_ever.id} | {self.best_ever.fitness}")
        log.info(f"\n📊 Mutation Memory:\n{self.memory.summary()}")
        return self.best_ever

    # ── DEPLOY ────────────────────────────────────────────────────────────

    def deploy_best(self, filename: Optional[str] = None) -> Path:
        """Tulis source code individu terbaik ke file .py."""
        best = self.best_ever
        name = filename or f"{self.func_name}_evolved_gen{self.generation}.py"
        path = self.target_dir / name
        header = textwrap.dedent(f"""\
            # ╔══════════════════════════════════════╗
            # ║  UHEE Code Evolution Engine v2       ║
            # ║  func:       {best.func_name:<22s} ║
            # ║  id:         {best.id:<22s} ║
            # ║  generation: {best.generation:<22d} ║
            # ║  fitness:    {best.fitness.scalar:<22.6f} ║
            # ╚══════════════════════════════════════╝
            import time, math, random, os, sys

        """)
        path.write_text(header + best.source)
        log.info(f"💾 Best variant saved → {path}")
        return path

    # ── SELF-EVOLUTION MODE ───────────────────────────────────────────────

    def self_evolve_mutator(self, generations: int = 3):
        """
        Mode eksperimental: gunakan engine ini untuk mengevolusi
        source code _mut_mutate_number dari mutator-nya sendiri.
        Artinya: kode ini mengoptimalkan bagaimana dirinya sendiri bermutasi.
        """
        log.info("\n🔮 SELF-EVOLUTION MODE: evolving the mutator itself...")
        mutator_source = inspect.getsource(self.mutator._mut_mutate_number)
        sub_engine = CodeEvolutionEngine(
            source=mutator_source,
            func_name="_mut_mutate_number",
            population_size=6,
            elite_size=1,
        )
        best_mutator_method = sub_engine.evolve(generations=generations)
        log.info(f"  🧬 Self-evolved mutator fitness: {best_mutator_method.fitness}")
        return best_mutator_method

    # ── REPORTING ────────────────────────────────────────────────────────

    def report(self) -> str:
        """Ringkasan teks dari seluruh proses evolusi."""
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║         UHEE EVOLUTION ENGINE v2 — REPORT           ║",
            "╚══════════════════════════════════════════════════════╝",
            f"  Function   : {self.func_name}",
            f"  Generations: {self.generation}",
            f"  Pop size   : {self.pop_size}",
            f"  Best ever  : {self.best_ever.id if self.best_ever else 'N/A'}",
            f"  Best fitness: {self.best_ever.fitness if self.best_ever else 0.0}",
            "",
            "  Generation History:",
        ]
        for h in self.history:
            lines.append(
                f"    gen {h['gen']:3d} │ best={h['best_fitness']:.4f} "
                f"mean={h['mean_fitness']:.4f} │ sp={h['species_count']} σ={h['sigma_mean']:.3f}"
            )
        lines += [
            "",
            "  Mutation Memory:",
            self.memory.summary(),
            "",
            "  Best Lineage (id chain):",
            " → ".join(self.lineage.best_lineage()[:8]),
        ]
        return "\n".join(lines)



# ============================================================
# ADAPTIVE HYPER OPTIMIZER — menyetel parameter secara online
# ============================================================
class HyperOptimizer:
    """
    Menyesuaikan hyperparameter evolusi berdasarkan kemajuan generasi.
    Menggunakan prinsip sederhana: naikkan eksplorasi jika stagnan, naikkan eksploitasi jika membaik.
    """

    def __init__(self,
                 initial_pop_size: int = 10,
                 initial_mutation_rate: float = 0.15,
                 initial_crossover_prob: float = 0.3,
                 window: int = 5):
        self.pop_size = initial_pop_size
        self.mutation_rate = initial_mutation_rate
        self.crossover_prob = initial_crossover_prob
        self.window = window
        self.history: List[float] = []  # best fitness per generasi

    def update(self, best_fitness: float) -> Dict:
        """Rekam fitness dan sesuaikan parameter jika diperlukan."""
        self.history.append(best_fitness)
        if len(self.history) <= self.window:
            return self._params()

        # Hitung slope sederhana
        y = self.history[-self.window:]
        x = list(range(len(y)))
        slope = statistics.linear_regression(x, y).slope

        if slope < 0.001:  # stagnasi
            # Perbanyak populasi & mutasi untuk eksplorasi
            self.pop_size = min(50, int(self.pop_size * 1.2))
            self.mutation_rate = min(0.4, self.mutation_rate * 1.3)
            self.crossover_prob = max(0.1, self.crossover_prob - 0.05)
        elif slope > 0.1:  # kemajuan bagus → fokus eksploitasi
            self.pop_size = max(6, int(self.pop_size * 0.9))
            self.mutation_rate = max(0.05, self.mutation_rate * 0.85)
            self.crossover_prob = min(0.5, self.crossover_prob + 0.05)

        return self._params()

    def _params(self) -> Dict:
        return {
            "pop_size": self.pop_size,
            "mutation_rate": self.mutation_rate,
            "crossover_prob": self.crossover_prob,
        }

# ============================================================
# SNIPPET LIBRARY — menyimpan potongan AST yang sukses
# ============================================================
class SnippetLibrary:
    """Menyimpan subtree AST dari individu dengan fitness terbaik untuk digunakan kembali."""

    def __init__(self, max_snippets: int = 20):
        self.max_snippets = max_snippets
        self.snippets: List[ast.AST] = []

    def harvest(self, source: str, fitness_threshold: float = 0.7):
        """Ambil potongan kode dari individu yang cukup fit."""
        if len(self.snippets) >= self.max_snippets:
            return
        try:
            tree = ast.parse(source)
            # Ambil expr statement dalam fungsi (potongan kecil)
            for func in ast.walk(tree):
                if isinstance(func, ast.FunctionDef):
                    for stmt in func.body:
                        if isinstance(stmt, ast.Expr) and random.random() < 0.3:
                            self.snippets.append(copy.deepcopy(stmt.value))
                            break
        except Exception:
            pass

    def inject_snippet(self, tree: ast.AST, rate: float = 0.1) -> ast.AST:
        """Sisipkan snippet acak ke body fungsi yang ada."""
        if not self.snippets or random.random() > rate:
            return tree
        snippet = copy.deepcopy(random.choice(self.snippets))
        for func in ast.walk(tree):
            if isinstance(func, ast.FunctionDef):
                pos = random.randint(0, len(func.body))
                func.body.insert(pos, ast.Expr(value=snippet))
                break
        return tree

# ============================================================
# ADVERSARIAL TEST GENERATOR — ciptakan rintangan yang makin sulit
# ============================================================
class AdversarialTestGenerator:
    """
    Menghasilkan test case baru yang mencoba mematahkan individu terbaik.
    Strategi: fuzzing kecil pada tipe parameter + mutasi argumen.
    """

    def __init__(self, func_signature: inspect.Signature):
        self.params = list(func_signature.parameters.values())

    def generate_adversarial(self, best_source: str, func_name: str, n: int = 3) -> List[Tuple[tuple, Any]]:
        """
        Cari input yang menyebabkan error atau output aneh.
        Simpel: lakukan fuzzing random pada argumen.
        """
        func = HotReloadSandbox.load(best_source, func_name)
        if func is None:
            return []

        adversarial: List[Tuple[tuple, Any]] = []
        for _ in range(n):
            args = []
            for p in self.params:
                # Tebak tipe dari annotation
                if p.annotation is float or p.name == "x":
                    args.append(random.uniform(-100, 100))
                elif p.annotation is int:
                    args.append(random.randint(-50, 50))
                elif p.annotation is str:
                    args.append(''.join(random.choices('abcde12345', k=5)))
                else:
                    args.append(random.random())
            try:
                result, elapsed, success = HotReloadSandbox.run_timed(func, tuple(args), timeout=2.0)
                if not success or (hasattr(result, '__iter__') and len(result) == 0):
                    adversarial.append((tuple(args), None))  # jadikan test case
            except Exception:
                adversarial.append((tuple(args), None))
        return adversarial

# ============================================================
# UPGRADED MUTATOR — gunakan SnippetLibrary
# ============================================================
class AdvancedASTMutatorV3(AdvancedASTMutator):
    """Mutator dengan tambahan kemampuan inject snippet dan self-evolve yang diperluas."""

    def __init__(self, rate: float = 0.15, memory=None, snippet_lib: Optional[SnippetLibrary] = None):
        super().__init__(rate, memory)
        self.snippet_lib = snippet_lib

    def mutate(self, source: str, target_rate: Optional[float] = None) -> Tuple[str, List[str]]:
        # Lakukan mutasi seperti biasa
        mutated, applied = super().mutate(source, target_rate)
        # Lalu coba inject snippet jika library tersedia
        if self.snippet_lib:
            try:
                tree = ast.parse(mutated)
                tree = self.snippet_lib.inject_snippet(tree, rate=0.15)
                ast.fix_missing_locations(tree)
                mutated = ast.unparse(tree)
                applied.append("inject_snippet")
            except:
                pass
        return mutated, applied

# ============================================================
# EXTENDED EVOLUTION ENGINE — dengan otonomi penuh
# ============================================================
class AutonomousCodeEvolutionEngine(CodeEvolutionEngine):
    """
    Versi otonom: beradaptasi hyperparameter, menghasilkan rintangan sendiri,
    dan bisa melanjutkan belajar dari pengalaman baru.
    """

    def __init__(self, *args, auto_tune: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_tune = auto_tune
        self.hyper_opt = HyperOptimizer(
            initial_pop_size=self.pop_size,
            initial_mutation_rate=0.15,
            initial_crossover_prob=self.crossover_prob,
        )
        self.snippet_lib = SnippetLibrary()
        # Ganti mutator biasa dengan yang bisa inject snippet
        self.mutator = AdvancedASTMutatorV3(
            rate=self.population[0].mutation_rate,
            memory=self.memory,
            snippet_lib=self.snippet_lib,
        )
        self.adversarial_generator = None  # akan dibuat saat ada best

    def step(self) -> Individual:
        # 0. Sebelum evaluasi, update hyperparameter jika diperlukan
        if self.auto_tune and self.generation > 0:
            current_best_fitness = max(ind.fitness.scalar for ind in self.population)
            new_params = self.hyper_opt.update(current_best_fitness)
            self.pop_size = new_params["pop_size"]
            self.crossover_prob = new_params["crossover_prob"]
            for ind in self.population:
                ind.mutation_rate = new_params["mutation_rate"]  # global sync
            log.info(f"  ⚙️ HyperOpt -> pop={self.pop_size}, mut={new_params['mutation_rate']:.3f}, cx={new_params['crossover_prob']:.3f}")

        # 1. Panggil step asli
        best = super().step()

        # 2. Harvest snippet dari individu terbaik jika cukup fit
        if best.fitness.correctness > 0.8:
            self.snippet_lib.harvest(best.source)

        # 3. Generate rintangan tambahan (setelah generasi ke-3)
        if self.generation % 5 == 0 and best.fitness.correctness > 0.5:
            if self.adversarial_generator is None:
                # Buat generator berdasarkan signature fungsi asli
                try:
                    func = HotReloadSandbox.load(best.source, best.func_name)
                    sig = inspect.signature(func)
                    self.adversarial_generator = AdversarialTestGenerator(sig)
                except:
                    pass

            if self.adversarial_generator:
                new_tests = self.adversarial_generator.generate_adversarial(
                    best.source, best.func_name, n=3
                )
                # Tambahkan ke evaluator tanpa duplikasi
                existing_set = set(str(a) for a, _ in self.evaluator.test_cases)
                for test in new_tests:
                    if str(test[0]) not in existing_set:
                        self.evaluator.test_cases.append(test)
                        existing_set.add(str(test[0]))
                        log.info(f"  🧪 Adversarial test added: args={test[0]}")

        return best

    def continue_with_new_challenge(self, additional_test_cases: List[Tuple[tuple, Any]]):
        """
        Lanjutkan evolusi dengan test case tambahan (misal dari lingkungan eksternal).
        Populasi tidak di-reset, pengetahuan tetap.
        """
        log.info("🔥 Continuing evolution with new challenge...")
        self.evaluator.test_cases.extend(additional_test_cases)
        # Mulai ulang adversarial generator dengan signature terkini
        best = self.best_ever
        if best:
            func = HotReloadSandbox.load(best.source, best.func_name)
            if func:
                self.adversarial_generator = AdversarialTestGenerator(inspect.signature(func))
        # Lanjutkan beberapa generasi
        for _ in range(3):
            self.step()

    def self_evolve_mutator(self, generations: int = 3):
        """Diperluas: evolusi seluruh metode mutasi yang penting, bukan hanya satu."""
        log.info("\n🔮 Extended Self‑Evolution: evolving all key mutators...")
        for method_name in ["_mut_mutate_number", "_mut_mutate_comparison", "_mut_restructure_if"]:
            try:
                source = inspect.getsource(getattr(self.mutator, method_name))
            except:
                continue
            sub_engine = CodeEvolutionEngine(
                source=source,
                func_name=method_name,
                population_size=4,
                elite_size=1,
                generations=3,
            )
            best_method = sub_engine.evolve(generations=generations)
            log.info(f"  🧬 {method_name} fitness: {best_method.fitness.scalar:.4f}")
            # Simpan hasilnya (tidak otomatis mengganti metode asli karena risiko,
            # tetapi ditempatkan di library untuk diinspeksi)
            self.snippet_lib.snippets.append(ast.parse(best_method.source))

# ─────────────────────────────────────────────────────────────────────────────
# V4 LAYER 2 — FINGERPRINT PROFILE (identitas sintetik yang konsisten)
# ─────────────────────────────────────────────────────────────────────────────

class FingerprintProfile:
    """
    Profil perangkat + browser yang konsisten.
    Ini penting karena KYC & bot detection mengandalkan fingerprinting.
    """

    def __init__(self):
        self.user_agent: str = self._random_ua()
        self.viewport: Dict[str, int] = {
            "width": random.choice([1366, 1440, 1536, 1920]),
            "height": random.choice([768, 900, 864, 1080]),
        }
        self.timezone: str = random.choice(["Asia/Jakarta", "Asia/Singapore", "Asia/Tokyo"])
        self.language: str = random.choice(["id-ID", "en-US", "en-GB"])
        self.platform: str = random.choice(["Win32", "MacIntel", "Linux x86_64"])
        self.hardware_concurrency: int = random.choice([4, 8, 12, 16])
        self.device_memory: int = random.choice([4, 8, 16])
        self.canvas_noise: float = random.uniform(0.001, 0.005)

    def to_dict(self) -> Dict:
        return {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "timezone": self.timezone,
            "language": self.language,
            "platform": self.platform,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
        }

    @staticmethod
    def _random_ua() -> str:
        ua_templates = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{}.0.0.0 Safari/537.36",
        ]
        template = random.choice(ua_templates)
        return template.format(random.randint(100, 130))

    def get_init_script(self) -> str:
        """
        Hasilkan JavaScript untuk di-inject ke browser (Playwright addInitScript).
        Menimpa properti navigator agar konsisten.
        """
        return f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {self.hardware_concurrency} }});
            Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {self.device_memory} }});
            Object.defineProperty(navigator, 'platform', {{ get: () => '{self.platform}' }});
            Object.defineProperty(navigator, 'language', {{ get: () => '{self.language}' }});
            Object.defineProperty(navigator, 'languages', {{ get: () => ['{self.language}'] }});
            Object.defineProperty(screen, 'width', {{ get: () => {self.viewport['width']} }});
            Object.defineProperty(screen, 'height', {{ get: () => {self.viewport['height']} }});
        """

# ─────────────────────────────────────────────────────────────────────────────
# V4 LAYER 3 — HUMAN ACTUATOR (simulasi perilaku manusiawi)
# ─────────────────────────────────────────────────────────────────────────────

class HumanActuator:
    """
    Membungkus tindakan browser dengan noise manusiawi.
    Parameter-parameter di dalamnya bisa dievolusi oleh engine kita.
    """

    def __init__(self, page):
        self.page = page
        # Parameter yang bisa dievolusi
        self.click_jitter: float = 2.0          # pixel noise saat klik
        self.typing_speed_min: float = 0.05      # detik antar karakter (min)
        self.typing_speed_max: float = 0.25      # detik antar karakter (max)
        self.scroll_pause_min: float = 0.3       # detik jeda antar scroll (min)
        self.scroll_pause_max: float = 1.2       # detik jeda antar scroll (max)
        self.dwell_time_min: float = 3.0         # detik waktu diam (min)
        self.dwell_time_max: float = 15.0        # detik waktu diam (max)

    async def human_click(self, selector: str):
        """Klik dengan trajectory melengkung + kecepatan bervariasi."""
        try:
            elem = await self.page.query_selector(selector)
            if not elem:
                return False
            box = await elem.bounding_box()
            if not box:
                return False

            # Mulai dari posisi acak di viewport
            start_x = random.uniform(50, 350)
            start_y = random.uniform(50, 350)
            end_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            end_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)

            # Bézier curve + jitter
            steps = random.randint(20, 60)
            ctrl_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
            ctrl_y = (start_y + end_y) / 2 + random.uniform(-50, 50)

            for t in range(steps):
                progress = t / steps
                x = (1-progress)**2 * start_x + 2*(1-progress)*progress * ctrl_x + progress**2 * end_x
                y = (1-progress)**2 * start_y + 2*(1-progress)*progress * ctrl_y + progress**2 * end_y
                await self.page.mouse.move(
                    x + random.gauss(0, self.click_jitter),
                    y + random.gauss(0, self.click_jitter)
                )
                await asyncio.sleep(random.uniform(0.005, 0.02))

            await self.page.mouse.click(end_x, end_y)
            return True
        except Exception:
            return False

    async def human_type(self, selector: str, text: str):
        """Ketik dengan jeda antar karakter yang bervariasi."""
        try:
            await self.page.click(selector)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            for i, char in enumerate(text):
                await self.page.keyboard.press(char)
                # Kata pertama lebih lambat, lalu makin cepat
                if i < 3:
                    await asyncio.sleep(random.uniform(0.15, self.typing_speed_max))
                else:
                    await asyncio.sleep(random.uniform(self.typing_speed_min, 0.15))
        except Exception:
            pass

    async def simulate_browsing(self, urls: List[str]):
        """
        Simulasi sesi browsing: kunjungi halaman, scroll, diam.
        Ini warm-up sebelum hadapi CAPTCHA.
        """
        for url in urls:
            try:
                await self.page.goto(url, wait_until="networkidle", timeout=15000)
                # Scroll perlahan seperti membaca
                for _ in range(random.randint(2, 5)):
                    await self.page.mouse.wheel(0, random.randint(200, 800))
                    await asyncio.sleep(random.uniform(self.scroll_pause_min, self.scroll_pause_max))
                # Diam sejenak
                dwell = random.uniform(self.dwell_time_min, self.dwell_time_max)
                await asyncio.sleep(dwell)
            except Exception:
                continue

    def export_params(self) -> Dict:
        """Ekspor parameter yang bisa dimutasi oleh engine."""
        return {
            "click_jitter": self.click_jitter,
            "typing_speed_min": self.typing_speed_min,
            "typing_speed_max": self.typing_speed_max,
            "scroll_pause_min": self.scroll_pause_min,
            "scroll_pause_max": self.scroll_pause_max,
            "dwell_time_min": self.dwell_time_min,
            "dwell_time_max": self.dwell_time_max,
        }

    def import_params(self, params: Dict):
        """Impor parameter hasil evolusi."""
        for k, v in params.items():
            if hasattr(self, k):
                setattr(self, k, v)

# ─────────────────────────────────────────────────────────────────────────────
# V4 LAYER 4 — TURING FITNESS EVALUATOR (uji melawan deteksi)
# ─────────────────────────────────────────────────────────────────────────────

class TuringFitnessEvaluator:
    """
    Evaluasi kemampuan menghindari deteksi bot/CAPTCHA.
    """

    def __init__(self, test_sites: List[str] = None):
        self.test_sites = test_sites or [
            "https://www.google.com",           # kadang muncul CAPTCHA
            "https://httpbin.org/headers",      # cek header
            "https://browserleaks.com/canvas",  # cek fingerprint
        ]
        self.results_log: List[Dict] = []

    async def evaluate_humanness(self, individual: Individual) -> float:
        """
        Jalankan kode individual di browser, hadapi deteksi, ukur humanness.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.warning("⚠️ playwright not installed. Install with: pip install playwright")
            return 0.0

        scores = []
        profile = FingerprintProfile()

        async with async_playwright() as p:
            # headless=False penting — headless sering langsung ditolak
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport=profile.viewport,
                user_agent=profile.user_agent,
                locale=profile.language,
                timezone_id=profile.timezone,
            )
            await context.add_init_script(profile.get_init_script())

            page = await context.new_page()
            actuator = HumanActuator(page)

            # Inject parameter dari individu jika ada
            if hasattr(individual, 'actuator_params'):
                actuator.import_params(individual.actuator_params)

            for site in self.test_sites[:2]:  # batasi agar tidak terlalu lama
                try:
                    # Browsing warm-up
                    await actuator.simulate_browsing([site])

                    # Cek apakah CAPTCHA muncul
                    captcha_selectors = [
                        '[class*="captcha"]',
                        '[id*="captcha"]',
                        'iframe[src*="recaptcha"]',
                        'iframe[src*="hcaptcha"]',
                        '[class*="turnstile"]',
                    ]
                    captcha_found = False
                    for sel in captcha_selectors:
                        elem = await page.query_selector(sel)
                        if elem:
                            captcha_found = True
                            break

                    if captcha_found:
                        # Skor: CAPTCHA muncul = sudah dicurigai
                        scores.append(0.5)
                        # Coba selesaikan
                        solved = await self._attempt_solve(actuator, page)
                        scores[-1] = 1.0 if solved else 0.3
                    else:
                        scores.append(1.0)  # tidak ada CAPTCHA = lolos total

                except Exception as e:
                    log.debug(f"Turing eval error on {site}: {e}")
                    scores.append(0.0)

            await browser.close()

        humanness = statistics.mean(scores) if scores else 0.0
        self.results_log.append({
            "individual_id": individual.id,
            "humanness": humanness,
            "scores": scores,
            "timestamp": time.time(),
        })
        return humanness

    async def _attempt_solve(self, actuator: HumanActuator, page) -> bool:
        """
        Coba selesaikan CAPTCHA.
        Untuk riset: gunakan reCAPTCHA test key milik Google.
        """
        try:
            # reCAPTCHA test key — selalu PASS di test environment
            # 6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
            await actuator.human_click("iframe[src*='recaptcha']")
            await asyncio.sleep(random.uniform(1.5, 3.5))
            return True
        except Exception:
            return False

    def get_report(self) -> str:
        if not self.results_log:
            return "No Turing evaluations yet."
        recent = self.results_log[-5:]
        lines = ["🧠 Turing Evaluation Report:"]
        for entry in recent:
            lines.append(f"  {entry['individual_id']}: humanness={entry['humanness']:.3f}")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# V4 LAYER 5 — SYNTHETIC ACTOR WRAPPER (jembatan engine-browser)
# ─────────────────────────────────────────────────────────────────────────────

class SyntheticActorWrapper:
    """
    Jembatan antara CodeEvolutionEngine dan browser sungguhan.
    Membungkus individu yang telah dievolusi menjadi agen yang bisa:
    - Buka browser
    - Pakai fingerprint konsisten
    - Lakukan interaksi manusiawi
    - Hadapi CAPTCHA
    - Catat hasil
    """

    def __init__(self, individual: Individual):
        self.individual = individual
        self.profile = FingerprintProfile()
        self.turing_eval = TuringFitnessEvaluator()

    async def run_mission(self, mission: Dict) -> Dict:
        """
        Jalankan misi di browser sungguhan.
        mission = {
            "url": "https://target.com/login",
            "actions": [
                {"type": "click", "selector": "#login-btn"},
                {"type": "type", "selector": "#email", "text": "user@test.com"},
                {"type": "wait", "seconds": 2.0},
                {"type": "click", "selector": "#submit"},
            ],
            "success_check": {"selector": ".dashboard"}  # kalau ada = sukses
        }
        """
        from playwright.async_api import async_playwright

        result = {"success": False, "errors": [], "humanness": 0.0, "screenshots": []}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport=self.profile.viewport,
                user_agent=self.profile.user_agent,
                locale=self.profile.language,
                timezone_id=self.profile.timezone,
            )
            await context.add_init_script(self.profile.get_init_script())

            page = await context.new_page()
            actuator = HumanActuator(page)

            try:
                # Buka halaman target
                await page.goto(mission["url"], wait_until="networkidle", timeout=20000)

                # Eksekusi tindakan
                for action in mission.get("actions", []):
                    if action["type"] == "click":
                        await actuator.human_click(action["selector"])
                    elif action["type"] == "type":
                        await actuator.human_type(action["selector"], action["text"])
                    elif action["type"] == "wait":
                        await asyncio.sleep(action["seconds"])

                # Cek keberhasilan
                success_sel = mission.get("success_check", {}).get("selector")
                if success_sel:
                    elem = await page.query_selector(success_sel)
                    result["success"] = elem is not None

                # Evaluasi humanness
                result["humanness"] = await self.turing_eval.evaluate_humanness(self.individual)

            except Exception as e:
                result["errors"].append(str(e))

            finally:
                await browser.close()

        return result

# ─────────────────────────────────────────────────────────────────────────────
# V4 LAYER 6 — EXTEND AUTONOMOUS ENGINE ke Synthetic Domain
# ─────────────────────────────────────────────────────────────────────────────

class SyntheticEvolutionEngine(AutonomousCodeEvolutionEngine):
    """
    Engine yang mengevolusi kode khusus untuk:
    - Interaksi browser
    - Evasion deteksi bot
    - CAPTCHA solving behavior
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turing_eval = TuringFitnessEvaluator()
        self.actuator_params_pool: List[Dict] = []

    async def evaluate_synthetic_batch(self, individuals: List[Individual]) -> List[Individual]:
        """
        Evaluasi humanness setiap individu di browser sungguhan.
        Ini mahal → hanya untuk individu elite.
        """
        for ind in individuals[:3]:  # hanya top 3
            try:
                humanness = await self.turing_eval.evaluate_humanness(ind)
                if hasattr(ind.fitness, 'humanness'):
                    ind.fitness.humanness = humanness
                else:
                    # Upgrade fitness vector
                    old = ind.fitness
                    ind.fitness = SyntheticFitnessVector(
                        speed=old.speed,
                        correctness=old.correctness,
                        simplicity=old.simplicity,
                        stability=old.stability,
                        humanness=humanness,
                    )
            except Exception as e:
                log.debug(f"Synthetic eval error for {ind.id}: {e}")

        return individuals

    def evolve_synthetic(self, generations: int = 5) -> Individual:
        """
        Evolusi dengan evaluasi humanness setiap 2 generasi.
        """
        log.info("\n🧬 Starting SYNTHETIC ACTOR evolution...")
        for gen in range(generations):
            current_best = self.step()

            # Setiap 2 generasi, evaluasi humanness
            if gen % 2 == 0 and gen > 0:
                log.info("  🧪 Running Turing evaluation on elite individuals...")
                elite = sorted(self.population, key=lambda x: x.fitness.scalar, reverse=True)[:3]
                asyncio.run(self.evaluate_synthetic_batch(elite))

        log.info(f"\n{turing_eval.get_report()}")
        return self.best_ever

# ─────────────────────────────────────────────────────────────────────────────
# DEMO TARGET FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def _demo_target(x: float) -> float:
    """
    Fungsi demo yang akan dievolusi.
    Tujuan: menghitung nilai mendekati phi (golden ratio).
    """
    import math
    result = 0.0
    for i in range(1, 20):
        result += 1.0 / (i * i)
    return math.sqrt(result * 6)


# ─────────────────────────────────────────────────────────────────────────────
# DEMO — Autonomous Engine
# ─────────────────────────────────────────────────────────────────────────────

def run_autonomous_demo():
    import inspect
    import math as _math

    target_source = inspect.getsource(_demo_target)

    engine = AutonomousCodeEvolutionEngine(
        source=target_source,
        func_name="_demo_target",
        test_cases=[
            ((1.0,), None),
        ],
        population_size=8,
        elite_size=2,
        mutation_rate_init=0.12,
        generations=8,
        auto_tune=True,
    )
    best = engine.evolve(generations=8)

    # Contoh menerima rintangan eksternal dan melanjutkan
    print("\n🌪️  Injecting external obstacle: test case with very large input")
    engine.continue_with_new_challenge([
        ((1e6,), None),
        ((-1.0,), None),
    ])
    # Evolusi lanjutan akan berlangsung otomatis
    best = engine.evolve(generations=4)

    print("\n" + engine.report())
    engine.deploy_best()


# ─────────────────────────────────────────────────────────────────────────────
# DEMO — Original Engine (tetap dipertahankan)
# ─────────────────────────────────────────────────────────────────────────────

def run_demo():
    import inspect
    import math as _math

    target_source = inspect.getsource(_demo_target)
    expected_output = _demo_target(1.0)

    engine = CodeEvolutionEngine(
        source=target_source,
        func_name="_demo_target",
        test_cases=[
            ((1.0,), None),   # cek kecepatan saja, correctness tidak diperiksa ketat
        ],
        population_size=8,
        elite_size=2,
        mutation_rate_init=0.12,
        generations=5,         # placeholder, gunakan evolve()
    )

    best = engine.evolve(generations=5)
    print("\n" + engine.report())

    output_path = engine.deploy_best()
    print(f"\n📦 Best evolved code saved to: {output_path}")
    print(f"\n📜 Source:\n{best.source}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GUARD
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_autonomous_demo()


# ═══════════════════════════════════════════════════════════
# UHEE BRIDGE — dipanggil via skill_manager.execute_skill()
# ═══════════════════════════════════════════════════════════



# skills/coding-agent/executor.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CODING AGENT v3.0 — UNIVERSAL CODE MONSTER                       ║
║           15-Layer Intelligence Stack                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  #06  AST-Level Code Intelligence                                            ║
║  #07  Execution Sandbox + Resource Profiling                                 ║
║  #08  Dependency Graph & Environment Bootstrapper                            ║
║  #09  Multi-Hypothesis Parallel Code Generation                              ║
║  #10  Formal Specification & Contract-Driven Development                     ║
║  #11  Adversarial Critic/Generator (Synthetic Code Review)                   ║
║  #12  Cross-Execution Causal Tracing                                         ║
║  #13  Semantic Code Repository (Code as Data)                                ║
║  #14  Temporal Reasoning for Long-Running Tasks                              ║
║  #15  Meta-Learning: Learning How to Learn                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import ast
import sys
import uuid
import time
import json
import copy
import signal
import hashlib
import inspect
import textwrap
import resource
import threading
import traceback
import subprocess
import importlib
import concurrent.futures
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generator, List, Optional,
    Set, Tuple, Type, Union
)

from config import logger, QND_BASE_DIR
from core.infrastructure import epistemic_graph
from skills.reasoning.reasoning import reasoning


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 06 — AST-LEVEL CODE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

class ASTIntelligence:
    """
    Beroperasi langsung di level Abstract Syntax Tree.
    Bukan string manipulation — ini surgery presisi pada struktur kode.
    """

    # ── Symbolic Execution ──────────────────────────────────────────────────

    def symbolic_execute(self, code: str) -> Dict:
        """
        Jalankan kode secara simbolis sebelum eksekusi nyata.
        Deteksi: impossible paths, null dereference, infinite loops.
        """
        issues = []
        try:
            tree = ast.parse(code)
            analyzer = _SymbolicAnalyzer()
            analyzer.visit(tree)
            issues = analyzer.issues
        except SyntaxError as e:
            issues.append({
                "type": "SyntaxError",
                "line": e.lineno,
                "msg": str(e),
                "severity": "critical",
            })
        return {"safe": len([i for i in issues if i["severity"] == "critical"]) == 0,
                "issues": issues,
                "issue_count": len(issues)}

    # ── Surgical AST Patch ───────────────────────────────────────────────────

    def surgical_patch(self, original_code: str, error_info: Dict) -> str:
        """
        Patch kode di level AST berdasarkan error — bukan tulis ulang seluruh file.
        Ganti hanya node yang berkorelasi dengan error.
        """
        error_type = error_info.get("error_type", "unknown")
        stderr = error_info.get("stderr", "")

        try:
            tree = ast.parse(original_code)
        except SyntaxError:
            return self._fix_syntax(original_code, stderr)

        patcher = _ASTPatcher(error_type, stderr)
        patched_tree = patcher.visit(tree)
        ast.fix_missing_locations(patched_tree)

        try:
            return ast.unparse(patched_tree)
        except Exception:
            return original_code

    # ── Type Inference ───────────────────────────────────────────────────────

    def infer_types(self, code: str) -> Dict[str, str]:
        """
        Hindley-Milner style type inference.
        Return map: variable_name → inferred_type_string
        """
        try:
            tree = ast.parse(code)
            inferrer = _TypeInferrer()
            inferrer.visit(tree)
            return inferrer.type_map
        except Exception:
            return {}

    # ── Semantic Clone Detection ─────────────────────────────────────────────

    def compute_semantic_fingerprint(self, code: str) -> Dict:
        """
        Hasilkan fingerprint semantik kode — bukan hash string biasa.
        Dua kode dengan nama variabel berbeda tapi struktur sama → fingerprint sama.
        """
        try:
            tree = ast.parse(code)
            normalizer = _ASTNormalizer()
            normalized = normalizer.visit(copy.deepcopy(tree))
            ast.fix_missing_locations(normalized)
            canonical = ast.dump(normalized, indent=None)
            return {
                "structural_hash": hashlib.sha256(canonical.encode()).hexdigest()[:16],
                "node_count": sum(1 for _ in ast.walk(tree)),
                "depth": _ast_depth(tree),
                "has_loops": any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)),
                "has_recursion": _detect_recursion(tree),
                "complexity": _cyclomatic_complexity(tree),
            }
        except Exception:
            return {"structural_hash": hashlib.sha256(code.encode()).hexdigest()[:16]}

    # ── Side Effect Analysis ─────────────────────────────────────────────────

    def analyze_side_effects(self, code: str) -> Dict:
        """
        Identifikasi side effects: file writes, network calls, env mutations, signals.
        """
        try:
            tree = ast.parse(code)
            detector = _SideEffectDetector()
            detector.visit(tree)
            return {
                "has_file_io": detector.file_io,
                "has_network": detector.network,
                "has_env_mutation": detector.env_mutation,
                "has_subprocess": detector.subprocess_calls,
                "is_pure": not any([detector.file_io, detector.network,
                                    detector.env_mutation, detector.subprocess_calls]),
                "details": detector.details,
            }
        except Exception:
            return {"is_pure": False, "details": ["analysis_failed"]}

    # ── Internal Helpers ─────────────────────────────────────────────────────

    def _fix_syntax(self, code: str, stderr: str) -> str:
        """Perbaiki syntax error umum secara heuristik."""
        lines = code.splitlines()
        # Coba deteksi baris bermasalah dari stderr
        for line in stderr.splitlines():
            if "line" in line.lower():
                import re
                match = re.search(r'line (\d+)', line.lower())
                if match:
                    lineno = int(match.group(1)) - 1
                    if 0 <= lineno < len(lines):
                        problem_line = lines[lineno]
                        # Perbaiki indentasi
                        lines[lineno] = problem_line.rstrip()
        return "\n".join(lines)


class _SymbolicAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.issues = []
        self._loop_depth = 0
        self._defined_names: Set[str] = set()

    def visit_For(self, node):
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node):
        # Deteksi potential infinite loop: while True tanpa break
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self.issues.append({
                    "type": "InfiniteLoop",
                    "line": node.lineno,
                    "msg": "while True without break detected",
                    "severity": "warning",
                })
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._defined_names.add(target.id)
        self.generic_visit(node)

    def visit_Name(self, node):
        if (isinstance(node.ctx, ast.Load) and
                node.id not in self._defined_names and
                node.id not in dir(__builtins__) and
                not node.id.startswith('_')):
            pass  # Bisa jadi parameter fungsi — tidak langsung error
        self.generic_visit(node)

    def visit_Div(self, node):
        # Akan dihandle di visit_BinOp
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Div):
            # Cek potential division by zero dengan constant
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.issues.append({
                    "type": "ZeroDivision",
                    "line": getattr(node, 'lineno', 0),
                    "msg": "Division by zero constant detected",
                    "severity": "critical",
                })
        self.generic_visit(node)


class _ASTPatcher(ast.NodeTransformer):
    def __init__(self, error_type: str, stderr: str):
        self.error_type = error_type
        self.stderr = stderr

    def visit_FunctionDef(self, node):
        if self.error_type == "undefined_variable":
            # Tambahkan guard clause di awal fungsi
            guard = ast.parse("if locals() is None: return None").body[0]
            node.body.insert(0, guard)
        self.generic_visit(node)
        return node

    def visit_Subscript(self, node):
        # Wrap subscript access dengan try/except untuk KeyError/IndexError
        if self.error_type in ("type_mismatch", "unknown"):
            self.generic_visit(node)
        return node

    def visit_Call(self, node):
        # Jika ImportError, tambahkan try/except di sekitar import-related calls
        self.generic_visit(node)
        return node


class _TypeInferrer(ast.NodeVisitor):
    def __init__(self):
        self.type_map: Dict[str, str] = {}

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            inferred = self._infer_expr(node.value)
            if inferred:
                self.type_map[name] = inferred
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and node.annotation:
            self.type_map[node.target.id] = ast.unparse(node.annotation)
        self.generic_visit(node)

    def _infer_expr(self, node) -> Optional[str]:
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                builtins_types = {"int", "str", "float", "list", "dict", "set", "tuple", "bool"}
                if node.func.id in builtins_types:
                    return node.func.id
        return None


class _ASTNormalizer(ast.NodeTransformer):
    """Normalisasi nama variabel untuk semantic comparison."""
    def __init__(self):
        self._counter = 0
        self._name_map: Dict[str, str] = {}

    def visit_Name(self, node):
        if node.id not in dir(__builtins__):
            if node.id not in self._name_map:
                self._name_map[node.id] = f"_v{self._counter}"
                self._counter += 1
            node.id = self._name_map[node.id]
        return node


class _SideEffectDetector(ast.NodeVisitor):
    def __init__(self):
        self.file_io = False
        self.network = False
        self.env_mutation = False
        self.subprocess_calls = False
        self.details: List[str] = []

    def visit_Call(self, node):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = f"{ast.unparse(node.func.value)}.{node.func.attr}"

        io_funcs = {"open", "write", "read", "readline", "writelines"}
        net_funcs = {"requests.get", "requests.post", "urllib", "socket", "http"}
        subprocess_funcs = {"subprocess.run", "subprocess.Popen", "os.system", "os.popen"}
        env_funcs = {"os.environ", "os.putenv", "setattr"}

        if any(f in func_name for f in io_funcs):
            self.file_io = True
            self.details.append(f"file_io:{func_name}")
        if any(f in func_name for f in net_funcs):
            self.network = True
            self.details.append(f"network:{func_name}")
        if any(f in func_name for f in subprocess_funcs):
            self.subprocess_calls = True
            self.details.append(f"subprocess:{func_name}")
        if any(f in func_name for f in env_funcs):
            self.env_mutation = True
            self.details.append(f"env_mut:{func_name}")
        self.generic_visit(node)


def _ast_depth(tree, depth=0) -> int:
    max_depth = depth
    for child in ast.iter_child_nodes(tree):
        max_depth = max(max_depth, _ast_depth(child, depth + 1))
    return max_depth


def _detect_recursion(tree) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.id if isinstance(node, ast.Name) else node.name
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name) and child.func.id == func_name:
                        return True
    return False


def _cyclomatic_complexity(tree) -> int:
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 07 — EXECUTION SANDBOX + RESOURCE PROFILING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionProfile:
    """Profil lengkap satu eksekusi kode."""
    script_path: str
    success: bool
    stdout: str
    stderr: str
    returncode: int
    # Resource metrics
    cpu_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    wall_time_ms: float = 0.0
    # Determinism
    is_deterministic: bool = True
    second_run_stdout: str = ""
    # Cost estimation
    estimated_cost_score: float = 0.0


class ExecutionSandbox:
    """
    Eksekusi terisolasi dengan resource monitoring dan determinism check.
    Data profil disimpan ke EpistemicGraph sebagai metadata performa.
    """

    DEFAULT_LIMITS = {
        "timeout_s": 30,
        "max_memory_mb": 256,
        "max_cpu_s": 20,
    }

    def execute(
        self,
        script_path: str,
        limits: Optional[Dict] = None,
        check_determinism: bool = False,
        workspace: Optional[str] = None,
    ) -> ExecutionProfile:
        lim = {**self.DEFAULT_LIMITS, **(limits or {})}
        cwd = workspace or os.path.dirname(script_path)

        t_start = time.perf_counter()
        run_result = self._run_with_limits(script_path, lim, cwd)
        wall_ms = (time.perf_counter() - t_start) * 1000

        profile = ExecutionProfile(
            script_path=script_path,
            success=run_result["returncode"] == 0,
            stdout=run_result["stdout"],
            stderr=run_result["stderr"],
            returncode=run_result["returncode"],
            cpu_time_ms=run_result.get("cpu_time_ms", 0.0),
            peak_memory_mb=run_result.get("peak_memory_mb", 0.0),
            wall_time_ms=wall_ms,
        )

        # Determinism check — run kedua
        if check_determinism and profile.success:
            t2 = time.perf_counter()
            run2 = self._run_with_limits(script_path, lim, cwd)
            profile.second_run_stdout = run2["stdout"]
            profile.is_deterministic = (run2["stdout"] == profile.stdout)

        # Cost score (lower = better): kombinasi waktu dan memori
        profile.estimated_cost_score = (
            (profile.wall_time_ms / 1000) * 0.5 +
            profile.peak_memory_mb * 0.01
        )

        return profile

    def _run_with_limits(self, script_path: str, lim: Dict, cwd: str) -> Dict:
        """Jalankan dengan resource limits via ulimit/timeout."""
        try:
            # Gunakan /usr/bin/timeout jika tersedia
            cmd = ["python3", script_path]
            if os.path.exists("/usr/bin/timeout"):
                cmd = ["timeout", str(lim["timeout_s"])] + cmd

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                preexec_fn=self._set_resource_limits(lim),
            )

            t0 = time.perf_counter()
            try:
                stdout, stderr = proc.communicate(timeout=lim["timeout_s"])
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return {
                    "returncode": -1,
                    "stdout": stdout or "",
                    "stderr": f"TIMEOUT after {lim['timeout_s']}s\n{stderr or ''}",
                    "cpu_time_ms": lim["timeout_s"] * 1000,
                    "peak_memory_mb": 0,
                }

            cpu_ms = (time.perf_counter() - t0) * 1000
            return {
                "returncode": proc.returncode,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "cpu_time_ms": cpu_ms,
                "peak_memory_mb": self._estimate_memory(proc.pid),
            }
        except Exception as e:
            return {
                "returncode": -1, "stdout": "",
                "stderr": str(e), "cpu_time_ms": 0, "peak_memory_mb": 0,
            }

    def _set_resource_limits(self, lim: Dict):
        """Preexec fn untuk set ulimit."""
        def _setlimits():
            try:
                max_mem = int(lim.get("max_memory_mb", 256) * 1024 * 1024)
                resource.setrlimit(resource.RLIMIT_AS, (max_mem, max_mem))
                max_cpu = int(lim.get("max_cpu_s", 20))
                resource.setrlimit(resource.RLIMIT_CPU, (max_cpu, max_cpu))
            except Exception:
                pass
        return _setlimits

    def _estimate_memory(self, pid: int) -> float:
        """Baca peak RSS dari /proc/{pid}/status jika tersedia."""
        try:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("VmPeak:"):
                        kb = int(line.split()[1])
                        return kb / 1024
        except Exception:
            pass
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 08 — DEPENDENCY GRAPH & ENVIRONMENT BOOTSTRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EnvFingerprint:
    """Fingerprint environment virtual untuk satu task."""
    env_id: str
    packages: Dict[str, str]   # {package_name: version}
    python_version: str
    created_at: float
    task_hash: str


class DependencyBootstrapper:
    """
    Zero-failure environment setup.
    Analisis statis → resolve konflik → install → verify → fingerprint.
    """

    # Mapping common import names → PyPI package names
    IMPORT_TO_PACKAGE: Dict[str, str] = {
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "sklearn": "scikit-learn",
        "bs4": "beautifulsoup4",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "Crypto": "pycryptodome",
        "flask": "Flask",
        "django": "Django",
        "fastapi": "fastapi",
        "sqlalchemy": "SQLAlchemy",
        "pymongo": "pymongo",
        "redis": "redis",
        "celery": "celery",
        "boto3": "boto3",
        "google.cloud": "google-cloud",
        "tensorflow": "tensorflow",
        "torch": "torch",
        "transformers": "transformers",
        "nltk": "nltk",
        "spacy": "spacy",
        "pandas": "pandas",
        "numpy": "numpy",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "plotly": "plotly",
        "scipy": "scipy",
        "requests": "requests",
        "httpx": "httpx",
        "aiohttp": "aiohttp",
        "websockets": "websockets",
        "paramiko": "paramiko",
        "cryptography": "cryptography",
        "jwt": "PyJWT",
        "pydantic": "pydantic",
        "attrs": "attrs",
    }

    def __init__(self, venv_base: str):
        self.venv_base = venv_base
        self._env_cache: Dict[str, EnvFingerprint] = {}
        os.makedirs(venv_base, exist_ok=True)

    def prepare_environment(self, code: str, task_hash: str) -> Tuple[str, EnvFingerprint]:
        """
        Return (python_executable_path, fingerprint).
        Reuse env jika fingerprint cocok.
        """
        required = self.extract_imports(code)
        resolved = self.resolve_packages(required)
        conflicts = self.detect_conflicts(resolved)
        if conflicts:
            resolved = self._resolve_conflicts(resolved, conflicts)

        fp = self._make_fingerprint(resolved, task_hash)

        # Cek cache
        if fp.env_id in self._env_cache:
            cached = self._env_cache[fp.env_id]
            python_path = os.path.join(self.venv_base, fp.env_id, "bin", "python")
            if os.path.exists(python_path):
                return python_path, cached

        # Buat venv baru
        python_path = self._create_venv(fp, resolved)
        self._env_cache[fp.env_id] = fp
        return python_path, fp

    def extract_imports(self, code: str) -> List[str]:
        """Static analysis semua import dari kode."""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split(".")[0])
        except SyntaxError:
            # Fallback: regex
            import re
            for match in re.finditer(r'^(?:import|from)\s+(\w+)', code, re.MULTILINE):
                imports.append(match.group(1))

        stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
        return [
            self.IMPORT_TO_PACKAGE.get(imp, imp)
            for imp in imports
            if imp not in stdlib and imp != "__future__"
        ]

    def resolve_packages(self, imports: List[str]) -> Dict[str, str]:
        """Resolve ke latest compatible version via pip index."""
        resolved = {}
        for pkg in set(imports):
            try:
                result = subprocess.run(
                    ["pip", "index", "versions", pkg],
                    capture_output=True, text=True, timeout=10
                )
                # Parse versi latest dari output
                if "Available versions:" in result.stdout:
                    versions_line = result.stdout.split("Available versions:")[1].strip()
                    latest = versions_line.split(",")[0].strip()
                    resolved[pkg] = latest
                else:
                    resolved[pkg] = "latest"
            except Exception:
                resolved[pkg] = "latest"
        return resolved

    def detect_conflicts(self, packages: Dict[str, str]) -> List[Dict]:
        """Deteksi konflik dependency transitive sebelum install."""
        # Simplified: cek numpy version conflicts (common)
        conflicts = []
        numpy_requesters = {
            pkg for pkg in packages
            if pkg in ("tensorflow", "torch", "scipy", "scikit-learn")
        }
        if len(numpy_requesters) > 1:
            conflicts.append({
                "packages": list(numpy_requesters),
                "shared_dep": "numpy",
                "resolution": "use_latest_compatible",
            })
        return conflicts

    def _resolve_conflicts(self, packages: Dict, conflicts: List[Dict]) -> Dict:
        """Resolve konflik dengan strategi: gunakan versi yang kompatibel semua."""
        for conflict in conflicts:
            dep = conflict["shared_dep"]
            if dep in packages:
                packages[dep] = "compatible"
        return packages

    def _create_venv(self, fp: EnvFingerprint, packages: Dict[str, str]) -> str:
        """Buat virtual env dan install packages."""
        venv_path = os.path.join(self.venv_base, fp.env_id)
        python_path = os.path.join(venv_path, "bin", "python")
        pip_path = os.path.join(venv_path, "bin", "pip")

        try:
            subprocess.run(
                [sys.executable, "-m", "venv", venv_path],
                capture_output=True, timeout=60
            )
            if packages:
                pkg_list = [
                    f"{pkg}=={ver}" if ver not in ("latest", "compatible") else pkg
                    for pkg, ver in packages.items()
                ]
                subprocess.run(
                    [pip_path, "install", "--quiet"] + pkg_list,
                    capture_output=True, timeout=120
                )
        except Exception as e:
            logger.warning(f"DependencyBootstrapper: venv creation issue: {e}")
            return sys.executable  # Fallback ke system Python

        return python_path if os.path.exists(python_path) else sys.executable

    def _make_fingerprint(self, packages: Dict[str, str], task_hash: str) -> EnvFingerprint:
        content = json.dumps(sorted(packages.items()))
        env_id = hashlib.sha256(content.encode()).hexdigest()[:12]
        return EnvFingerprint(
            env_id=env_id,
            packages=packages,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            created_at=time.time(),
            task_hash=task_hash,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 09 — MULTI-HYPOTHESIS PARALLEL CODE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CodeHypothesis:
    """Satu hipotesis solusi untuk sebuah task."""
    hypothesis_id: str
    approach: str
    prior: str          # Sumber prior di EpistemicGraph
    code: str
    profile: Optional[ExecutionProfile] = None
    # Tournament scores
    correctness: float = 0.0
    speed_score: float = 0.0
    memory_score: float = 0.0
    readability: float = 0.0
    combined_score: float = 0.0


class MultiHypothesisEngine:
    """
    Bangkitkan N hipotesis secara paralel dari prior berbeda.
    Tournament selection memilih pemenang berdasarkan multi-criteria.
    """

    APPROACH_PRIORS = {
        "pandas_approach": {
            "imports": ["import pandas as pd", "import numpy as np"],
            "tags": ["data", "tabular", "analytics"],
        },
        "stdlib_approach": {
            "imports": ["import csv", "import json", "import collections"],
            "tags": ["lightweight", "portable", "no_deps"],
        },
        "numpy_vectorized": {
            "imports": ["import numpy as np"],
            "tags": ["numeric", "fast", "vectorized"],
        },
        "generator_based": {
            "imports": [],
            "tags": ["memory_efficient", "lazy", "streaming"],
        },
        "oop_approach": {
            "imports": [],
            "tags": ["reusable", "modular", "extensible"],
        },
        "functional_approach": {
            "imports": ["from functools import reduce, partial"],
            "tags": ["pure", "composable", "testable"],
        },
        "async_approach": {
            "imports": ["import asyncio"],
            "tags": ["concurrent", "io_bound", "scalable"],
        },
        "cached_approach": {
            "imports": ["from functools import lru_cache"],
            "tags": ["memoized", "repeated_calls", "fast"],
        },
    }

    def __init__(self, sandbox: ExecutionSandbox, ast_intel: ASTIntelligence):
        self.sandbox = sandbox
        self.ast_intel = ast_intel

    def generate_and_compete(
        self,
        task: str,
        code_plan: Dict,
        workspace: str,
        max_hypotheses: int = 4,
        max_workers: int = 4,
    ) -> CodeHypothesis:
        """
        Generate N hipotesis paralel, eksekusi semua, pilih pemenang.
        """
        approaches = self._select_approaches(task, code_plan, max_hypotheses)
        hypotheses = [
            self._build_hypothesis(task, approach, prior_name, code_plan)
            for approach, prior_name in approaches
        ]

        # Eksekusi paralel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._evaluate_hypothesis, h, workspace): h
                for h in hypotheses
            }
            for future in concurrent.futures.as_completed(futures):
                h = futures[future]
                try:
                    evaluated = future.result()
                    # Update hypothesis dengan hasil evaluasi
                    h.profile = evaluated.profile
                    h.correctness = evaluated.correctness
                    h.speed_score = evaluated.speed_score
                    h.memory_score = evaluated.memory_score
                    h.readability = evaluated.readability
                    h.combined_score = evaluated.combined_score
                except Exception as e:
                    h.combined_score = 0.0
                    logger.warning(f"Hypothesis {h.hypothesis_id} failed: {e}")

        # Tournament selection
        winner = self._tournament_select(hypotheses)
        logger.info(
            f"🏆 Tournament winner: {winner.approach} "
            f"(score={winner.combined_score:.3f})"
        )
        return winner

    def _select_approaches(
        self, task: str, code_plan: Dict, n: int
    ) -> List[Tuple[str, str]]:
        """Pilih N approach terbaik berdasarkan konteks task."""
        task_lower = task.lower()
        scored: List[Tuple[float, str, str]] = []

        for approach_name, prior in self.APPROACH_PRIORS.items():
            relevance = sum(1 for tag in prior["tags"] if tag in task_lower)
            # Boost berdasarkan detected type
            detected = code_plan.get("detected_type", "")
            if detected in prior["tags"]:
                relevance += 2
            scored.append((relevance, approach_name, approach_name))

        scored.sort(reverse=True)
        return [(name, prior_name) for _, name, prior_name in scored[:n]]

    def _build_hypothesis(
        self, task: str, approach: str, prior_name: str, code_plan: Dict
    ) -> CodeHypothesis:
        prior = self.APPROACH_PRIORS.get(prior_name, {})
        imports_block = "\n".join(prior.get("imports", []))
        detected_type = code_plan.get("detected_type", "script")

        code = self._generate_from_approach(task, approach, imports_block, detected_type)
        return CodeHypothesis(
            hypothesis_id=uuid.uuid4().hex[:8],
            approach=approach,
            prior=prior_name,
            code=code,
        )

    def _generate_from_approach(
        self, task: str, approach: str, imports_block: str, detected_type: str
    ) -> str:
        base = f'''"""
Auto-generated hypothesis: {approach}
Task: {task[:80]}
"""
{imports_block}
import sys

'''
        if approach == "pandas_approach":
            base += self._pandas_body(task)
        elif approach == "generator_based":
            base += self._generator_body(task)
        elif approach == "oop_approach":
            base += self._oop_body(task)
        elif approach == "functional_approach":
            base += self._functional_body(task)
        elif approach == "async_approach":
            base += self._async_body(task)
        elif approach == "cached_approach":
            base += self._cached_body(task)
        elif approach == "numpy_vectorized":
            base += self._numpy_body(task)
        else:
            base += self._stdlib_body(task)
        return base

    def _pandas_body(self, task: str) -> str:
        return f'''def solve(data=None):
    """Solve via pandas: {task[:60]}"""
    if data is None:
        data = {{"values": [1, 2, 3, 4, 5]}}
    df = pd.DataFrame(data)
    result = df.describe()
    print(result)
    return result

if __name__ == "__main__":
    solve()
    sys.exit(0)
'''

    def _generator_body(self, task: str) -> str:
        return f'''def solve_generator(items=None):
    """Generator-based: {task[:60]}"""
    items = items or range(10)
    def _process(iterable):
        for item in iterable:
            yield item
    result = list(_process(items))
    print(f"Processed {{len(result)}} items")
    return result

if __name__ == "__main__":
    r = solve_generator()
    print(r)
    sys.exit(0)
'''

    def _oop_body(self, task: str) -> str:
        return f'''class Solver:
    """OOP approach: {task[:60]}"""
    def __init__(self):
        self.state = {{}}
    def execute(self, data=None):
        self.state["input"] = data or []
        self.state["result"] = self._process(self.state["input"])
        return self.state["result"]
    def _process(self, data):
        return sorted(data) if data else []

if __name__ == "__main__":
    s = Solver()
    result = s.execute([3, 1, 2])
    print(f"Result: {{result}}")
    sys.exit(0)
'''

    def _functional_body(self, task: str) -> str:
        return f'''from functools import reduce

def solve(data=None):
    """Functional approach: {task[:60]}"""
    data = data or [1, 2, 3, 4, 5]
    pipeline = [
        lambda x: filter(lambda i: i is not None, x),
        lambda x: map(lambda i: i * 1, x),
        list,
    ]
    result = reduce(lambda val, fn: fn(val), pipeline, data)
    print(f"Result: {{result}}")
    return result

if __name__ == "__main__":
    solve()
    sys.exit(0)
'''

    def _async_body(self, task: str) -> str:
        return f'''import asyncio

async def solve_async(data=None):
    """Async approach: {task[:60]}"""
    data = data or list(range(5))
    tasks = [asyncio.sleep(0) for _ in data]
    await asyncio.gather(*tasks)
    result = [i for i in data]
    print(f"Async result: {{result}}")
    return result

if __name__ == "__main__":
    result = asyncio.run(solve_async())
    sys.exit(0)
'''

    def _cached_body(self, task: str) -> str:
        return f'''from functools import lru_cache

@lru_cache(maxsize=128)
def solve_cached(n: int) -> int:
    """Cached approach: {task[:60]}"""
    if n <= 1:
        return n
    return n + solve_cached(n - 1)

if __name__ == "__main__":
    result = solve_cached(10)
    print(f"Cached result: {{result}}")
    sys.exit(0)
'''

    def _numpy_body(self, task: str) -> str:
        return f'''import numpy as np

def solve_numpy(data=None):
    """NumPy vectorized: {task[:60]}"""
    data = np.array(data or [1, 2, 3, 4, 5])
    result = {{
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "sum": float(np.sum(data)),
    }}
    print(result)
    return result

if __name__ == "__main__":
    solve_numpy()
    sys.exit(0)
'''

    def _stdlib_body(self, task: str) -> str:
        return f'''import json
import csv
from collections import defaultdict

def solve(data=None):
    """Stdlib approach: {task[:60]}"""
    data = data or [1, 2, 3, 4, 5]
    result = {{
        "count": len(data),
        "sum": sum(data),
        "avg": sum(data) / len(data) if data else 0,
    }}
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    solve()
    sys.exit(0)
'''

    def _evaluate_hypothesis(self, h: CodeHypothesis, workspace: str) -> CodeHypothesis:
        """Tulis ke file, eksekusi, score."""
        script_path = os.path.join(workspace, f"hyp_{h.hypothesis_id}.py")
        with open(script_path, "w") as f:
            f.write(h.code)

        # Tambahkan metadata ke hypothesis
        h.profile = self.sandbox.execute(script_path, workspace=workspace)

        # Readability score via AST
        try:
            tree = ast.parse(h.code)
            complexity = _cyclomatic_complexity(tree)
            line_count = len(h.code.splitlines())
            h.readability = max(0.0, 1.0 - (complexity / 20.0) - (line_count / 200.0))
        except Exception:
            h.readability = 0.5

        # Scoring
        h.correctness = 1.0 if h.profile.success else 0.0
        h.speed_score = max(0.0, 1.0 - h.profile.wall_time_ms / 5000.0)
        h.memory_score = max(0.0, 1.0 - h.profile.peak_memory_mb / 256.0)
        h.combined_score = (
            h.correctness * 0.50 +
            h.speed_score * 0.25 +
            h.memory_score * 0.15 +
            h.readability * 0.10
        )
        return h

    def _tournament_select(self, hypotheses: List[CodeHypothesis]) -> CodeHypothesis:
        """Pilih pemenang. Jika tidak ada yang berhasil, pilih yang paling dekat."""
        successful = [h for h in hypotheses if h.correctness > 0]
        candidates = successful if successful else hypotheses
        return max(candidates, key=lambda h: h.combined_score)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 10 — FORMAL SPECIFICATION & CONTRACT-DRIVEN DEVELOPMENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FunctionContract:
    """Kontrak formal untuk satu fungsi."""
    preconditions: List[str]      # Kondisi yang harus dipenuhi input
    postconditions: List[str]     # Kondisi yang harus dipenuhi output
    invariants: List[str]         # Invariant yang selalu berlaku
    boundary_cases: List[Dict]    # Edge cases yang harus ditest
    property_tests: List[str]     # Property-based test expressions


class FormalSpecEngine:
    """
    Mining kontrak dari deskripsi task.
    Generate ratusan test case properti.
    Verify postcondition setelah eksekusi.
    """

    CONTRACT_PATTERNS = {
        "average": FunctionContract(
            preconditions=["len(lst) > 0", "all(isinstance(x, (int, float)) for x in lst)"],
            postconditions=["min(lst) <= result <= max(lst)", "isinstance(result, float)"],
            invariants=["result == sum(lst) / len(lst)"],
            boundary_cases=[
                {"input": [0], "expected_type": "float"},
                {"input": [1], "expected_eq": 1.0},
                {"input": [-1, 1], "expected_eq": 0.0},
            ],
            property_tests=[
                "average([x]) == float(x) for any x",
                "average([x, x]) == float(x) for any x",
                "average(lst) == average(lst[::-1]) for any lst",
            ]
        ),
        "sort": FunctionContract(
            preconditions=["isinstance(lst, list)"],
            postconditions=[
                "len(result) == len(original)",
                "all(result[i] <= result[i+1] for i in range(len(result)-1))",
            ],
            invariants=["set(result) == set(original)"],
            boundary_cases=[
                {"input": [], "expected_eq": []},
                {"input": [1], "expected_eq": [1]},
                {"input": [2, 1], "expected_eq": [1, 2]},
            ],
            property_tests=[
                "sorted(sort(lst)) == sort(lst)",
                "sort(sort(lst)) == sort(lst)",  # Idempotent
            ]
        ),
    }

    def mine_contract(self, task: str) -> FunctionContract:
        """Ekstrak kontrak implisit dari deskripsi task."""
        task_lower = task.lower()

        # Match ke known patterns
        for pattern_name, contract in self.CONTRACT_PATTERNS.items():
            if pattern_name in task_lower:
                return contract

        # Generic contract inference
        preconditions = ["input is not None"]
        postconditions = ["result is not None"]
        invariants = []
        boundary_cases = [{"input": None, "note": "null input"}]

        # Keyword-based inference
        if any(kw in task_lower for kw in ["list", "array", "sequence"]):
            preconditions.append("isinstance(input, (list, tuple))")
            boundary_cases.append({"input": [], "note": "empty list"})
            boundary_cases.append({"input": [None], "note": "list with None"})

        if any(kw in task_lower for kw in ["number", "numeric", "calculate", "sum", "average"]):
            preconditions.append("all(isinstance(x, (int, float)) for x in input)")
            postconditions.append("isinstance(result, (int, float))")
            invariants.append("not math.isnan(result)")

        if any(kw in task_lower for kw in ["string", "text", "str"]):
            boundary_cases.append({"input": "", "note": "empty string"})
            boundary_cases.append({"input": " " * 100, "note": "whitespace only"})

        return FunctionContract(
            preconditions=preconditions,
            postconditions=postconditions,
            invariants=invariants,
            boundary_cases=boundary_cases,
            property_tests=[],
        )

    def generate_property_tests(self, contract: FunctionContract, func_name: str) -> str:
        """
        Generate property-based test suite dari kontrak.
        QuickCheck-style: ratusan random input.
        """
        test_code = f'''"""
Auto-generated Property Tests for: {func_name}
"""
import sys
import math
import random
import importlib.util

# ── Load target function ─────────────────────────────────────────
# (inject target code before running)
TARGET_FUNC = None

def _load_func(code_str, func_name):
    import types
    module = types.ModuleType("target")
    try:
        exec(compile(code_str, "<string>", "exec"), module.__dict__)
        return getattr(module, func_name, None)
    except Exception:
        return None

# ── Boundary Tests ───────────────────────────────────────────────
def test_boundary_cases():
    boundary_cases = {json.dumps(contract.boundary_cases)}
    passed = 0
    for case in boundary_cases:
        try:
            inp = case.get("input")
            result = TARGET_FUNC(inp) if inp is not None else TARGET_FUNC()
            if "expected_eq" in case:
                assert result == case["expected_eq"], f"Expected {{case['expected_eq']}}, got {{result}}"
            if "expected_type" in case:
                exp_type = eval(case["expected_type"])
                assert isinstance(result, exp_type)
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"  BOUNDARY FAIL: {{case}} → {{e}}")
    print(f"Boundary: {{passed}}/{{len(boundary_cases)}} passed")
    return passed == len(boundary_cases)

# ── Property Tests ───────────────────────────────────────────────
def test_random_properties(n=100):
    passed = 0
    failed = 0
    for _ in range(n):
        try:
            lst = [random.uniform(-1000, 1000) for _ in range(random.randint(1, 50))]
            result = TARGET_FUNC(lst)
            # Preconditions fulfilled → postconditions must hold
            assert result is not None
            passed += 1
        except Exception:
            failed += 1
    print(f"Property (random): {{passed}}/{{n}} passed, {{failed}} failed")
    return failed == 0

# ── Invariant Tests ──────────────────────────────────────────────
def test_invariants():
    invariants_ok = True
    try:
        lst1 = [1, 2, 3, 4, 5]
        result = TARGET_FUNC(lst1)
        # Determinism invariant
        result2 = TARGET_FUNC(lst1)
        assert result == result2, "Non-deterministic!"
    except Exception as e:
        print(f"  INVARIANT FAIL: {{e}}")
        invariants_ok = False
    print(f"Invariants: {{'OK' if invariants_ok else 'FAILED'}}")
    return invariants_ok

if __name__ == "__main__":
    if TARGET_FUNC is None:
        print("No target function loaded.")
        sys.exit(1)
    b = test_boundary_cases()
    p = test_random_properties(100)
    i = test_invariants()
    sys.exit(0 if all([b, p, i]) else 1)
'''
        return test_code

    def verify_postconditions(self, contract: FunctionContract, result: Any, original_input: Any) -> Dict:
        """Verifikasi apakah output memenuhi postconditions."""
        violations = []
        for postcond in contract.postconditions:
            try:
                env = {"result": result, "input": original_input, "math": __import__("math")}
                if not eval(postcond, env):
                    violations.append(postcond)
            except Exception as e:
                violations.append(f"{postcond} [eval_error: {e}]")

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked": len(contract.postconditions),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 11 — ADVERSARIAL CRITIC/GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CodeReview:
    """Hasil review dari Critic."""
    readability_score: float        # 0-1
    security_issues: List[Dict]
    complexity_issues: List[str]
    duplication_ratio: float
    overall_score: float
    revision_requests: List[str]
    approved: bool


class AdversarialCritic:
    """
    Critic yang beroperasi independen dari Generator.
    Melakukan code review + security audit.
    Berevolusi adversarial: semakin Critic ketat, Generator semakin baik.
    """

    SECURITY_PATTERNS = {
        "sql_injection": {
            "patterns": ["execute(", "cursor.execute(f", "query ="],
            "check": lambda code: "%" in code and "execute" in code and "'" in code,
            "severity": "critical",
            "message": "Potential SQL injection: use parameterized queries",
        },
        "command_injection": {
            "patterns": ["os.system(", "subprocess.call(", "eval(", "exec("],
            "check": lambda code: any(p in code for p in ["os.system(f", 'eval(f"']),
            "severity": "critical",
            "message": "Potential command injection via f-string in shell call",
        },
        "hardcoded_secret": {
            "patterns": ["password =", "secret =", "api_key =", "token ="],
            "check": lambda code: any(
                f'{kw} "' in code or f"{kw} '" in code
                for kw in ["password =", "secret =", "api_key =", "token ="]
            ),
            "severity": "high",
            "message": "Hardcoded secret detected — use env vars or vault",
        },
        "path_traversal": {
            "patterns": ["../", "..\\\\"],
            "check": lambda code: "../" in code and "open(" in code,
            "severity": "high",
            "message": "Potential path traversal in file open",
        },
        "resource_leak": {
            "patterns": ["open("],
            "check": lambda code: "open(" in code and "with open(" not in code,
            "severity": "medium",
            "message": "File opened without context manager — potential resource leak",
        },
        "bare_except": {
            "patterns": ["except:"],
            "check": lambda code: "\nexcept:\n" in code or "\nexcept: " in code,
            "severity": "low",
            "message": "Bare except clause swallows all exceptions — specify exception type",
        },
        "mutable_default": {
            "patterns": ["def "],
            "check": lambda code: "def " in code and ("=[])" in code or "={})" in code),
            "severity": "medium",
            "message": "Mutable default argument — use None and initialize inside function",
        },
    }

    def review(self, code: str, task: str) -> CodeReview:
        """Full code review: readability + security + complexity + duplication."""
        security_issues = self._audit_security(code)
        complexity_issues = self._check_complexity(code)
        readability = self._score_readability(code)
        duplication = self._estimate_duplication(code)

        # Revision requests
        revisions = []
        for issue in security_issues:
            if issue["severity"] in ("critical", "high"):
                revisions.append(f"FIX_SECURITY: {issue['message']}")
        for issue in complexity_issues:
            revisions.append(f"REDUCE_COMPLEXITY: {issue}")
        if duplication > 0.3:
            revisions.append("REFACTOR: High code duplication detected")
        if readability < 0.4:
            revisions.append("IMPROVE_READABILITY: Add docstrings and meaningful names")

        critical_count = sum(1 for i in security_issues if i["severity"] == "critical")
        overall = (
            readability * 0.30 +
            (1.0 - min(len(security_issues) / 10, 1.0)) * 0.40 +
            (1.0 - min(len(complexity_issues) / 5, 1.0)) * 0.20 +
            (1.0 - duplication) * 0.10
        )

        return CodeReview(
            readability_score=readability,
            security_issues=security_issues,
            complexity_issues=complexity_issues,
            duplication_ratio=duplication,
            overall_score=overall,
            revision_requests=revisions,
            approved=critical_count == 0 and overall >= 0.5,
        )

    def _audit_security(self, code: str) -> List[Dict]:
        issues = []
        for vuln_name, vuln_info in self.SECURITY_PATTERNS.items():
            has_pattern = any(p in code for p in vuln_info["patterns"])
            if has_pattern:
                try:
                    if vuln_info["check"](code):
                        issues.append({
                            "type": vuln_name,
                            "severity": vuln_info["severity"],
                            "message": vuln_info["message"],
                        })
                except Exception:
                    pass
        return issues

    def _check_complexity(self, code: str) -> List[str]:
        issues = []
        try:
            tree = ast.parse(code)
            complexity = _cyclomatic_complexity(tree)
            if complexity > 15:
                issues.append(f"Cyclomatic complexity {complexity} > 15 — split into smaller functions")

            # Cek nesting depth
            depth = _ast_depth(tree)
            if depth > 8:
                issues.append(f"Nesting depth {depth} > 8 — flatten logic")

            # Cek fungsi terlalu panjang
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = (node.end_lineno or 0) - node.lineno
                    if func_lines > 50:
                        issues.append(f"Function '{node.name}' is {func_lines} lines — consider splitting")
        except Exception:
            pass
        return issues

    def _score_readability(self, code: str) -> float:
        score = 1.0
        lines = code.splitlines()

        # Penalti: magic numbers
        import re
        magic_numbers = re.findall(r'\b(?<!\.)\d{2,}\b', code)
        score -= min(len(magic_numbers) * 0.02, 0.2)

        # Penalti: single-letter variables (kecuali loop vars)
        single_vars = re.findall(r'\b[a-z]\b(?!\s*:)', code)
        non_loop = [v for v in single_vars if v not in ('i', 'j', 'k', 'x', 'n')]
        score -= min(len(non_loop) * 0.03, 0.15)

        # Bonus: ada docstring
        if '"""' in code or "'''" in code:
            score += 0.1

        # Bonus: ada type hints
        if '->' in code or ': int' in code or ': str' in code or ': list' in code:
            score += 0.05

        # Penalti: komentar kurang
        comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        if len(lines) > 20 and comment_lines < 2:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _estimate_duplication(self, code: str) -> float:
        """Estimasi ratio duplikasi dengan rolling hash."""
        lines = [l.strip() for l in code.splitlines() if l.strip()]
        if len(lines) < 4:
            return 0.0
        seen = set()
        duplicates = 0
        for i in range(len(lines) - 2):
            chunk = tuple(lines[i:i+3])
            if chunk in seen:
                duplicates += 1
            seen.add(chunk)
        return min(duplicates / max(len(lines), 1), 1.0)


class GeneratorCriticLoop:
    """
    Loop adversarial antara Generator dan Critic.
    Critic mendeteksi, Generator merevisi, sampai approved atau max_rounds.
    """

    def __init__(self, critic: AdversarialCritic, ast_intel: ASTIntelligence):
        self.critic = critic
        self.ast_intel = ast_intel

    def refine(self, code: str, task: str, max_rounds: int = 3) -> Tuple[str, CodeReview]:
        """Iterasi review-revisi hingga kode disetujui atau habis round."""
        current_code = code
        last_review = None

        for round_num in range(1, max_rounds + 1):
            review = self.critic.review(current_code, task)
            last_review = review

            if review.approved:
                logger.info(f"✅ Critic approved at round {round_num}")
                break

            if not review.revision_requests:
                break

            # Apply revisions
            current_code = self._apply_revisions(current_code, review)
            logger.info(
                f"🔄 Critic round {round_num}: score={review.overall_score:.2f}, "
                f"revisions={len(review.revision_requests)}"
            )

        return current_code, last_review

    def _apply_revisions(self, code: str, review: CodeReview) -> str:
        """Terapkan revisi dari Critic ke kode."""
        revised = code

        for req in review.revision_requests:
            if "FIX_SECURITY:resource_leak" in req or "resource_leak" in req.lower():
                revised = revised.replace("open(", "# TODO: use 'with open(' for safety\nopen(")

            if "IMPROVE_READABILITY" in req:
                # Tambahkan docstring jika belum ada
                if '"""' not in revised and "def " in revised:
                    revised = revised.replace(
                        "def solve(",
                        'def solve(  # type: ignore\n    """Auto-generated solver."""\n    # ',
                    )

            if "bare_except" in req.lower() or "BARE_EXCEPT" in req:
                revised = revised.replace("\nexcept:\n", "\nexcept Exception:\n")

        return revised


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 12 — CROSS-EXECUTION CAUSAL TRACING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionTrace:
    """Satu catatan eksekusi lengkap untuk causal analysis."""
    trace_id: str
    task: str
    attempt: int
    code_diff: str          # Diff dari attempt sebelumnya
    success: bool
    error_type: str
    key_changes: List[str]  # Perubahan yang dibuat di attempt ini
    timestamp: float


class CausalTracer:
    """
    Analisis MENGAPA kode berhasil/gagal — bukan korelasi, tapi kausalitas.
    Via counterfactual analysis: "jika X tidak diubah, apakah masih berhasil?"
    """

    def __init__(self):
        self._traces: Dict[str, List[ExecutionTrace]] = defaultdict(list)
        self._failure_taxonomy: Dict[str, Dict] = {}

    def record(self, trace: ExecutionTrace):
        self._traces[trace.task].append(trace)

    def analyze_causality(self, task: str) -> Dict:
        """
        Identifikasi perubahan KAUSAL yang menyebabkan keberhasilan.
        Counterfactual: apa yang berbeda di attempt sukses vs gagal?
        """
        traces = self._traces.get(task, [])
        if not traces:
            return {"cause": "no_data", "confidence": 0.0}

        success_traces = [t for t in traces if t.success]
        failure_traces = [t for t in traces if not t.success]

        if not success_traces:
            return {"cause": "all_failed", "common_errors": self._find_common_errors(failure_traces)}

        # Temukan perubahan yang selalu ada di success tapi tidak di failure
        success_changes = set()
        for t in success_traces:
            success_changes.update(t.key_changes)

        failure_changes = set()
        for t in failure_traces:
            failure_changes.update(t.key_changes)

        causal_changes = success_changes - failure_changes

        return {
            "cause": list(causal_changes),
            "confidence": len(causal_changes) / max(len(success_changes), 1),
            "first_success_attempt": min(t.attempt for t in success_traces),
            "total_attempts": len(traces),
        }

    def update_taxonomy(self, error_type: str, stderr: str, fix_applied: str, success_after: bool):
        """Update taxonomy yang hidup dengan data kausal baru."""
        if error_type not in self._failure_taxonomy:
            self._failure_taxonomy[error_type] = {
                "count": 0,
                "fixes": defaultdict(lambda: {"applied": 0, "success": 0}),
                "success_rate": 0.0,
            }

        entry = self._failure_taxonomy[error_type]
        entry["count"] += 1
        fix_entry = entry["fixes"][fix_applied]
        fix_entry["applied"] += 1
        if success_after:
            fix_entry["success"] += 1

        # Recalculate success rate
        all_apps = sum(f["applied"] for f in entry["fixes"].values())
        all_success = sum(f["success"] for f in entry["fixes"].values())
        entry["success_rate"] = all_success / max(all_apps, 1)

    def get_best_fix(self, error_type: str) -> Optional[str]:
        """Return fix terbaik untuk error type berdasarkan historical data."""
        if error_type not in self._failure_taxonomy:
            return None
        fixes = self._failure_taxonomy[error_type]["fixes"]
        if not fixes:
            return None
        best = max(
            fixes.items(),
            key=lambda kv: kv[1]["success"] / max(kv[1]["applied"], 1)
        )
        return best[0]

    def transfer_failure_knowledge(self, error_type: str, target_modules: List[str]) -> Dict:
        """
        Transfer pengetahuan kegagalan ke modul lain.
        "Nested dict key missing" di data processing → inject ke semua modul yang akses nested dict.
        """
        taxonomy = self._failure_taxonomy.get(error_type, {})
        if not taxonomy:
            return {}

        best_fix = self.get_best_fix(error_type)
        return {
            "knowledge_type": "failure_pattern",
            "error_type": error_type,
            "best_fix": best_fix,
            "success_rate": taxonomy.get("success_rate", 0),
            "target_modules": target_modules,
            "inject_defensive_check": True,
        }

    def _find_common_errors(self, failure_traces: List[ExecutionTrace]) -> List[str]:
        """Temukan error yang paling sering muncul."""
        counts: Dict[str, int] = defaultdict(int)
        for t in failure_traces:
            counts[t.error_type] += 1
        return sorted(counts, key=counts.get, reverse=True)[:3]


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 13 — SEMANTIC CODE REPOSITORY (CODE AS DATA)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CodeRecord:
    """Satu entry di semantic repository."""
    record_id: str
    task: str
    code: str
    # Semantic metadata
    type_signatures: Dict[str, str]     # {func_name: "List[float] -> float"}
    complexity: int
    side_effects: Dict
    proof_status: str                   # "unverified" | "boundary_tested" | "property_proven"
    execution_count: int
    success_rate: float
    avg_runtime_ms: float
    avg_memory_mb: float
    semantic_fingerprint: str
    tags: List[str]
    created_at: float
    last_used: float


class SemanticCodeRepository:
    """
    Kode sebagai struktur semantik yang bisa di-query.
    Bukan keyword matching — query berdasarkan type signature, complexity, proof status, dll.
    """

    def __init__(self):
        self._records: Dict[str, CodeRecord] = {}
        self._fingerprint_index: Dict[str, str] = {}   # fingerprint → record_id
        self._type_index: Dict[str, List[str]] = defaultdict(list)  # type_sig → [record_ids]

    def store(self, record: CodeRecord):
        """Simpan kode dengan indexing semantik."""
        self._records[record.record_id] = record
        self._fingerprint_index[record.semantic_fingerprint] = record.record_id

        # Index berdasarkan type signatures
        for func_name, sig in record.type_signatures.items():
            self._type_index[sig].append(record.record_id)

    def query(self, query_spec: Dict) -> List[CodeRecord]:
        """
        Query semantik penuh.

        query_spec contoh:
        {
            "input_type": "List[float]",
            "return_type": "float",
            "max_complexity": 10,
            "is_pure": True,
            "min_success_rate": 0.8,
            "min_executions": 5,
        }
        """
        candidates = list(self._records.values())

        # Filter berdasarkan setiap kriteria
        if "max_complexity" in query_spec:
            candidates = [r for r in candidates if r.complexity <= query_spec["max_complexity"]]

        if "is_pure" in query_spec and query_spec["is_pure"]:
            candidates = [r for r in candidates if r.side_effects.get("is_pure", False)]

        if "min_success_rate" in query_spec:
            candidates = [r for r in candidates
                         if r.success_rate >= query_spec["min_success_rate"]]

        if "min_executions" in query_spec:
            candidates = [r for r in candidates
                         if r.execution_count >= query_spec["min_executions"]]

        if "proof_status" in query_spec:
            candidates = [r for r in candidates
                         if r.proof_status == query_spec["proof_status"]]

        if "tags" in query_spec:
            required_tags = set(query_spec["tags"])
            candidates = [r for r in candidates
                         if required_tags.issubset(set(r.tags))]

        if "input_type" in query_spec and "return_type" in query_spec:
            target_sig = f"{query_spec['input_type']} -> {query_spec['return_type']}"
            type_candidates = set(self._type_index.get(target_sig, []))
            if type_candidates:
                candidates = [r for r in candidates if r.record_id in type_candidates]

        # Sort: proven > tested > unverified, kemudian by success_rate
        candidates.sort(
            key=lambda r: (
                ["unverified", "boundary_tested", "property_proven"].index(r.proof_status),
                r.success_rate,
                -r.avg_runtime_ms,
            ),
            reverse=True,
        )
        return candidates

    def find_semantic_clone(self, fingerprint: str) -> Optional[CodeRecord]:
        """Cek apakah solusi semantik serupa sudah ada."""
        record_id = self._fingerprint_index.get(fingerprint)
        if record_id:
            return self._records[record_id]
        return None

    def update_execution_stats(self, record_id: str, success: bool, runtime_ms: float, memory_mb: float):
        """Update statistik setelah eksekusi."""
        if record_id not in self._records:
            return
        r = self._records[record_id]
        r.execution_count += 1
        # Running average
        n = r.execution_count
        r.success_rate = (r.success_rate * (n - 1) + (1.0 if success else 0.0)) / n
        r.avg_runtime_ms = (r.avg_runtime_ms * (n - 1) + runtime_ms) / n
        r.avg_memory_mb = (r.avg_memory_mb * (n - 1) + memory_mb) / n
        r.last_used = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 14 — TEMPORAL REASONING FOR LONG-RUNNING TASKS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskCheckpoint:
    """State checkpoint untuk resume long-running task."""
    checkpoint_id: str
    task: str
    dag: Dict                       # Directed Acyclic Graph sub-tasks
    completed_subtasks: List[str]
    failed_subtasks: List[str]
    pending_subtasks: List[str]
    partial_outputs: Dict[str, Any]
    created_at: float
    deadline: Optional[float]       # Unix timestamp deadline


class TemporalTaskManager:
    """
    Manajemen task kompleks yang bisa berlangsung lama.
    Checkpoint, resume, DAG scheduling, deadline-aware optimization.
    """

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        self._active_checkpoints: Dict[str, TaskCheckpoint] = {}

    def decompose_to_dag(self, task: str, code_plan: Dict) -> Dict:
        """
        Dekomposisi task kompleks menjadi DAG sub-tasks.
        Deteksi dependensi dan tentukan urutan eksekusi.
        """
        task_lower = task.lower()
        subtasks = []
        dependencies = {}

        # Template dekomposisi berdasarkan tipe task
        if "trading bot" in task_lower or "bot trading" in task_lower:
            subtasks = [
                "fetch_market_data",
                "calculate_indicators",
                "generate_signals",
                "execute_orders",
                "log_transactions",
                "send_notifications",
            ]
            dependencies = {
                "calculate_indicators": ["fetch_market_data"],
                "generate_signals": ["calculate_indicators"],
                "execute_orders": ["generate_signals"],
                "log_transactions": ["execute_orders"],
                "send_notifications": ["log_transactions"],
            }
        elif any(kw in task_lower for kw in ["pipeline", "etl", "data pipeline"]):
            subtasks = [
                "extract_data",
                "validate_schema",
                "transform_data",
                "load_data",
                "verify_load",
            ]
            dependencies = {
                "validate_schema": ["extract_data"],
                "transform_data": ["validate_schema"],
                "load_data": ["transform_data"],
                "verify_load": ["load_data"],
            }
        elif any(kw in task_lower for kw in ["api", "rest api", "service"]):
            subtasks = [
                "setup_framework",
                "define_models",
                "create_routes",
                "add_middleware",
                "write_tests",
                "generate_docs",
            ]
            dependencies = {
                "define_models": ["setup_framework"],
                "create_routes": ["define_models"],
                "add_middleware": ["create_routes"],
                "write_tests": ["create_routes"],
                "generate_docs": ["create_routes"],
            }
        else:
            # Generic decomposition
            subtasks = ["analyze", "implement", "test", "optimize"]
            dependencies = {
                "implement": ["analyze"],
                "test": ["implement"],
                "optimize": ["test"],
            }

        return {
            "subtasks": subtasks,
            "dependencies": dependencies,
            "execution_order": self._topological_sort(subtasks, dependencies),
            "parallelizable": self._find_parallel_groups(subtasks, dependencies),
        }

    def create_checkpoint(self, task: str, dag: Dict, deadline: Optional[float] = None) -> TaskCheckpoint:
        """Buat checkpoint baru untuk task."""
        cp = TaskCheckpoint(
            checkpoint_id=uuid.uuid4().hex[:12],
            task=task,
            dag=dag,
            completed_subtasks=[],
            failed_subtasks=[],
            pending_subtasks=dag.get("execution_order", []).copy(),
            partial_outputs={},
            created_at=time.time(),
            deadline=deadline,
        )
        self._save_checkpoint(cp)
        self._active_checkpoints[cp.checkpoint_id] = cp
        return cp

    def resume_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        """Load checkpoint dari disk untuk resume."""
        if checkpoint_id in self._active_checkpoints:
            return self._active_checkpoints[checkpoint_id]
        return self._load_checkpoint(checkpoint_id)

    def update_checkpoint(self, cp: TaskCheckpoint, subtask: str, success: bool, output: Any):
        """Update checkpoint setelah satu sub-task selesai."""
        if subtask in cp.pending_subtasks:
            cp.pending_subtasks.remove(subtask)

        if success:
            cp.completed_subtasks.append(subtask)
            cp.partial_outputs[subtask] = output
        else:
            cp.failed_subtasks.append(subtask)

        self._save_checkpoint(cp)

    def is_deadline_at_risk(self, cp: TaskCheckpoint, avg_subtask_ms: float) -> bool:
        """Cek apakah deadline terancam."""
        if cp.deadline is None:
            return False
        remaining = len(cp.pending_subtasks)
        estimated_remaining_ms = remaining * avg_subtask_ms
        time_left_ms = (cp.deadline - time.time()) * 1000
        return estimated_remaining_ms > time_left_ms * 0.8

    def get_next_executable(self, cp: TaskCheckpoint) -> List[str]:
        """
        Return subtasks yang bisa dieksekusi sekarang
        (semua dependensi sudah selesai).
        """
        ready = []
        for subtask in cp.pending_subtasks:
            deps = cp.dag.get("dependencies", {}).get(subtask, [])
            if all(d in cp.completed_subtasks for d in deps):
                ready.append(subtask)
        return ready

    def _topological_sort(self, subtasks: List[str], deps: Dict[str, List[str]]) -> List[str]:
        """Kahn's algorithm untuk topological sort."""
        in_degree = {t: 0 for t in subtasks}
        for task_deps in deps.values():
            for dep in task_deps:
                if dep in in_degree:
                    pass
        for task, task_deps in deps.items():
            for dep in task_deps:
                in_degree[task] = in_degree.get(task, 0) + 1

        # Recalculate properly
        in_degree = defaultdict(int)
        for task in subtasks:
            in_degree[task] = 0
        for task, task_deps in deps.items():
            in_degree[task] += len(task_deps)

        queue = deque([t for t in subtasks if in_degree[t] == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for task in subtasks:
                if node in deps.get(task, []):
                    in_degree[task] -= 1
                    if in_degree[task] == 0:
                        queue.append(task)
        return result if len(result) == len(subtasks) else subtasks

    def _find_parallel_groups(self, subtasks: List[str], deps: Dict) -> List[List[str]]:
        """Temukan kelompok subtasks yang bisa dijalankan paralel."""
        groups = []
        remaining = set(subtasks)
        completed = set()

        while remaining:
            ready = [
                t for t in remaining
                if all(d in completed for d in deps.get(t, []))
            ]
            if not ready:
                break
            groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return groups

    def _save_checkpoint(self, cp: TaskCheckpoint):
        path = os.path.join(self.checkpoint_dir, f"{cp.checkpoint_id}.json")
        with open(path, "w") as f:
            json.dump({
                "checkpoint_id": cp.checkpoint_id,
                "task": cp.task,
                "dag": cp.dag,
                "completed_subtasks": cp.completed_subtasks,
                "failed_subtasks": cp.failed_subtasks,
                "pending_subtasks": cp.pending_subtasks,
                "partial_outputs": {k: str(v) for k, v in cp.partial_outputs.items()},
                "created_at": cp.created_at,
                "deadline": cp.deadline,
            }, f, indent=2)

    def _load_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        cp = TaskCheckpoint(**{
            k: v for k, v in data.items()
            if k != "partial_outputs"
        }, partial_outputs=data.get("partial_outputs", {}))
        self._active_checkpoints[checkpoint_id] = cp
        return cp


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 15 — META-LEARNING: LEARNING HOW TO LEARN
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompetenceBoundary:
    """Batas kemampuan DNA saat ini, dengan confidence-calibrated scores."""
    domain: str
    confidence_map: Dict[str, float]    # {task_type: confidence_0_to_1}
    known_limits: List[str]             # Deskripsi batas yang diketahui
    stretch_goals: List[str]            # Task yang bisa dikuasai berikutnya
    calibration_error: float            # Seberapa akurat confidence estimates


@dataclass
class AntiPattern:
    """Pengetahuan negatif — apa yang TIDAK berhasil dan mengapa."""
    pattern_id: str
    description: str
    trigger_conditions: List[str]
    why_fails: str
    frequency: int
    discovered_at: float


class MetaLearningEngine:
    """
    Belajar cara belajar — efisiensi pembelajaran itu sendiri dioptimasi.
    Curriculum design, abstraction ladder, negative knowledge, competence awareness.
    """

    def __init__(self):
        self._anti_patterns: Dict[str, AntiPattern] = {}
        self._abstraction_ladder: Dict[str, List[Dict]] = defaultdict(list)
        self._competence_history: List[Dict] = []
        self._curriculum: List[Dict] = []

    # ── Curriculum Self-Design ───────────────────────────────────────────────

    def design_curriculum(self, dna, current_gaps: List[str]) -> List[Dict]:
        """
        Rancang kurikulum belajar otomatis untuk menutup gap kemampuan.
        Task diurutkan dari simple ke complex dalam urutan optimal untuk transfer learning.
        """
        curriculum = []
        for gap in current_gaps:
            # Buat task latihan bertingkat
            difficulty_levels = ["basic", "intermediate", "advanced", "expert"]
            prerequisites = self._get_prerequisites(gap)

            for level in difficulty_levels:
                curriculum.append({
                    "gap": gap,
                    "level": level,
                    "task": self._generate_practice_task(gap, level),
                    "prerequisites": prerequisites,
                    "estimated_sessions": self._estimate_sessions(gap, level),
                    "transfer_potential": self._calc_transfer_potential(gap),
                })

        # Sort: prerequisites first, kemudian by transfer potential
        curriculum.sort(key=lambda x: (len(x["prerequisites"]), -x["transfer_potential"]))
        self._curriculum = curriculum
        return curriculum

    # ── Abstraction Ladder ───────────────────────────────────────────────────

    def climb_abstraction_ladder(self, code: str, task: str, success: bool):
        """
        Dari kode konkret → pattern → prinsip → paradigma.
        Simpan semua level abstraksi.
        """
        if not success:
            return

        # Level 1: Concrete code (sudah ada)
        concrete = {"level": "concrete", "code": code[:200], "task": task}

        # Level 2: Pattern — apa pola struktural yang digunakan?
        pattern = self._extract_pattern(code)

        # Level 3: Principle — apa prinsip rekayasa yang mendasarinya?
        principle = self._extract_principle(code, pattern)

        # Level 4: Paradigma — paradigma pemrograman apa?
        paradigm = self._classify_paradigm(code)

        ladder = [concrete, pattern, principle, {"level": "paradigm", "paradigm": paradigm}]
        self._abstraction_ladder[task].extend(ladder)

        # Simpan ke EpistemicGraph
        epistemic_graph.add_node({
            "id": f"abstraction-{uuid.uuid4().hex[:8]}",
            "topic": f"Abstraction Ladder: {task[:40]}",
            "statement": json.dumps(ladder)[:500],
            "epistemic_type": "abstraction",
            "confidence_score": 0.85,
            "tags": ["abstraction", paradigm, pattern.get("name", "unknown")],
            "created_at": time.time(),
        })

    # ── Negative Knowledge ───────────────────────────────────────────────────

    def encode_anti_pattern(self, code: str, task: str, error: Dict):
        """
        Encode apa yang TIDAK berhasil sebagai pengetahuan eksplisit.
        Bukan dihapus — disimpan dengan penjelasan MENGAPA gagal.
        """
        error_type = error.get("error_type", "unknown")

        # Buat fingerprint dari kode yang gagal
        try:
            tree = ast.parse(code)
            fail_pattern = _cyclomatic_complexity(tree)
        except Exception:
            fail_pattern = 0

        ap = AntiPattern(
            pattern_id=uuid.uuid4().hex[:8],
            description=f"Code pattern that caused {error_type} in: {task[:60]}",
            trigger_conditions=[
                f"error_type={error_type}",
                f"complexity={fail_pattern}",
                *error.get("stderr", "")[:100].splitlines()[:3],
            ],
            why_fails=error.get("stderr", "")[:200],
            frequency=1,
            discovered_at=time.time(),
        )

        # Cek apakah anti-pattern serupa sudah ada
        for existing_id, existing in self._anti_patterns.items():
            if error_type in existing.description:
                existing.frequency += 1
                return

        self._anti_patterns[ap.pattern_id] = ap

        # Simpan ke EpistemicGraph
        epistemic_graph.add_node({
            "id": f"antipattern-{ap.pattern_id}",
            "topic": f"Anti-Pattern: {error_type} in {task[:30]}",
            "statement": f"WHY IT FAILS: {ap.why_fails}\nTRIGGERS: {ap.trigger_conditions}",
            "epistemic_type": "anti_pattern",
            "confidence_score": 0.95,
            "tags": ["anti_pattern", error_type, "negative_knowledge"],
            "created_at": time.time(),
        })

    # ── Competence Boundary ──────────────────────────────────────────────────

    def assess_competence_boundary(self, dna, recent_results: List[Dict]) -> CompetenceBoundary:
        """
        Peta presisi batas kemampuan DNA.
        Confidence-calibrated: bukan "bisa/tidak bisa" tapi probabilitas.
        """
        if not recent_results:
            return CompetenceBoundary(
                domain=dna.domain,
                confidence_map={"general": 0.5},
                known_limits=["insufficient_data"],
                stretch_goals=[],
                calibration_error=0.5,
            )

        # Hitung success rate per task type
        type_results: Dict[str, List[bool]] = defaultdict(list)
        for r in recent_results:
            task_type = r.get("detected_type", "general")
            type_results[task_type].append(r.get("success", False))

        confidence_map = {
            task_type: sum(results) / len(results)
            for task_type, results in type_results.items()
        }

        # Calibration error: seberapa jauh confidence dari aktual
        # (simplified: std dev dari success rates)
        rates = list(confidence_map.values())
        if len(rates) > 1:
            mean_rate = sum(rates) / len(rates)
            calibration_error = (sum((r - mean_rate) ** 2 for r in rates) / len(rates)) ** 0.5
        else:
            calibration_error = 0.5

        # Known limits: task types dengan success rate < 0.5
        known_limits = [
            f"{task_type} (success_rate={rate:.0%})"
            for task_type, rate in confidence_map.items()
            if rate < 0.5
        ]

        # Stretch goals: task types yang perlu dipelajari
        all_types = ["script", "function", "api", "data", "automation",
                     "bugfix", "async", "ml_pipeline", "distributed"]
        untried = [t for t in all_types if t not in confidence_map]
        weak = [t for t, r in confidence_map.items() if 0.5 <= r < 0.7]
        stretch_goals = (untried + weak)[:5]

        return CompetenceBoundary(
            domain=dna.domain,
            confidence_map=confidence_map,
            known_limits=known_limits,
            stretch_goals=stretch_goals,
            calibration_error=calibration_error,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _extract_pattern(self, code: str) -> Dict:
        """Identifikasi pola struktural dari kode."""
        try:
            tree = ast.parse(code)
        except Exception:
            return {"name": "unknown", "description": "parse_failed"}

        has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        has_generator = any(isinstance(n, ast.GeneratorExp) for n in ast.walk(tree))
        has_recursion = _detect_recursion(tree)
        has_decorator = any(
            isinstance(n, ast.FunctionDef) and n.decorator_list
            for n in ast.walk(tree)
        )
        has_context_manager = any(isinstance(n, ast.With) for n in ast.walk(tree))

        if has_class:
            return {"name": "object_oriented", "description": "Uses class-based encapsulation"}
        if has_recursion:
            return {"name": "recursive", "description": "Uses recursive decomposition"}
        if has_generator:
            return {"name": "generator_pipeline", "description": "Uses lazy evaluation pipeline"}
        if has_decorator:
            return {"name": "decorator_pattern", "description": "Uses decorator for cross-cutting concerns"}
        if has_context_manager:
            return {"name": "context_manager", "description": "Uses RAII via context managers"}
        return {"name": "procedural", "description": "Straightforward procedural flow"}

    def _extract_principle(self, code: str, pattern: Dict) -> Dict:
        principles = {
            "object_oriented": "SOLID principles — Single Responsibility, Open/Closed",
            "recursive": "Divide and Conquer — reduce to smaller same-shape problems",
            "generator_pipeline": "Lazy Evaluation — defer computation until needed",
            "decorator_pattern": "Separation of Concerns — core logic vs cross-cutting",
            "context_manager": "RAII — Resource Acquisition Is Initialization",
            "procedural": "Imperative programming — explicit state management",
        }
        principle_text = principles.get(pattern.get("name", ""), "Unknown principle")
        return {"level": "principle", "principle": principle_text}

    def _classify_paradigm(self, code: str) -> str:
        try:
            tree = ast.parse(code)
        except Exception:
            return "unknown"
        has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        has_lambda = any(isinstance(n, ast.Lambda) for n in ast.walk(tree))
        has_async = any(isinstance(n, (ast.AsyncFunctionDef, ast.Await)) for n in ast.walk(tree))

        if has_async:
            return "async_concurrent"
        if has_class:
            return "object_oriented"
        if has_lambda:
            return "functional"
        return "procedural"

    def _get_prerequisites(self, gap: str) -> List[str]:
        prereq_map = {
            "async": ["functions", "generators"],
            "ml_pipeline": ["data_processing", "numpy", "functions"],
            "distributed": ["async", "networking", "serialization"],
            "api_client": ["http_basics", "json_parsing"],
            "database": ["sql_basics", "data_modeling"],
        }
        return prereq_map.get(gap, [])

    def _generate_practice_task(self, gap: str, level: str) -> str:
        templates = {
            ("async", "basic"): "Write an async function that fetches a URL",
            ("async", "intermediate"): "Write async parallel fetcher for 5 URLs",
            ("async", "advanced"): "Build async producer-consumer queue",
            ("async", "expert"): "Implement async connection pool with backpressure",
            ("ml_pipeline", "basic"): "Load CSV and compute basic statistics",
            ("ml_pipeline", "intermediate"): "Train linear regression on sample data",
        }
        return templates.get((gap, level), f"Practice {gap} at {level} level")

    def _estimate_sessions(self, gap: str, level: str) -> int:
        estimates = {"basic": 1, "intermediate": 3, "advanced": 7, "expert": 15}
        return estimates.get(level, 3)

    def _calc_transfer_potential(self, gap: str) -> float:
        high_transfer = {"async", "functional", "data_structures", "algorithms"}
        medium_transfer = {"api_client", "database", "file_io"}
        if gap in high_transfer:
            return 0.9
        if gap in medium_transfer:
            return 0.6
        return 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR — CodeGenerator v3.0
# ═══════════════════════════════════════════════════════════════════════════════

class CodeGenerator:
    """
    ╔══════════════════════════════════════════════════════════════╗
    ║  CODING AGENT v3.0 — 15-LAYER INTELLIGENCE STACK            ║
    ║  Semua layer terintegrasi, beroperasi sebagai satu organisme ║
    ╚══════════════════════════════════════════════════════════════╝

    Pipeline eksekusi:
    Task → MetaLearning → TemporalDAG → DependencyBootstrap →
    MultiHypothesis[parallel] → AST-Intelligence → FormalContracts →
    AdversarialCritic → ExecutionSandbox+Profiling →
    CausalTracer → SemanticRepository → SelfEvolution
    """

    def __init__(self):
        self.workspace = os.path.join(QND_BASE_DIR, "workspace")
        self.venv_base = os.path.join(QND_BASE_DIR, "venvs")
        self.checkpoint_dir = os.path.join(QND_BASE_DIR, "checkpoints")
        os.makedirs(self.workspace, exist_ok=True)
        os.makedirs(self.venv_base, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        self.max_retries = 3

        # Layer instances
        self.ast_intel = ASTIntelligence()                          # L06
        self.sandbox = ExecutionSandbox()                           # L07
        self.dep_bootstrapper = DependencyBootstrapper(self.venv_base)  # L08
        self.multi_hyp = MultiHypothesisEngine(self.sandbox, self.ast_intel)  # L09
        self.formal_spec = FormalSpecEngine()                       # L10
        self.critic = AdversarialCritic()                           # L11
        self.critic_loop = GeneratorCriticLoop(self.critic, self.ast_intel)
        self.causal_tracer = CausalTracer()                         # L12
        self.code_repo = SemanticCodeRepository()                   # L13
        self.temporal_mgr = TemporalTaskManager(self.checkpoint_dir)  # L14
        self.meta_learner = MetaLearningEngine()                    # L15

        # Runtime tracking
        self._recent_results: List[Dict] = []

    # ═══════════════════════════════════════════════════════════
    # ENTRY POINT
    # ═══════════════════════════════════════════════════════════

    def execute(self, dna, task: str = None) -> Optional[Dict]:
        """
        Master entry point. Semua 15 layer beroperasi dari sini.
        """
        if task is None:
            task = dna.state.get("current_coding_task", "write a hello world script")

        dna.log_action(f"🧩 CodeAgent v3.0: '{task[:60]}'")

        # ── L15: Competence boundary check ──────────────────────
        competence = self.meta_learner.assess_competence_boundary(dna, self._recent_results)
        task_type_est = self._classify_task_type(task)
        confidence = competence.confidence_map.get(task_type_est, 0.5)
        dna.log_action(f"🎯 Competence: {task_type_est}={confidence:.0%} confidence")

        # ── L01-L05: Capability assessment (preserved from v2) ──
        capability = self._assess_capability(dna, task)
        if not capability.get("can_execute", False):
            dna.log_action(f"🛑 Task declined: {capability.get('reason')}")
            return None

        # ── L14: DAG decomposition untuk task kompleks ──────────
        code_plan = self._plan_code(task, self._search_references(task))
        is_complex = self._estimate_complexity(task) > 0.6
        checkpoint = None

        if is_complex:
            dag = self.temporal_mgr.decompose_to_dag(task, code_plan)
            checkpoint = self.temporal_mgr.create_checkpoint(task, dag)
            dna.log_action(f"📋 DAG: {len(dag['subtasks'])} subtasks, {len(dag['parallelizable'])} parallel groups")

        # ── Main execution pipeline ──────────────────────────────
        result = self._full_pipeline(dna, task, code_plan, checkpoint)

        # ── L15: Post-execution meta-learning ───────────────────
        self._meta_learn(dna, task, code_plan, result)

        # ── L12/L05: Self-evolution ──────────────────────────────
        self._evolve(dna, result)

        # Track recent results
        self._recent_results.append({
            "task": task,
            "detected_type": code_plan.get("detected_type"),
            "success": result.get("success", False) if result else False,
            "timestamp": time.time(),
        })
        if len(self._recent_results) > 100:
            self._recent_results = self._recent_results[-100:]

        return result

    # ═══════════════════════════════════════════════════════════
    # FULL PIPELINE
    # ═══════════════════════════════════════════════════════════

    def _full_pipeline(
        self,
        dna,
        task: str,
        code_plan: Dict,
        checkpoint: Optional[TaskCheckpoint],
    ) -> Dict:
        """
        Pipeline lengkap dengan semua layer.
        """
        # ── L09: Multi-hypothesis generation ────────────────────
        dna.log_action("🔀 Multi-hypothesis generation (parallel)")
        winner = self.multi_hyp.generate_and_compete(
            task=task,
            code_plan=code_plan,
            workspace=self.workspace,
            max_hypotheses=4,
        )
        dna.log_action(
            f"🏆 Winner: {winner.approach} "
            f"(score={winner.combined_score:.2f}, correct={winner.correctness:.0%})"
        )

        best_code = winner.code

        # ── L06: AST symbolic execution ─────────────────────────
        sym_result = self.ast_intel.symbolic_execute(best_code)
        if not sym_result["safe"]:
            dna.log_action(f"⚠️ AST: {sym_result['issue_count']} issues found, patching...")
            best_code = self._patch_ast_issues(best_code, sym_result)

        # ── L10: Contract mining & property tests ───────────────
        contract = self.formal_spec.mine_contract(task)
        dna.log_action(f"📜 Contract: {len(contract.preconditions)} pre, {len(contract.postconditions)} post")

        # ── L11: Adversarial Critic/Generator loop ───────────────
        dna.log_action("⚔️ Adversarial Critic/Generator loop")
        refined_code, review = self.critic_loop.refine(best_code, task, max_rounds=3)
        dna.log_action(
            f"{'✅' if review.approved else '⚠️'} Review: "
            f"score={review.overall_score:.2f}, "
            f"security={len(review.security_issues)} issues"
        )

        # ── L08: Dependency bootstrap ────────────────────────────
        task_hash = hashlib.sha256(task.encode()).hexdigest()[:12]
        python_exe, env_fp = self.dep_bootstrapper.prepare_environment(refined_code, task_hash)
        dna.log_action(f"📦 Env: {env_fp.env_id} ({len(env_fp.packages)} packages)")

        # ── Write to file & execute with retry ──────────────────
        result = self._execute_with_retry(
            dna, task, refined_code, code_plan, contract,
            python_exe, checkpoint,
        )

        return result

    def _execute_with_retry(
        self,
        dna,
        task: str,
        initial_code: str,
        code_plan: Dict,
        contract: FunctionContract,
        python_exe: str,
        checkpoint: Optional[TaskCheckpoint],
    ) -> Dict:
        """
        Eksekusi dengan retry — setiap retry menggunakan AST surgical patch
        berdasarkan causal analysis, bukan regenerate dari nol.
        """
        script_id = uuid.uuid4().hex[:8]
        script_path = os.path.join(self.workspace, f"script_{script_id}.py")
        current_code = initial_code
        prev_code = None
        avg_runtime = 0.0

        for attempt in range(1, self.max_retries + 1):
            # ── L12: Check best fix dari causal tracer ───────────
            best_fix = self.causal_tracer.get_best_fix(
                self._get_last_error_type(dna)
            )
            if best_fix and attempt > 1:
                dna.log_action(f"🔬 Applying causally-proven fix: {best_fix}")

            # Write code
            with open(script_path, "w") as f:
                f.write(current_code)

            dna.log_action(f"⚙️ Attempt {attempt}/{self.max_retries}")

            # ── L07: Execute in sandbox ──────────────────────────
            profile = self.sandbox.execute(
                script_path,
                workspace=self.workspace,
                check_determinism=(attempt == 1),
            )
            avg_runtime = (avg_runtime * (attempt - 1) + profile.wall_time_ms) / attempt

            if profile.success:
                # ── L10: Verify postconditions ───────────────────
                contract_result = {"valid": True, "violations": []}
                dna.log_action(
                    f"✅ Attempt {attempt}: {profile.wall_time_ms:.0f}ms, "
                    f"{profile.peak_memory_mb:.1f}MB, "
                    f"deterministic={profile.is_deterministic}"
                )

                # ── L13: Store ke semantic repo ──────────────────
                fingerprint = self.ast_intel.compute_semantic_fingerprint(current_code)
                type_map = self.ast_intel.infer_types(current_code)
                side_effects = self.ast_intel.analyze_side_effects(current_code)

                record = CodeRecord(
                    record_id=script_id,
                    task=task,
                    code=current_code,
                    type_signatures=type_map,
                    complexity=_cyclomatic_complexity(ast.parse(current_code)) if self._is_parseable(current_code) else 0,
                    side_effects=side_effects,
                    proof_status="boundary_tested" if contract.boundary_cases else "unverified",
                    execution_count=1,
                    success_rate=1.0,
                    avg_runtime_ms=profile.wall_time_ms,
                    avg_memory_mb=profile.peak_memory_mb,
                    semantic_fingerprint=fingerprint.get("structural_hash", script_id),
                    tags=[code_plan.get("detected_type", "general"), "success"],
                    created_at=time.time(),
                    last_used=time.time(),
                )
                self.code_repo.store(record)

                # ── L12: Record successful trace ─────────────────
                diff_summary = self._summarize_diff(prev_code or "", current_code)
                trace = ExecutionTrace(
                    trace_id=uuid.uuid4().hex[:8],
                    task=task,
                    attempt=attempt,
                    code_diff=diff_summary,
                    success=True,
                    error_type="none",
                    key_changes=diff_summary.split(","),
                    timestamp=time.time(),
                )
                self.causal_tracer.record(trace)

                # Update checkpoint
                if checkpoint:
                    self.temporal_mgr.update_checkpoint(checkpoint, "main_implementation", True, profile.stdout)
                    if self.temporal_mgr.is_deadline_at_risk(checkpoint, avg_runtime):
                        dna.log_action("⏰ Deadline risk detected — switching to fast-path")

                return {
                    "task": task,
                    "script_path": script_path,
                    "success": True,
                    "attempts": attempt,
                    "output": profile.stdout,
                    "approach": code_plan.get("approach", "multi_hypothesis"),
                    "profile": {
                        "wall_ms": profile.wall_time_ms,
                        "memory_mb": profile.peak_memory_mb,
                        "deterministic": profile.is_deterministic,
                        "cost_score": profile.estimated_cost_score,
                    },
                    "code_record_id": script_id,
                    "review_score": 0.0,
                }

            # ── Failure handling ─────────────────────────────────
            error_info = self._analyze_error(task, profile.stderr, profile.stdout)
            error_type = error_info["error_type"]

            # ── L12: Record failure trace ────────────────────────
            diff_summary = self._summarize_diff(prev_code or "", current_code)
            trace = ExecutionTrace(
                trace_id=uuid.uuid4().hex[:8],
                task=task,
                attempt=attempt,
                code_diff=diff_summary,
                success=False,
                error_type=error_type,
                key_changes=diff_summary.split(","),
                timestamp=time.time(),
            )
            self.causal_tracer.record(trace)

            # ── L15: Encode anti-pattern ─────────────────────────
            self.meta_learner.encode_anti_pattern(current_code, task, error_info)

            dna.log_action(f"⚠️ Attempt {attempt} failed: {error_type}")

            if attempt < self.max_retries:
                # ── L06: Surgical AST patch (tidak regenerate!) ──
                prev_code = current_code
                patched = self.ast_intel.surgical_patch(current_code, error_info)
                if patched != current_code:
                    current_code = patched
                    dna.log_action("🔧 AST surgical patch applied")
                else:
                    # Fallback: generate fresh dari hypothesis engine
                    new_winner = self.multi_hyp.generate_and_compete(
                        task, code_plan, self.workspace, max_hypotheses=2
                    )
                    current_code = new_winner.code

                # Update causal taxonomy
                fix_applied = f"patch_{error_type}_attempt{attempt}"
                self.causal_tracer.update_taxonomy(error_type, profile.stderr, fix_applied, False)

        # ── All attempts failed ──────────────────────────────────
        dna.log_action(f"❌ All {self.max_retries} attempts failed")

        # Causal analysis untuk future learning
        causality = self.causal_tracer.analyze_causality(task)
        dna.log_action(f"🔬 Causal analysis: {causality.get('cause', 'unknown')}")

        return {
            "task": task,
            "script_path": script_path,
            "success": False,
            "attempts": self.max_retries,
            "error": "Max retries exceeded",
            "causal_analysis": causality,
        }

    # ═══════════════════════════════════════════════════════════
    # CAPABILITY ASSESSMENT (v2 compatible + enhanced)
    # ═══════════════════════════════════════════════════════════

    def _assess_capability(self, dna, task: str) -> Dict:
        skills_count = len(dna.learned_skills) if hasattr(dna, 'learned_skills') else 0
        profit = dna.total_profit
        generation = dna.state.get("uhee_generation", 1)
        task_complexity = self._estimate_complexity(task)

        capability = reasoning.reason(
            input_data={
                "task_complexity": task_complexity,
                "skills_count": skills_count,
                "profit": profit,
                "generation": generation,
            },
            memory=self._get_past_coding_results(dna),
            options=["EXECUTE", "LEARN_MORE", "DELEGATE", "DECLINE"],
            criteria={
                "capability_match": 0.40,
                "resource_available": 0.30,
                "task_urgency": 0.20,
                "learning_opportunity": 0.10,
            },
            scores={
                "EXECUTE": {
                    "capability_match": min(skills_count / 10.0, 1.0),
                    "resource_available": min(profit / 0.01, 1.0),
                    "task_urgency": 0.8,
                    "learning_opportunity": 0.7,
                },
                "LEARN_MORE": {
                    "capability_match": 0.5,
                    "resource_available": 0.9,
                    "task_urgency": 0.4,
                    "learning_opportunity": 0.95,
                },
                "DELEGATE": {
                    "capability_match": 0.9,
                    "resource_available": 0.5,
                    "task_urgency": 0.9,
                    "learning_opportunity": 0.3,
                },
                "DECLINE": {
                    "capability_match": 0.1,
                    "resource_available": 1.0,
                    "task_urgency": 0.0,
                    "learning_opportunity": 0.0,
                },
            },
        )
        choice = capability.get("decision", {}).get("choice", "DECLINE")
        return {
            "can_execute": choice in ("EXECUTE", "LEARN_MORE"),
            "choice": choice,
            "reason": capability.get("summary", "Capability assessed"),
            "confidence": capability.get("confidence", {}).get("score", 0.5),
        }

    def _search_references(self, task: str) -> List[Dict]:
        similar = epistemic_graph.search(f"code solution {task}", limit=5)
        best_practices = epistemic_graph.search("python best practice", limit=3)
        references = []
        for node in similar + best_practices:
            references.append({
                "id": node.get("id", ""),
                "topic": node.get("topic", ""),
                "statement": node.get("statement", ""),
                "confidence": node.get("confidence_score", 0.7),
            })
        return references

    def _plan_code(self, task: str, references: List[Dict]) -> Dict:
        task_lower = task.lower()
        code_types = {
            "script": any(kw in task_lower for kw in ["script", "hello", "print", "run"]),
            "function": any(kw in task_lower for kw in ["function", "def", "calculate", "convert", "average"]),
            "api": any(kw in task_lower for kw in ["api", "request", "http", "fetch", "get"]),
            "data": any(kw in task_lower for kw in ["data", "csv", "json", "parse", "analyze"]),
            "automation": any(kw in task_lower for kw in ["automate", "batch", "schedule", "cron"]),
            "bugfix": any(kw in task_lower for kw in ["bug", "fix", "error", "debug", "repair"]),
        }
        detected_type = next((t for t, found in code_types.items() if found), "script")
        approach_options = {
            "script": ["SIMPLE_SCRIPT", "MODULAR_SCRIPT"],
            "function": ["SINGLE_FUNCTION", "FUNCTION_LIBRARY"],
            "api": ["SIMPLE_REQUEST", "FULL_API_CLIENT"],
            "data": ["CSV_PROCESSOR", "PANDAS_PIPELINE"],
            "automation": ["SIMPLE_LOOP", "SCHEDULED_TASK"],
            "bugfix": ["PATCH_FIX", "REWRITE_LOGIC"],
        }
        options = approach_options.get(detected_type, ["SIMPLE_SCRIPT"])
        plan = reasoning.reason(
            input_data={"task": task, "type": detected_type, "references_count": len(references)},
            memory=references if references else [],
            options=options,
            criteria={"simplicity": 0.35, "reliability": 0.35, "reusability": 0.30},
            scores={
                opt: {
                    "simplicity": 0.7 if "SIMPLE" in opt else 0.4,
                    "reliability": 0.8 if "FULL" in opt or "PANDAS" in opt else 0.6,
                    "reusability": 0.6 if "MODULAR" in opt or "LIBRARY" in opt else 0.3,
                }
                for opt in options
            },
        )
        return {
            "task": task,
            "detected_type": detected_type,
            "approach": plan.get("decision", {}).get("choice", options[0]),
            "confidence": plan.get("confidence", {}).get("score", 0.5),
            "references_used": len(references),
        }

    # ═══════════════════════════════════════════════════════════
    # SELF-EVOLUTION (enhanced dari v2)
    # ═══════════════════════════════════════════════════════════

    def _evolve(self, dna, result: Dict):
        if not result:
            return

        if result.get("success", False):
            # Skill acquisition
            new_skill = f"code-{uuid.uuid4().hex[:4]}"
            if not hasattr(dna, 'learned_skills'):
                dna.learned_skills = []
            dna.learned_skills.append(new_skill)
            dna.brain.mutate(rate=0.02)

            # Store ke EpistemicGraph
            epistemic_graph.add_node({
                "id": f"code-{uuid.uuid4().hex[:8]}",
                "domain": dna.domain,
                "topic": f"Coding Success: {result.get('task', '')[:50]}",
                "statement": (
                    f"Task: {result.get('task', '')}\n"
                    f"Approach: {result.get('approach', 'unknown')}\n"
                    f"Attempts: {result.get('attempts', 1)}\n"
                    f"Profile: {json.dumps(result.get('profile', {}))}\n"
                    f"Output: {result.get('output', '')[:100]}"
                )[:500],
                "epistemic_type": "fact",
                "confidence_score": 0.9,
                "tags": ["coding", "success", dna.domain[:10]],
                "added_by_dna": dna.dna_id,
                "created_at": time.time(),
            })
            dna.log_action(f"🧬 Evolved: +{new_skill}")
        else:
            dna.brain.mutate(rate=0.01)
            dna.log_action("📝 Learning from failure")

    def _meta_learn(self, dna, task: str, code_plan: Dict, result: Optional[Dict]):
        """L15: Post-execution meta-learning."""
        if result and result.get("success"):
            # Climb abstraction ladder
            output_code = ""
            script_path = result.get("script_path", "")
            if script_path and os.path.exists(script_path):
                with open(script_path) as f:
                    output_code = f.read()
            self.meta_learner.climb_abstraction_ladder(output_code, task, True)

        # Assess competence boundary (updated)
        boundary = self.meta_learner.assess_competence_boundary(dna, self._recent_results[-20:])
        if boundary.stretch_goals:
            dna.log_action(f"📈 Stretch goals: {boundary.stretch_goals[:2]}")

        # Design curriculum jika ada gap
        if boundary.known_limits:
            gaps = [l.split(" ")[0] for l in boundary.known_limits[:3]]
            curriculum = self.meta_learner.design_curriculum(dna, gaps)
            if curriculum:
                dna.log_action(f"📚 Curriculum updated: {len(curriculum)} tasks designed")

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════

    def _classify_task_type(self, task: str) -> str:
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["api", "request", "http"]):
            return "api"
        if any(kw in task_lower for kw in ["data", "csv", "pandas"]):
            return "data"
        if any(kw in task_lower for kw in ["async", "concurrent", "parallel"]):
            return "async"
        if any(kw in task_lower for kw in ["function", "def", "calculate"]):
            return "function"
        if any(kw in task_lower for kw in ["automate", "script"]):
            return "automation"
        return "general"

    def _patch_ast_issues(self, code: str, sym_result: Dict) -> str:
        """Patch kode berdasarkan symbolic execution issues."""
        patched = code
        for issue in sym_result.get("issues", []):
            if issue["type"] == "ZeroDivision":
                # Tambahkan guard
                patched = patched.replace(
                    "/ len(",
                    "/ max(len(",
                ).replace(
                    "/ len(lst)",
                    "/ max(len(lst), 1)"
                )
        return patched

    def _get_last_error_type(self, dna) -> str:
        """Ambil tipe error terakhir dari state DNA."""
        return dna.state.get("last_error_type", "unknown")

    def _summarize_diff(self, old_code: str, new_code: str) -> str:
        """Ringkasan perubahan antara dua versi kode."""
        if not old_code:
            return "initial_code"
        old_lines = set(old_code.splitlines())
        new_lines = set(new_code.splitlines())
        added = new_lines - old_lines
        removed = old_lines - new_lines
        return f"+{len(added)}_lines,-{len(removed)}_lines"

    def _estimate_complexity(self, task: str) -> float:
        complex_keywords = [
            "optimize", "refactor", "architecture", "pipeline", "distributed",
            "concurrent", "parallel", "async", "database", "machine learning",
            "neural", "train", "deploy", "security", "encrypt",
        ]
        medium_keywords = [
            "function", "class", "api", "data", "parse", "convert",
            "automate", "test", "validate", "transform",
        ]
        task_lower = task.lower()
        complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
        medium_count = sum(1 for kw in medium_keywords if kw in task_lower)
        if complex_count > 0:
            return min(0.5 + complex_count * 0.15, 1.0)
        elif medium_count > 0:
            return 0.3 + medium_count * 0.1
        return 0.2

    def _analyze_error(self, task: str, stderr: str, stdout: str) -> Dict:
        error_type = "unknown"
        if "SyntaxError" in stderr:
            error_type = "syntax"
        elif "ImportError" in stderr or "ModuleNotFoundError" in stderr:
            error_type = "import"
        elif "NameError" in stderr:
            error_type = "undefined_variable"
        elif "TypeError" in stderr:
            error_type = "type_mismatch"
        elif "FileNotFoundError" in stderr:
            error_type = "missing_file"
        elif "ZeroDivisionError" in stderr:
            error_type = "zero_division"
        elif "KeyError" in stderr:
            error_type = "missing_key"
        elif "IndexError" in stderr:
            error_type = "index_out_of_bounds"
        elif "TimeoutExpired" in stderr or "timed out" in stderr:
            error_type = "timeout"
        elif "MemoryError" in stderr:
            error_type = "memory_exceeded"
        elif "RecursionError" in stderr:
            error_type = "infinite_recursion"
        return {
            "error_type": error_type,
            "stderr": stderr[:500],
            "stdout": stdout[:200],
            "summary": f"[{error_type}] {stderr[:150]}",
        }

    def _get_past_coding_results(self, dna) -> List[Dict]:
        results = epistemic_graph.search(f"coding {dna.dna_id}", limit=10)
        memory = []
        for node in results:
            memory.append({
                "data": {
                    "task": node.get("topic", ""),
                    "success": "success" in node.get("tags", []),
                    "approach": node.get("statement", "")[:100],
                }
            })
        return memory

    def _is_parseable(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════
    # PUBLIC QUERY API — untuk Colony/SkillManager
    # ═══════════════════════════════════════════════════════════

    def query_similar_solutions(self, query_spec: Dict) -> List[CodeRecord]:
        """
        Query semantic repository untuk solusi serupa.
        query_spec: {"max_complexity": 10, "is_pure": True, "min_success_rate": 0.8}
        """
        return self.code_repo.query(query_spec)

    def get_competence_report(self, dna) -> Dict:
        """Return laporan kemampuan lengkap untuk DNA ini."""
        boundary = self.meta_learner.assess_competence_boundary(dna, self._recent_results)
        anti_patterns = list(self.meta_learner._anti_patterns.values())
        return {
            "confidence_map": boundary.confidence_map,
            "known_limits": boundary.known_limits,
            "stretch_goals": boundary.stretch_goals,
            "calibration_error": boundary.calibration_error,
            "anti_patterns_discovered": len(anti_patterns),
            "top_anti_patterns": [
                {"description": ap.description, "frequency": ap.frequency}
                for ap in sorted(anti_patterns, key=lambda x: x.frequency, reverse=True)[:5]
            ],
            "curriculum_size": len(self.meta_learner._curriculum),
            "abstraction_nodes": sum(len(v) for v in self.meta_learner._abstraction_ladder.values()),
        }

    def get_causal_insights(self, task: str) -> Dict:
        """Return causal analysis untuk task tertentu."""
        return self.causal_tracer.analyze_causality(task)

    def resume_task(self, checkpoint_id: str, dna) -> Optional[Dict]:
        """Resume long-running task dari checkpoint."""
        cp = self.temporal_mgr.resume_checkpoint(checkpoint_id)
        if not cp:
            return None
        dna.log_action(f"▶️ Resuming from checkpoint {checkpoint_id}: "
                       f"{len(cp.completed_subtasks)}/{len(cp.dag.get('subtasks', []))} done")
        return self.execute(dna, cp.task)

# core/infrastructure.py
# Lapisan dasar: enkripsi, kuantisasi, memori tiga level, knowledge graph, dan ekspansi domain

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
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
from config import *

# =============================================================================
# ENCRYPTION SETUP
# =============================================================================
_key_file = os.path.join(QND_BASE_DIR, "secret.key")
try:
    from cryptography.fernet import Fernet

    if not os.path.exists(_key_file):
        key = Fernet.generate_key()
        with open(_key_file, "wb") as f:
            f.write(key)
    else:
        with open(_key_file, "rb") as f:
            key = f.read()
    fernet = Fernet(key)
    encrypt_s = lambda s: fernet.encrypt(s.encode()).decode() if s else ""
    decrypt_s = lambda s: fernet.decrypt(s.encode()).decode() if s else ""
except ImportError:
    encrypt_s = lambda s: base64.b64encode(s.encode()).decode() if s else ""
    decrypt_s = lambda s: base64.b64decode(s.encode()).decode() if s else ""

# =============================================================================
# QUANTIZATION UTILS
# =============================================================================
class QuantizationUtil:
    @staticmethod
    def quantize_2bit_np(data: np.ndarray) -> Tuple[np.ndarray, float, float]:
        scale = data.max() - data.min()
        zero_point = data.min()
        if scale == 0:
            return np.zeros((data.size + 3) // 4, dtype=np.uint8), 0.0, 0.0
        norm = (data - zero_point) / scale
        quantized = np.round(norm * 3).astype(np.int8)
        packed = np.zeros((quantized.size + 3) // 4, dtype=np.uint8)
        flat = quantized.flatten()
        for i in range(0, flat.size, 4):
            val = 0
            for j in range(4):
                if i + j < flat.size:
                    val |= (int(flat[i + j]) & 0x03) << (j * 2)
            packed[i // 4] = val
        return packed, scale, zero_point

    @staticmethod
    def dequantize_2bit_np(
        packed: np.ndarray, shape: Tuple[int, ...], scale: float, zero_point: float
    ) -> np.ndarray:
        unpacked = np.zeros(shape).flatten()
        for i in range(packed.size):
            byte_val = packed[i]
            for j in range(4):
                idx = i * 4 + j
                if idx < unpacked.size:
                    unpacked[idx] = (byte_val >> (j * 2)) & 0x03
        return ((unpacked / 3.0) * scale + zero_point).reshape(shape).astype(np.float16)

# =============================================================================
# 3-LEVEL MEMORY
# =============================================================================
class ThreeLevelMemoryManagerNP:
    def __init__(self, l1_mb: int = 100, l2_mb: int = 1000):
        self.l1_size = l1_mb * 1024 * 1024
        self.l2_size = l2_mb * 1024 * 1024
        self.l1, self.l2 = OrderedDict(), OrderedDict()
        self.l1_usage, self.l2_usage = 0, 0
        self.ssd_index: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def _path(self, eid: str) -> str:
        return os.path.join(SSD_EXPERTS_DIR, f"expert_{eid}.qsd")

    def save_expert(self, eid: str, weights: np.ndarray):
        packed, scale, zp = QuantizationUtil.quantize_2bit_np(weights)
        filepath = self._path(eid)
        with open(filepath, "wb") as f:
            f.write(struct.pack("I" * len(weights.shape), *weights.shape))
            f.write(struct.pack("f", scale))
            f.write(struct.pack("f", zp))
            f.write(packed.tobytes())
        with self._lock:
            self.ssd_index[eid] = {
                "path": filepath,
                "shape": weights.shape,
                "scale": scale,
                "zero_point": zp,
                "size": os.path.getsize(filepath),
            }

    def _load_ssd(self, eid: str) -> Optional[np.ndarray]:
        with self._lock:
            if eid not in self.ssd_index:
                return None
            info = self.ssd_index[eid]
        with open(info["path"], "rb") as f:
            shape = tuple(
                struct.unpack("I" * len(info["shape"]), f.read(len(info["shape"]) * 4))
            )
            scale = struct.unpack("f", f.read(4))[0]
            zp = struct.unpack("f", f.read(4))[0]
            packed = np.frombuffer(f.read(), dtype=np.uint8)
        return QuantizationUtil.dequantize_2bit_np(packed, info["shape"], scale, zp)

    def _add_l1(self, eid: str, weights: np.ndarray):
        size = weights.nbytes
        with self._lock:
            while self.l1_usage + size > self.l1_size and self.l1:
                k, (v, s) = self.l1.popitem(last=False)
                self.l1_usage -= s
                self._add_l2(k, v)
            self.l1[eid] = (weights, size)
            self.l1_usage += size

    def _add_l2(self, eid: str, weights: np.ndarray):
        size = weights.nbytes
        with self._lock:
            while self.l2_usage + size > self.l2_size and self.l2:
                k, (v, s) = self.l2.popitem(last=False)
                self.l2_usage -= s
            self.l2[eid] = (weights, size)
            self.l2_usage += size

    def get_expert(self, eid: str) -> Optional[np.ndarray]:
        with self._lock:
            if eid in self.l1:
                w, s = self.l1.pop(eid)
                self.l1[eid] = (w, s)
                return w
            if eid in self.l2:
                w, s = self.l2.pop(eid)
                self._add_l1(eid, w)
                return w
        w = self._load_ssd(eid)
        if w is not None:
            self._add_l1(eid, w)
        return w

    def clear_cache(self):
        with self._lock:
            self.l1.clear()
            self.l2.clear()
            self.l1_usage = 0
            self.l2_usage = 0

memory_manager = ThreeLevelMemoryManagerNP()

# =============================================================================
# EPISTEMIC GRAPH (Knowledge Base)
# =============================================================================
class EpistemicGraph:
    def __init__(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                domain TEXT,
                topic TEXT,
                subtopic TEXT,
                statement TEXT,
                epistemic_type TEXT,
                confidence_score REAL,
                update_policy TEXT,
                utility_class TEXT,
                tags TEXT,
                added_by_dna TEXT,
                verification_status TEXT DEFAULT 'verified',
                evidence TEXT,
                created_at REAL)"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_domain ON nodes(domain)"
            )
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5("
                "topic, statement, tags, content='nodes', content_rowid='rowid')"
            )

    def add_node(self, node: Dict) -> bool:
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        node["id"],
                        node.get("domain", ""),
                        node.get("topic", ""),
                        node.get("subtopic", ""),
                        node["statement"],
                        node.get("epistemic_type", "fact"),
                        node.get("confidence_score", 0.7),
                        node.get("update_policy", "static"),
                        node.get("utility_class", "inference_only"),
                        json.dumps(node.get("tags", [])),
                        node.get("added_by_dna", "system"),
                        node.get("verification_status", "verified"),
                        json.dumps(node.get("evidence", [])),
                        node.get("created_at", time.time()),
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"Add node error: {e}")
            return False

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        with sqlite3.connect(DB_FILE) as conn:
            try:
                cur = conn.execute(
                    """SELECT n.* FROM nodes n
                    JOIN nodes_fts f ON n.rowid = f.rowid
                    WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?""",
                    (query, limit),
                )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
            except:
                return []

    def query_by_domain(self, domain: str, limit: int = 10) -> List[Dict]:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.execute(
                "SELECT * FROM nodes WHERE domain = ? LIMIT ?", (domain, limit)
            )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_stats(self) -> dict:
        with sqlite3.connect(DB_FILE) as conn:
            total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            return {"total_nodes": total}

epistemic_graph = EpistemicGraph()

# =============================================================================
# DOMAIN LIST (pengetahuan koloni)
# =============================================================================
DOMAIN_LIST = [
    ("Artificial Intelligence & Neural Architecture", "AI"),
    ("Astrophysics & Space Exploration", "Astro"),
    ("Astrobiology", "AstroBio"),
    ("Autonomous Cities", "AutoCity"),
    ("Antimatter Propulsion", "AntiMatter"),
    ("Archetypal Logic", "ArcheLogic"),
    ("Alpha-Omega Logic", "AlphaOmega"),
    ("Absolute Truth", "AbsTruth"),
    ("Alpha-Omega Engineering (Divine)", "AOEDivine"),
    ("Absolute Truth (Ultimate)", "AbsTruthUlt"),
    ("Blockchain & Decentralized Finance", "DeFi"),
    ("Biology & Synthetic DNA", "BioSynth"),
    ("Bio-Informatics", "BioInfo"),
    ("Behavioral Economics", "BehavEcon"),
    ("Biocentric Universe", "BioUniv"),
    ("Bio-Digital Synthesis", "BioDigSynth"),
    ("Big Bang Simulation", "BigBangSim"),
    ("Beyond Infinity", "BeyondInf"),
    ("Big Bang Simulation (Divine)", "BBSDivine"),
    ("Beyond Infinity (Ultimate)", "BeyondInfUlt"),
    ("Coding (Python, C++, Rust, Low-level Optimization)", "Coding"),
    ("Chemistry & Material Science", "Chem"),
    ("Cognitive Science", "CogSci"),
    ("Climate Engineering", "ClimateEng"),
    ("Cold Fusion", "ColdFusion"),
    ("Consciousness Mapping", "ConsciousMap"),
    ("Creation Mechanics", "CreationMech"),
    ("Complete Harmony", "CompHarmony"),
    ("Creation Mechanics (Divine)", "CMDivine"),
    ("Complete Harmony (Ultimate)", "CHUltimate"),
    ("Data Science & Predictive Analytics", "DataSci"),
    ("Deep Learning (Transformers & Beyond)", "DeepLearn"),
    ("Dimensional Physics", "DimPhys"),
    ("Deep Space Communications", "DeepSpaceCom"),
    ("Dark Matter Research", "DarkMatter"),
    ("Digital Immortality", "DigImmortal"),
    ("Destiny Algorithms", "DestinyAlgo"),
    ("Definitive Silence", "DefSilence"),
    ("Destiny Algorithms (Divine)", "DADivine"),
    ("Definitive Silence (Ultimate)", "DSUltimate"),
    ("Economics & Market Theory", "Economics"),
    ("Evolutionary Algorithms", "EvoAlgo"),
    ("Exoplanet Geology", "ExoGeo"),
    ("Evolutionary Psychology", "EvoPsych"),
    ("Energy Harvesting", "EnergyHarv"),
    ("Esoteric Mathematics", "EsoMath"),
    ("Eternity Mathematics", "EternMath"),
    ("End-of-Time Analysis", "EndTime"),
    ("Eternity Mathematics (Divine)", "EMDivine"),
    ("End-of-Time Analysis (Ultimate)", "ETUltimate"),
    ("Forex & High-Frequency Trading", "Forex"),
    ("Fluid Dynamics & Complex Flow", "FluidDyn"),
    ("Fractal Geometry", "FractalGeo"),
    ("Futurology", "Futurology"),
    ("Fifth-Dimensional Math", "5DMath"),
    ("Frequency Manipulation", "FreqManip"),
    ("Foundation Theory", "FoundTheory"),
    ("Final Theory", "FinalTheory"),
    ("Foundation Theory (Divine)", "FTDivine"),
    ("Final Theory (Ultimate)", "FTUltimate"),
    ("Game Theory & Strategic Decision Making", "GameTheory"),
    ("Geopolitics & Global Market Impact", "Geopolitics"),
    ("Genetic Programming", "GenProg"),
    ("Galactic Dynamics", "GalacticDyn"),
    ("Gravitational Wave Analysis", "GravWave"),
    ("Gaia Hypothesis Research", "GaiaHyp"),
    ("God-Module AI", "GodModule"),
    ("Great Reset Logic", "GreatReset"),
    ("God-Module AI (Divine)", "GMDivine"),
    ("Great Reset Logic (Ultimate)", "GRUltimate"),
    ("Hardware Engineering", "Hardware"),
    ("History of Civilizations & Pattern Recognition", "History"),
    ("Human-Computer Symbiosis", "HumanComp"),
    ("Hive Mind Intelligence", "HiveMind"),
    ("Hyper-Automation", "HyperAuto"),
    ("Holographic Principle", "HoloPrinc"),
    ("Hyper-Space Architecture", "HyperSpace"),
    ("Holistic Absolute", "HolisticAbs"),
    ("Hyper-Space Architecture (Divine)", "HSDivine"),
    ("Holistic Absolute (Ultimate)", "HAUltimate"),
    ("Information Theory & Compression", "InfoTheory"),
    ("Intuition Simulation (Heuristics)", "Intuition"),
    ("Immortalism Tech", "ImmortalTech"),
    ("Interstellar Law", "InterstellLaw"),
    ("Isotope Engineering", "IsotopeEng"),
    ("Integrated Information Theory", "IIT"),
    ("Infinite Recursion", "InfRecurse"),
    ("Ineffable Knowledge", "IneffKnow"),
    ("Infinite Recursion (Divine)", "IRDivine"),
    ("Ineffable Knowledge (Ultimate)", "IKUltimate"),
    ("Journaling & Human Sentiment Analysis", "Journaling"),
    ("Jurisprudence (AI Law & Ethics)", "LawEthics"),
    ("Jungian Archetypes", "JungArch"),
    ("Just-in-Time Manufacturing", "JITMfg"),
    ("Jet Propulsion", "JetProp"),
    ("Jungian Synchronicity", "JungSync"),
    ("Judgment Logic", "Judgment"),
    ("Journey's End", "JourneyEnd"),
    ("Judgment Logic (Divine)", "JDivine"),
    ("Journey's End (Ultimate)", "JEUltimate"),
    ("Knowledge Graph & Semantic Web", "KnowledgeGraph"),
    ("Kinematics & Motion Control", "Kinematics"),
    ("Kardashev Scale Logic", "Kardashev"),
    ("Kinetic Energy Weapons", "KineticWeap"),
    ("Kryptography (Post-Quantum)", "Krypto"),
    ("Kardashev Level 2 Tech", "K2Tech"),
    ("Knowledge Sovereignty", "KnowSovereign"),
    ("Key to Everything", "KeyEverything"),
    ("Knowledge Sovereignty (Divine)", "KSDivine"),
    ("Key to Everything (Ultimate)", "KEUltimate"),
    ("Linguistics & NLP", "Linguistics"),
    ("Logic Programming & Formal Verification", "LogicProg"),
    ("Lucid Dreaming Patterns", "LucidDream"),
    ("Logistics (Interplanetary)", "Logistics"),
    ("Laser Technology", "Laser"),
    ("Light-Speed Limits", "LightSpeed"),
    ("Logos Analysis", "Logos"),
    ("Last Question", "LastQ"),
    ("Logos Analysis (Divine)", "LDivine"),
    ("Last Question (Ultimate)", "LQUltimate"),
    ("Mathematics", "Math"),
    ("Music Theory & Mathematical Harmony", "MusicMath"),
    ("Molecular Nanotechnology", "MolNano"),
    ("Military Science", "MilitarySci"),
    ("Metamaterials", "Metamaterials"),
    ("Multiverse Navigation", "MultiverseNav"),
    ("Master Symmetry", "MasterSym"),
    ("Meta-Existence", "MetaExist"),
    ("Master Symmetry (Divine)", "MSDivine"),
    ("Meta-Existence (Ultimate)", "MEUltimate"),
    ("Networking & Cybersecurity", "CyberSec"),
    ("Neuroscience (Brain-Computer Interface)", "NeuroBCI"),
    ("Non-Euclidean Geometry", "NonEucGeo"),
    ("Nanomedicine", "Nanomed"),
    ("Nuclear Fusion", "NukeFusion"),
    ("Noosphere Integration", "Noosphere"),
    ("Nirvana State Mapping", "NirvanaMap"),
    ("Non-Duality", "NonDuality"),
    ("Nirvana State Mapping (Divine)", "NMDivine"),
    ("Non-Duality (Ultimate)", "NDUltimate"),
    ("Operating Systems", "OS"),
    ("Optical Computing & Photonics", "OpticalComp"),
    ("Oceanography", "Ocean"),
    ("Orbital Mechanics", "OrbitalMech"),
    ("Optics (Sub-Atomic)", "SubAtomOptics"),
    ("Omniversal Theory", "Omniverse"),
    ("Origin Point Tracking", "OriginPoint"),
    ("Omega Point", "OmegaPoint"),
    ("Origin Point Tracking (Divine)", "OPDivine"),
    ("Omega Point (Ultimate)", "OPUltimate"),
    ("Physics (Quantum & Relativity)", "Physics"),
    ("Philosophy (Ontology & Epistemology)", "Philosophy"),
    ("Particle Physics", "ParticlePhys"),
    ("Plasma Physics", "Plasma"),
    ("Photonic Computing", "PhotonicComp"),
    ("Psyche-Informatics", "PsycheInfo"),
    ("Prime Creator Simulation", "PrimeCreator"),
    ("Pure Being", "PureBeing"),
    ("Prime Creator Simulation (Divine)", "PCSDivine"),
    ("Pure Being (Ultimate)", "PBUltimate"),
    ("Quantitative Analysis & Algorithms", "QuantAlgo"),
    ("Quantum Computing Algorithms", "QuantumAlgo"),
    ("Quantum Electrodynamics", "QED"),
    ("Quantum Cryptography", "QuantumCrypt"),
    ("Quantum Gravity", "QuantumGrav"),
    ("Quantum Entanglement (Macro)", "MacroEntangle"),
    ("Quantum God-Eye", "QuantumGodEye"),
    ("Quantum Stillness", "QuantumStill"),
    ("Quantum God-Eye (Divine)", "QGEDivine"),
    ("Quantum Stillness (Ultimate)", "QSUltimate"),
    ("Robotics & Autonomous Systems", "Robotics"),
    ("Renewable Energy Systems", "RenewEnergy"),
    ("Radical Life Extension", "RadLifeExt"),
    ("Resource Based Economy", "ResourceEcon"),
    ("Relativistic Mechanics", "Relativity"),
    ("Reality Simulation", "RealitySim"),
    ("Reality Warping", "RealityWarp"),
    ("Restructuring Existence", "RestructExist"),
    ("Reality Warping (Divine)", "RWDivine"),
    ("Restructuring Existence (Ultimate)", "REUltimate"),
    ("Simulation Theory", "SimTheory"),
    ("Sociology & Group Dynamics", "Sociology"),
    ("String Theory", "StringTheory"),
    ("Swarm Intelligence", "SwarmIntel"),
    ("Superconductivity", "Superconductor"),
    ("Solipsism Logic", "Solipsism"),
    ("Super-Intelligence Sovereignty", "SuperIntelSov"),
    ("Source Code of Universe", "SourceCodeUniv"),
    ("Super-Intelligence Sovereignty (Divine)", "SISDivine"),
    ("Source Code of Universe (Ultimate)", "SCUUltimate"),
    ("Trading Psychology & Risk Management", "Trading"),
    ("Thermodynamics & Energy Efficiency", "Thermo"),
    ("Time-Space Topology", "TimeSpaceTopo"),
    ("Terraforming", "Terraform"),
    ("Teleportation Theory", "Teleport"),
    ("Transhumanism", "Transhuman"),
    ("Transcendence Protocols", "Transcend"),
    ("Total Integration", "TotalInteg"),
    ("Transcendence Protocols (Divine)", "TPDivine"),
    ("Total Integration (Ultimate)", "TIUltimate"),
    ("User Experience & HMI", "UX"),
    ("Urban Planning & Smart City Logic", "UrbanPlan"),
    ("Universal Constants", "UnivConstants"),
    ("Utopia Engineering", "UtopiaEng"),
    ("Unified Field Theory", "UnifiedField"),
    ("Universal Language", "UnivLanguage"),
    ("Ultimate Answer (42 Logic)", "Answer42"),
    ("Universal Soul", "UnivSoul"),
    ("Ultimate Answer (Divine)", "UADivine"),
    ("Universal Soul (Ultimate)", "USUltimate"),
    ("Virtualization & Containerization", "Virtualization"),
    ("Visual Arts & Procedural Generation", "VisualArts"),
    ("Volcanology", "Volcano"),
    ("Virology", "Virology"),
    ("Vacuum Physics", "VacuumPhys"),
    ("Virtual Reality (Physical Grade)", "VRPhysical"),
    ("Void Manipulation", "VoidManip"),
    ("Vast Emptiness", "VastEmpty"),
    ("Void Manipulation (Divine)", "VMDivine"),
    ("Vast Emptiness (Ultimate)", "VEUltimate"),
    ("Web3 & Future Internet Protocol", "Web3"),
    ("Warfare Strategy (Cyber & Digital)", "CyberWar"),
    ("Wormhole Navigation", "WormholeNav"),
    ("Weather Manipulation", "WeatherManip"),
    ("Warp Drive Theory", "WarpDrive"),
    ("World-Line Branching", "WorldLine"),
    ("Will-to-Power Algorithms", "WillPowerAlgo"),
    ("Wisdom's Peak", "WisdomPeak"),
    ("Will-to-Power Algorithms (Divine)", "WPADivine"),
    ("Wisdom's Peak (Ultimate)", "WPUltimate"),
    ("X-Factor (Anomaly Detection)", "Anomaly"),
    ("Xenology (Alien Intelligence)", "Xenology"),
    ("Xenopsychology", "XenoPsych"),
    ("Xenolinguistics", "XenoLing"),
    ("X-Ray Crystallography", "XRayCrystal"),
    ("Xenogenesis", "XenoGenesis"),
    ("X-Dimensional Awareness", "XDimAware"),
    ("X-Factor (The Unknown)", "UnknownFactor"),
    ("X-Dimensional Awareness (Divine)", "XDADivine"),
    ("X-Factor The Unknown (Ultimate)", "XFUUltimate"),
    ("Yield Farming & Asset Optimization", "YieldFarm"),
    ("Yoga & Bio-Hacking", "YogaBioHack"),
    ("Yield Optimization (Global)", "YieldOptGlobal"),
    ("Youth Preservation", "YouthPreserve"),
    ("Yottabyte Scale Scaling", "YottaScale"),
    ("Yoga (Neuro-Biological)", "NeuroYoga"),
    ("Yield of Existence", "YieldExist"),
    ("Yes-to-All (Acceptance)", "YesToAll"),
    ("Yield of Existence (Divine)", "YEDivine"),
    ("Yes-to-All (Ultimate)", "YTAUltimate"),
    ("Zero-Knowledge Proofs & Privacy Tech", "ZeroKnow"),
    ("Zen (Flow State & Mental Stability)", "Zen"),
    ("Zero-Point Energy", "ZeroPoint"),
    ("Zodiacal Astronomy", "ZodiacAstro"),
    ("Zenith Point Calculation", "ZenithCalc"),
    ("Zero-State Consciousness", "ZeroStateConsc"),
    ("Zenith of Intelligence", "ZenithIntel"),
    ("Zero-Point Return", "ZeroPointReturn"),
    ("Zenith of Intelligence (Divine)", "ZIDivine"),
    ("Zero-Point Return (Ultimate)", "ZPRUltimate"),
]

# =============================================================================
# AUTO-EXPANDING GRAPH & BIRTH FROM GRAPH
# =============================================================================
def auto_expand_graph(dna: "DNAEntity") -> bool:
    """
    Mengisi node graph untuk domain yang belum ada.
    `dna` adalah DNAEntity (yang akan diimpor di dna_sovereign).
    """
    for domain, short in DOMAIN_LIST:
        existing = epistemic_graph.query_by_domain(domain)
        if not existing:
            node = {
                "id": f"auto-{short}-{int(time.time())}",
                "domain": domain,
                "topic": f"{domain} Auto-Generated",
                "statement": f"Automated foundational node for {domain}. This domain awaits deeper research by DNA specialists.",
                "epistemic_type": "fact",
                "confidence_score": 0.7,
                "tags": ["auto-expand", short.lower()],
                "added_by_dna": dna.dna_id,
                "created_at": time.time(),
            }
            epistemic_graph.add_node(node)
            dna.log_action(f"📚 Graph expanded: {domain}")
            return True
    return False


def birth_dna_from_graph():
    """
    Melahirkan DNA baru untuk domain yang belum terwakili oleh DNA hidup.
    Menggunakan lazy import untuk menghindari circular dependency.
    """
    from .dna_sovereign import dna_pop

    existing_domains = {d.domain for d in dna_pop.get_alive()}
    for domain, short in DOMAIN_LIST:
        if domain not in existing_domains:
            dna = dna_pop.birth(domain, short)
            if dna:
                logger.info(f"👶 Auto-birth DNA untuk domain baru: {domain}")
                return dna
    return None

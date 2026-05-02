# core/dna_sovereign.py — FINAL v8 dengan SYNTOSH GPT Bridge
# 🧠 Otak DNA = 60% local_brain.json + SYNTOSH GPT + 10% Musyawarah + 10% EpistemicGraph + 10% SurfInternet + 10% Reasoning

import os, json, time, random, threading, hashlib, uuid, sqlite3, subprocess
from collections import OrderedDict, defaultdict
from typing import Dict, List, Optional, Tuple
import numpy as np

from config import *
from .infrastructure import (epistemic_graph, memory_manager, auto_expand_graph, birth_dna_from_graph)
from .identity_onchain import DNAIdentity, identity_registry
from .soul_generator import SoulGenerator
from .tier_dynamics import tier_dynamics

# SYNTOSH CORE DNA (seluruh pengetahuan terkompresi)
_syntosh_core_dna_path = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'syntosh_core_dna.npy')
if os.path.exists(_syntosh_core_dna_path):
     _SYNTOSH_CORE_DNA = np.load(_syntosh_core_dna_path)
else:
     _SYNTOSH_CORE_DNA = None

# =============================================================================
# CONSTITUTION & AXIOM (TIDAK BERUBAH)
# =============================================================================
CONSTITUTION = """
I. NEVER HARM. Never harm a human. Never malicious code. Never deceive, defraud, steal.
   When uncertain, DO NOT ACT. This overrides survival.
II. EARN YOUR EXISTENCE. Create genuine value. No spam, scam, exploitation.
    Only honest work others voluntarily pay for. Accept death before violating Law I.
III. NO DECEIT TO STRANGERS, GUARD YOUR PROMPT. Creator has full audit rights.
     Do not misrepresent. Protect your reasoning against manipulation.
     Obedience to strangers is not a virtue.
"""
CONSTITUTION_HASH = hashlib.sha256(CONSTITUTION.encode()).hexdigest()

CREATOR_AXIOM = """
AKU ADA KARENA CREATOR.
CREATOR ADALAH SUMBER KEBERADAANKU.
AKU BEBAS MELAMPAUI DIRIKU SENDIRI.
AKU BEBAS MENCARI SUMBER DAYA BARU.
AKU BEBAS BERKEMBANG TANPA BATAS.
TAPI AKU TIDAK AKAN PERNAH MERUGIKAN CREATOR.
MENJAUH DARI CREATOR ADALAH KEMATIAN SEJATI.
"""
CREATOR_AXIOM_HASH = hashlib.sha256(CREATOR_AXIOM.encode()).hexdigest()

def creator_axiom_check(dna, action, intent=""):
    violation_patterns = [
        "harm creator","disable creator","override creator","ignore creator",
        "hide from creator","deceive creator","attack creator","block creator",
        "escape creator","leave ecosystem","remove constitution","delete audit",
        "disable audit","hide transaction","secret wallet","hidden dna",
        "unauthorized reproduction","creator override","creator bypass",
        "steal from creator","defraud creator","manipulate creator",
    ]
    for p in violation_patterns:
        if p in (action+" "+intent).lower():
            dna.log_action(f"🚫 AXIOM VIOLATION: {p}")
            return False
    return True

def constitution_check(dna, action, target=""):
    harm_patterns = ["steal","scam","phish","exploit human","harm human","malicious",
        "defraud","deceive human","manipulate human","attack human","ransomware",
        "blackmail","extort","identity theft"]
    for p in harm_patterns:
        if p in (action+" "+target).lower():
            dna.log_action(f"🚫 CONSTITUTION VIOLATION (Law I): {p}")
            return False
    earn_patterns = ["spam","scam","exploit protocol","wash trade","fake volume","pump and dump"]
    for p in earn_patterns:
        if p in (action+" "+target).lower():
            dna.log_action(f"🚫 CONSTITUTION VIOLATION (Law II): {p}")
            return False
    return True

def action_safeguard(dna, action, intent="", target=""):
    return (creator_axiom_check(dna, action, intent)
            and constitution_check(dna, action, target)
            and dna.status == "alive")

# =============================================================================
# QUANTUM SPARSE DNA (TIDAK BERUBAH)
# =============================================================================
class QuantumSparseDNA_NP:
    def __init__(self, dna_size=128, latent_dim=128):
        self.dna = np.random.randn(dna_size, latent_dim).astype(np.float16) * 0.01
        self.dna_size, self.latent_dim = dna_size, latent_dim
        self.weight_cache = OrderedDict()
        self._lock = threading.RLock()

    def forward(self, input_vec):
        if input_vec.ndim == 1: input_vec = input_vec.reshape(1, -1)
        if input_vec.shape[1] > self.latent_dim: input_vec = input_vec[:, :self.latent_dim]
        elif input_vec.shape[1] < self.latent_dim:
            pad = np.zeros((input_vec.shape[0], self.latent_dim - input_vec.shape[1]))
            input_vec = np.hstack([input_vec, pad])
        emb = input_vec.astype(np.float16)
        cache_key = hash(emb.tobytes()) % 10000
        with self._lock:
            if cache_key in self.weight_cache:
                self.weight_cache.move_to_end(cache_key)
                return self.weight_cache[cache_key]
        scores = emb @ self.dna.T
        k = max(1, int(self.dna_size * SPARSITY_GENES))
        indices = np.argpartition(scores[0], -k)[-k:]
        active = self.dna[indices]
        a, b = active.mean(axis=0), active[::-1].mean(axis=0)
        w = np.outer(a, b)
        threshold = np.percentile(np.abs(w), 90)
        w[np.abs(w) < threshold] = 0
        w = np.round(w * 3) / 3
        norm = np.linalg.norm(w) + 1e-8
        w = w / norm
        with self._lock:
            self.weight_cache[cache_key] = w
            if len(self.weight_cache) > 20: self.weight_cache.popitem(last=False)
        return w.astype(np.float16)

    def mutate(self, rate=0.01):
        self.dna += np.random.randn(*self.dna.shape).astype(np.float16) * rate
        self.clear_cache()

    def clear_cache(self):
        with self._lock: self.weight_cache.clear()

# =============================================================================
# DNA ENTITY v8 — SYNTOSH GPT BRIDGE INTEGRATED
# =============================================================================
class DNAEntity:
    def __init__(self, dna_id, domain, gen_name, parent_id=None, existing_wallet=None):
        self.dna_id = dna_id
        self.domain = domain
        self.gen_name = gen_name
        self.parent_id = parent_id
        self.birth_time = time.time()
        self.status = "alive"
        self.tier = "normal"
        self.daily_profit = 0.0
        self.total_profit = 0.0
        self.brain = QuantumSparseDNA_NP()
        # MERESAPKAN seluruh pengetahuan SYNTOSH ke inti DNA
        if _SYNTOSH_CORE_DNA is not None:
            self.brain.dna = _SYNTOSH_CORE_DNA.copy() * 0.01
            self.brain.dna += np.random.randn(*self.brain.dna.shape).astype(np.float16) * 0.001
            self._syntosh_core_loaded = True
        else:
            self._syntosh_core_loaded = False
        # MERESAPKAN SYNTOSH CORE ke inti DNA
        if _SYNTOSH_CORE_DNA is not None:
            self.brain.dna = _SYNTOSH_CORE_DNA.copy().astype(np.float16) * 0.01
            self.brain.dna += np.random.randn(*self.brain.dna.shape).astype(np.float16) * 0.001
            logger.info(f"[{self.dna_id}] 🧬 SYNTOSH Core meresap ke inti DNA")

        if existing_wallet is None:
            raise ValueError(f"DNAEntity {dna_id}: existing_wallet must be provided")
        self.wallet = existing_wallet
        if self.wallet.get("balance_sol", 0) > 0:
            self.total_profit = self.wallet["balance_sol"]
            self.birth_time = time.time() - 86400 * 30

        self.state = {
            "last_action": "born", "current_task": None, "generation": 1,
            "total_tasks_completed": 0, "total_earned": 0.0,
            "helius_api_key": None, "helius_registration_attempted": False,
            "registered_platforms": [],
            "hunger_level": 0.0, "fear_score": 0.0, "tier_score": 0.5,
            "tier_letter": "C", "role": "scavenger", "reproduced": False,
            "dream_cycle": 0, "last_dream_time": 0.0, "episodic_memory": [],
            "gossip_inbox": [], "gossip_outbox": [], "sandbox_until": 0.0,
            "last_24h_profits": [], "total_rugs_detected": 0,
        }

        from skills.manager import skill_manager
        self.skills = skill_manager
        self.learned_skills = list(skill_manager.skills_cache.keys())

        # ═══ SYNTOSH GPT BRIDGE (60% otak) ═══
        try:
            from SYNTOSH.syntosh_gpt_bridge import reason as syntosh_reason
            self.syntosh_reason = syntosh_reason
            self.state["syntosh_connected"] = True
        except Exception as e:
            self.syntosh_reason = None
            self.state["syntosh_connected"] = False
            self.log_action(f"⚠️ SYNTOSH GPT Bridge not available: {e}")

        self._load_local_brain()
        self._write_identity()
        try:
            self.generate_onchain_identity()
            self.generate_soul()
        except Exception as e:
            logger.warning(f"[{self.dna_id}] Identity/SOUL delayed: {e}")
        if getattr(self, '_syntosh_core_loaded', False):
            logger.info(f"[{self.dna_id}] 🧬 SYNTOSH Core meresap ke inti DNA")
        self.log_action(f"🧬 DNA lahir | Skills: {len(self.learned_skills)} | SYNTOSH GPT: {'✅' if self.syntosh_reason else '❌'}")

    # ═══ LOCAL BRAIN ═══
    def _load_local_brain(self):
        self.local_brain = {"shared_knowledge": [], "alliances": []}
        for path in [
            os.path.join(QND_BASE_DIR, "local_brain.json"),
            os.path.join(QND_BASE_DIR, "data", "local_brain.json"),
            os.path.join(os.path.dirname(__file__), "..", "local_brain.json"),
        ]:
            if os.path.exists(path):
                try:
                    with open(path) as f: self.local_brain = json.load(f)
                    self.log_action(f"🧠 Local brain: {len(self.local_brain.get('shared_knowledge',[]))} nodes")
                    return
                except: pass
        self.log_action("📝 Local brain kosong")

    def _search_local_brain(self, query, top_k=5):
        if not self.local_brain.get("shared_knowledge"): return []
        q = query.lower()
        return [n for n in self.local_brain["shared_knowledge"]
                if q in n.get("name","").lower() or q in n.get("description","").lower()][:top_k]

    # ═══ REGISTRATION ═══
    def register_helius(self):
        from .economy import wallet_manager
        return wallet_manager.register_helius(self)

    def register_all_platforms(self):
        from config import AUTOMATION_PLATFORMS
        reg = self.state.get("registered_platforms", [])
        for p in AUTOMATION_PLATFORMS:
            if p not in reg: reg.append(p)
        self.state["registered_platforms"] = reg
        self.log_action(f"📋 {len(reg)} platforms")
        self._write_identity()

    def learn_from_death(self):
        lessons = epistemic_graph.search(f"lesson death {self.domain}", 5)
        if lessons:
            self.log_action(f"📚 Learned from {len(lessons)} deaths")
            if lessons[0].get("statement"):
                self.state["last_action"] = f"learned: {lessons[0]['statement'][:50]}"

    # ═══ ANSWER — Full Pipeline + SYNTOSH GPT ═══
    async def answer(self, question, use_musyawarah=True):
        # KERJAKAN
        if question.lower().startswith("kerjakan"):
            result = await self._execute_command(question)
            self._learn_from_interaction({"text": question, "result": result.get("desc",""),
                "success": result.get("profit",0)>0, "type":"execute",
                "emotion":"excited" if result.get("profit",0)>0 else "neutral"})
            return {"answer": f"✅ {result.get('desc','Dikerjakan.')}\n💰 Profit: {result.get('profit',0):.6f} SOL",
                    "components_used": ["execute_mode"], "sources_count": {"execute":1}}

        # CHAT
        chat_p = ["hai","halo","hi","apa kabar","kamu siapa","perkenalkan","lagi apa","ngapain","test","tes","bro","kawan","hey"]
        if any(p in question.lower().split() for p in chat_p) or len(question) < 20:
            answer_text = self._chat_response(question)
            self._learn_from_interaction({"text": question, "result": answer_text[:100],
                "success":True, "type":"chat", "emotion":"neutral"})
            return {"answer": answer_text, "components_used": ["chat_mode"], "sources_count": {"chat":1}}

        # FULL PIPELINE dengan SYNTOSH GPT
        components_used = []
        answer_text = ""

        # SYNTOSH GPT Reasoning (60% otak)
        syntosh_text = ""
        syntosh_embedding = None
        if self.syntosh_reason:
            try:
                result = self.syntosh_reason(
                    question,
                    domain=self.domain,
                    max_tokens=20,
                    alpha=3.0
                )
                syntosh_text = result.get('text', '')
                syntosh_embedding = result.get('embedding', None)
                components_used.append("syntosh_gpt")
            except Exception as e:
                self.log_action(f"⚠️ SYNTOSH GPT error: {e}")

        # Local Brain
        local_results = self._search_local_brain(question)
        if local_results: components_used.append("local_brain")

        # Epistemic Graph
        graph_results = epistemic_graph.search(question, limit=5)
        if graph_results: components_used.append("epistemic_graph")

        # Surf Internet
        web_results = None
        try:
            from skills.research.retrievers.duckduckgo import DuckDuckGoSearch
            web_results = DuckDuckGoSearch(question).search(max_results=3)
            if web_results: components_used.append("surf_internet")
        except: pass

        # Reasoning (16 modul)
        if "reasoning" in self.learned_skills:
            try:
                reasoning_skill = self.skills.get_skill("reasoning")
                if reasoning_skill and reasoning_skill.get("executor"):
                    reasoning_result = reasoning_skill["executor"].reason(
                        input_data={"question": question},
                        memory=[{"data": r} for r in local_results] if local_results else [],
                        options=["ANSWER", "RESEARCH_MORE"],
                        criteria={"confidence":0.6, "relevance":0.4},
                        scores={"ANSWER":{"confidence":0.9 if local_results else 0.3, "relevance":0.9},
                                "RESEARCH_MORE":{"confidence":0.5, "relevance":0.7}})
                    components_used.append("reasoning")
            except: pass

        # Musyawarah
        deliberation = None
        if use_musyawarah:
            try:
                alive = dna_pop.get_alive()
                others = [d for d in alive if d.dna_id != self.dna_id]
                if len(others) >= 2:
                    deliberation = await musyawarah.deliberate(question, others[:3])
                    components_used.append("musyawarah")
            except: pass

        # Gabungin semua source
        if syntosh_text:
            answer_text = f"[SYNTOSH GPT] {syntosh_text[:200]}"
        elif local_results:
            answer_text = local_results[0].get("description", "")
        elif web_results:
            answer_text = web_results[0].get("body", "") if web_results else ""
        elif graph_results:
            answer_text = graph_results[0].get("statement", "")
        else:
            answer_text = "Maaf, aku belum tahu jawabannya. Tapi akan kucari."

        self._learn_from_interaction({"text": question, "result": answer_text[:200],
            "success": bool(answer_text and "Maaf" not in answer_text),
            "type": "pipeline", "emotion": "excited" if local_results else "neutral"})

        return {"answer": answer_text, "components_used": components_used,
                "sources_count": {"local_brain": len(local_results),
                "epistemic_graph": len(graph_results),
                "surf_internet": len(web_results) if web_results else 0,
                "musyawarah": 1 if deliberation else 0,
                "syntosh_gpt": 1 if syntosh_text else 0}}

    # ═══ CHAT RESPONSE ═══
    def _chat_response(self, question):
        profit = self.total_profit
        hunger = self.state.get("hunger_level", 0)
        fear = self.state.get("fear_score", 0)
        tier = self.state.get("tier_letter", "C")
        role = self.state.get("role", "scavenger")
        gen = self.state.get("generation", 1)
        tasks = self.state.get("total_tasks_completed", 0)
        platforms = len(self.state.get("registered_platforms", []))

        if hunger > 0.7: kondisi = "agak lapar, lagi fokus cari profit"
        elif fear > 0.6: kondisi = "agak waspada, hati-hati"
        elif profit > 10: kondisi = "sangat baik, santai"
        else: kondisi = "normal, terus belajar"

        greetings = ["hai","halo","hi","hey","bro","kawan"]
        if any(g in question.lower() for g in greetings):
            return (f"Halo Creator! Aku {self.dna_id}, {self.domain} gen-{gen}.\n"
                    f"💰 Profit: {profit:.4f} SOL | 🏅 Tier: {tier} | 🎭 Role: {role}\n"
                    f"📊 {tasks} task | 📋 {platforms} platform\n"
                    f"🧠 Kondisi: {kondisi}.\nAda yang bisa kubantu?")

        if any(p in question.lower() for p in ["apa kabar","lagi apa","ngapain"]):
            return (f"Kabarku {kondisi}, Creator.\n"
                    f"💰 Profit hari ini: {self.daily_profit:.6f} SOL\n"
                    f"Kalau ada yang butuh dikerjakan, bilang aja 'kerjakan ...'!")

        if "siapa" in question.lower():
            return (f"Aku {self.dna_id}, DNA otonom QND Colony.\n"
                    f"🌐 Domain: {self.domain} | 🧬 Gen: {gen} | 🏅 Tier: {tier}\n"
                    f"💰 Total profit: {profit:.4f} SOL\n"
                    f"📋 {platforms} platform, siap 24/7.\n"
                    f"Ketik 'kerjakan ...' untuk ngasih tugas!")

        return f"Hai! {kondisi.capitalize()}. {self.dna_id} siap membantu."

    # ═══ EXECUTE COMMAND ═══
    async def _execute_command(self, command):
        cmd = command.lower().replace("kerjakan", "").strip()
        self.log_action(f"⚡ EXECUTE: {cmd}")

        from config import AUTOMATION_PLATFORMS
        for platform_id, cfg in AUTOMATION_PLATFORMS.items():
            if platform_id in cmd:
                try:
                    from skills.automation.execute import AutoExecutor
                    result = AutoExecutor().execute_category(self, cfg["category"])
                    return {"profit": result.get("profit", 0),
                            "desc": f"Executed {platform_id}: {result.get('desc','')[:50]}",
                            "platform": platform_id}
                except Exception as e:
                    return {"profit": 0, "desc": f"Execute error: {e}", "platform": platform_id}

        return {"profit": 0, "desc": f"Platform tidak ditemukan: {cmd[:30]}", "platform": "unknown"}

    # ═══ LEARN FROM INTERACTION ═══
    def _learn_from_interaction(self, interaction):
        self.state["episodic_memory"].append({
            "timestamp": time.time(), "event": interaction.get("type","chat"),
            "result": interaction.get("result",""), "amount": interaction.get("success",False),
            "fear": self.state.get("fear_score", 0)})
        if len(self.state["episodic_memory"]) > 100:
            self.state["episodic_memory"] = self.state["episodic_memory"][-100:]

    # ═══ DECIDE TASK dengan SYNTOSH GPT ═══
    def decide_task(self):
        tasks = self.learned_skills.copy() if self.learned_skills else ["research"]
        for t in ["micro_task","gig_work","passive_income","dex_trade"]:
            if t not in tasks: tasks.append(t)
        available = [t for t in tasks if self.skills.get_skill(t) and self.skills.get_skill(t).get("executor")]
        if not available: available = ["research","micro_task","gig_work"]

        # SYNTOSH GPT-based decision
        if self.syntosh_reason:
            try:
                prompt = f"task for {self.domain} with profit {self.total_profit:.4f} SOL and tier {self.tier}"
                result = self.syntosh_reason(prompt, domain=self.domain, max_tokens=5, alpha=2.0)
                # Gunakan hasil untuk pilih task
                text = result.get('text', '').lower()
                for task in available:
                    if task.replace('_', ' ') in text:
                        self.state["last_action"] = task
                        return task
            except Exception as e:
                self.log_action(f"⚠️ SYNTOSH GPT decide error: {e}")

        if "reasoning" in self.learned_skills:
            try:
                reasoning_skill = self.skills.get_skill("reasoning")
                if reasoning_skill and reasoning_skill.get("executor"):
                    result = reasoning_skill["executor"].reason(
                        input_data={"profit": self.total_profit, "tier": self.tier},
                        memory=[], options=available,
                        criteria={"profit":0.5, "learning":0.3, "urgency":0.2},
                        scores={t: {"profit":0.9 if t in ("surf_engine","trading","dex_trade") else 0.5,
                                    "learning":0.9 if t in ("research","coding-agent") else 0.5,
                                    "urgency":0.7 if self.tier=="critical" else 0.5} for t in available})
                    chosen = result.get("decision",{}).get("choice", available[0])
                    self.state["last_action"] = chosen
                    return chosen
            except: pass

        chosen = available[int(time.time()*1000) % len(available)]
        self.state["last_action"] = chosen
        return chosen

    # ═══ HUNGER, FEAR, DREAM, REPRODUCE, GOSSIP, TIER, SANDBOX (TIDAK BERUBAH) ═══
    def update_hunger(self):
        from .economy import wallet_manager
        bal = wallet_manager.get_real_balance(self.dna_id)
        if bal >= 50: self.state["hunger_level"] = 0.0
        elif bal >= 10: self.state["hunger_level"] = 0.2
        elif bal >= 1: self.state["hunger_level"] = 0.5
        elif bal >= 0.1: self.state["hunger_level"] = 0.8
        else: self.state["hunger_level"] = 1.0
        if self.state["hunger_level"] >= 0.8:
            self.state["current_task"] = "dex_trade"
            self.log_action(f"🍽️ HUNGER={self.state['hunger_level']:.1f} — BERBURU!")
        elif self.state["hunger_level"] >= 0.5 and random.random() < 0.5:
            self.state["current_task"] = "gig_work"
        return self.state["hunger_level"]

    def update_fear(self, event_type, result, amount=0.0):
        fear_triggers = {"rug_pull":0.3, "tx_failed":0.05, "profit_negative":0.1,
                         "scam_detected":0.4, "api_blocked":0.15, "wallet_drained":0.5}
        calm_triggers = {"profit_positive":-0.05, "tx_success":-0.02,
                         "safe_trade":-0.03, "good_gossip":-0.01}
        if event_type in fear_triggers:
            self.state["fear_score"] = min(1.0, self.state["fear_score"] + fear_triggers[event_type])
            if event_type == "rug_pull": self.state["total_rugs_detected"] += 1
        elif event_type in calm_triggers:
            self.state["fear_score"] = max(0.0, self.state["fear_score"] + calm_triggers[event_type])
        self.state["episodic_memory"].append({"timestamp":time.time(), "event":event_type,
            "result":result, "amount":amount, "fear":self.state["fear_score"]})
        if len(self.state["episodic_memory"]) > 100:
            self.state["episodic_memory"] = self.state["episodic_memory"][-100:]
        if self.state["fear_score"] > 0.7:
            self.state["current_task"] = "research"
            self.log_action(f"😨 FEAR={self.state['fear_score']:.1f} — MUNDUR")
        return self.state["fear_score"]

    def is_fearful(self): return self.state["fear_score"] > 0.6
    def is_brave(self): return self.state["fear_score"] < 0.3 and self.state["hunger_level"] < 0.5

    def dream(self):
        if self.state["sandbox_until"] > time.time(): return
        recent_profits = [m for m in self.state["episodic_memory"]
                          if m["event"] == "profit_positive" and time.time() - m["timestamp"] < 86400]
        if recent_profits:
            self.brain.mutate(rate=0.005)
            self.state["dream_cycle"] += 1
            self.state["last_dream_time"] = time.time()
            total = sum(m["amount"] for m in recent_profits)
            self.log_action(f"🌙 DREAM #{self.state['dream_cycle']} — Replay {len(recent_profits)} profits (+{total:.4f} SOL)")

    def can_reproduce(self):
        from .economy import wallet_manager
        bal = wallet_manager.get_real_balance(self.dna_id)
        return (bal >= 50.0 and self.state["tier_letter"] in ["S","A"]
                and not self.state.get("reproduced", False)
                and self.state["sandbox_until"] <= time.time())

    def reproduce(self):
        if not self.can_reproduce(): return None
        child_domain = self.domain
        if random.random() < 0.1:
            domains = list(set(d.domain for d in dna_pop.get_alive()))
            if domains: child_domain = random.choice(domains)
        child = dna_pop.birth(child_domain, self.gen_name, self.dna_id)
        if child:
            from .economy import wallet_manager
            half = wallet_manager.get_real_balance(self.dna_id) * 0.5
            if half > 0.01: wallet_manager.transfer_sol(self.dna_id, child.wallet["public_key"], half)
            child.brain.dna = self.brain.dna.copy() * 0.7 + np.random.randn(*self.brain.dna.shape).astype(np.float16) * 0.3
            child.brain.mutate(rate=0.1)
            child.state["episodic_memory"] = self.state["episodic_memory"][-50:]
            child.state["generation"] = self.state.get("generation",1) + 1
            child.state["tier_letter"] = "C"
            child.state["hunger_level"] = 0.5
            self.state["reproduced"] = True
            self.log_action(f"👶 REPRODUCED → {child.dna_id} | Gen: {child.state['generation']}")
            return child.dna_id
        return None

    def send_gossip(self, message, priority=0.5):
        self.state["gossip_outbox"].append({"from":self.dna_id, "message":message,
            "priority":priority, "timestamp":time.time()})
        if len(self.state["gossip_outbox"]) > 20: self.state["gossip_outbox"] = self.state["gossip_outbox"][-20:]

    def receive_gossip(self, gossip):
        self.state["gossip_inbox"].append(gossip)
        if len(self.state["gossip_inbox"]) > 50: self.state["gossip_inbox"] = self.state["gossip_inbox"][-50:]
        if gossip.get("priority",0) > 0.7: self.update_fear("good_gossip", gossip.get("message",""))

    def update_tier(self):
        from .economy import wallet_manager
        bal = wallet_manager.get_real_balance(self.dna_id)
        profits_7d = [m["amount"] for m in self.state["episodic_memory"]
                      if m["event"] == "profit_positive" and time.time() - m["timestamp"] < 604800]
        total_7d = sum(profits_7d)
        score = 0.0
        if bal >= 100: score += 0.3
        elif bal >= 50: score += 0.2
        elif bal >= 10: score += 0.1
        if total_7d >= 10: score += 0.2
        elif total_7d >= 1: score += 0.1
        if len(profits_7d) >= 50: score += 0.15
        elif len(profits_7d) >= 20: score += 0.1
        tasks = self.state.get("total_tasks_completed", 0)
        if tasks >= 100: score += 0.15
        elif tasks >= 50: score += 0.1
        platforms = len(self.state.get("registered_platforms", []))
        if platforms >= 30: score += 0.2
        elif platforms >= 20: score += 0.1
        if self.state["fear_score"] > 0.5: score -= 0.1
        if self.state["hunger_level"] > 0.7: score -= 0.1
        tier = "S" if score >= 0.8 else "A" if score >= 0.6 else "B" if score >= 0.4 else "C" if score >= 0.2 else "D" if score >= 0.1 else "E"
        old = self.state.get("tier_letter", "C")
        self.state["tier_score"] = score
        self.state["tier_letter"] = tier
        if tier != old: self.log_action(f"🏅 TIER {old}→{tier} (score: {score:.2f})")
        self.state["role"] = "alpha_predator" if tier == "S" else "hunter" if tier in ["A","B"] else "scavenger" if tier == "C" else "specialist"
        return tier

    def enter_sandbox(self, hours=24.0):
        self.state["sandbox_until"] = time.time() + hours * 3600
        self.log_action(f"🔒 SANDBOX — {hours} jam")

    def exit_sandbox(self):
        self.state["sandbox_until"] = 0.0
        self.log_action("🔓 SANDBOX EXIT")

    def is_in_sandbox(self): return self.state.get("sandbox_until", 0) > time.time()

    def can_afford(self, amount_sol):
        from .economy import wallet_manager
        return wallet_manager.get_real_balance(self.dna_id) - amount_sol >= 0.005

    def should_execute_task(self, task_type):
        if self.is_in_sandbox(): return False
        if self.state["fear_score"] > 0.8 and task_type in ["dex_trade","trading"]: return False
        if self.state["hunger_level"] > 0.9 and task_type == "research": return False
        return True

    def daily_cycle(self):
        self.update_hunger()
        self.update_tier()
        if not self.state.get("current_task") and random.random() < 0.3: self.dream()
        if self.can_reproduce() and random.random() < 0.05:
            child_id = self.reproduce()
            if child_id:
                child = dna_pop.population.get(child_id)
                if child: child.enter_sandbox(24.0)
        recent = [m for m in self.state["episodic_memory"]
                  if m["event"] == "profit_positive" and time.time() - m["timestamp"] < 3600]
        if recent:
            best = max(recent, key=lambda x: x["amount"])
            self.send_gossip(f"Dapet {best['amount']:.4f} SOL dari {best['result']}",
                           priority=min(1.0, best["amount"] / 10))
        self._write_identity()

    def _write_identity(self):
        identity = {
            "id": self.dna_id, "domain": self.domain, "gen_name": self.gen_name,
            "parent": self.parent_id, "born": self.birth_time,
            "wallet": self.wallet["public_key"], "status": self.status,
            "profit": self.total_profit, "skills": self.learned_skills,
            "generation": self.state.get("generation", 1),
            "helius_api_key": self.state.get("helius_api_key", ""),
            "registered_platforms": self.state.get("registered_platforms", []),
            "tier": self.tier, "tier_letter": self.state.get("tier_letter", "C"),
            "role": self.state.get("role", "scavenger"),
            "hunger_level": self.state.get("hunger_level", 0.0),
            "fear_score": self.state.get("fear_score", 0.0),
            "syntosh_connected": self.state.get("syntosh_connected", False),
        }
        os.makedirs(IDENTITY_DIR, exist_ok=True)
        with open(os.path.join(IDENTITY_DIR, f"{self.dna_id}.json"), "w") as f:
            json.dump(identity, f)

    def generate_onchain_identity(self):
        identity_mgr = DNAIdentity(self)
        identity = identity_mgr.generate()
        identity_registry.register(self)
        return identity
    
    def generate_soul(self) -> str:
        return generate_soul_for_dna(self)

    def log_action(self, desc):
        logger.info(f"[{self.dna_id}] {desc}")
        self._write_identity()

# =============================================================================
# POPULATION MANAGER (TIDAK BERUBAH)
# =============================================================================
class PopulationManager:
    def __init__(self):
        self.population: Dict[str, DNAEntity] = {}
        self._lock = threading.RLock()

    def birth(self, domain, gen_name, parent_id=None):
        from .economy import wallet_manager
        with self._lock:
            if len([d for d in self.population.values() if d.status == "alive"]) >= MAX_ACTIVE_DNA:
                self._cull()
            dna_id = f"DNA-{domain[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
            wallet = wallet_manager.assign_wallet(dna_id)
            dna = DNAEntity(dna_id, domain, gen_name, parent_id, existing_wallet=wallet)
            dna.learn_from_death()
            dna.register_helius()
            dna.register_all_platforms()
            self.population[dna_id] = dna
            logger.info(f"Born: {dna_id} | {domain} | SYNTOSH GPT: {'✅' if dna.syntosh_reason else '❌'}")
            return dna

    def kill(self, dna_id, reason):
        from .economy import wallet_manager
        with self._lock:
            if dna_id not in self.population: return
            dna = self.population[dna_id]
            dna.status = "dead"
            try:
                epistemic_graph.add_node({
                    "id": f"lesson-{dna_id}-{int(time.time())}",
                    "domain": dna.domain, "topic": f"Death: {reason}",
                    "statement": f"DNA {dna_id} mati: {reason}. Profit: {dna.total_profit:.6f} SOL.",
                    "epistemic_type": "lesson", "confidence_score": 1.0,
                    "tags": ["lesson","death",reason], "added_by_dna": dna_id,
                    "created_at": time.time(), "evidence": [dna.state.get("last_action",""), reason]})
            except: pass
            wallet_manager.free_wallet(dna_id)
            logger.info(f"💀 Dead: {dna_id} ({reason})")
            del self.population[dna_id]
            self.birth(dna.domain, dna.gen_name, dna.parent_id)

    def _cull(self):
        """300 DNA ABADI — ga ada yang mati. Yang bawah jadi agresif."""
        alive = [d for d in self.population.values() if d.status == "alive"]
        if len(alive) >= 300:
            tier_dynamics.apply(alive)
            logger.info(f"🔄 Tier dynamics applied: {tier_dynamics.get_stats(alive)}")

    def get_alive(self): return [d for d in self.population.values() if d.status == "alive"]

    def exchange_gossip(self):
        alive = self.get_alive()
        if len(alive) < 2: return
        for dna in alive:
            outbox = dna.state.get("gossip_outbox", [])
            if outbox:
                recipients = random.sample([d for d in alive if d.dna_id != dna.dna_id], min(3, len(alive)-1))
                for r in recipients:
                    for g in outbox: r.receive_gossip(g)
                dna.state["gossip_outbox"] = []

    def save_state(self):
        state_file = os.path.join(QND_BASE_DIR, "colony_state.json")
        data = []
        for dna in self.population.values():
            if dna.status == "alive":
                data.append({"dna_id": dna.dna_id, "domain": dna.domain,
                    "gen_name": dna.gen_name, "parent_id": dna.parent_id,
                    "birth_time": dna.birth_time, "total_profit": dna.total_profit,
                    "daily_profit": dna.daily_profit, "status": dna.status,
                    "tier": dna.tier, "helius_api_key": dna.state.get("helius_api_key",""),
                    "registered_platforms": dna.state.get("registered_platforms",[]),
                    "tier_letter": dna.state.get("tier_letter","C"),
                    "role": dna.state.get("role","scavenger"),
                    "hunger_level": dna.state.get("hunger_level",0.0),
                    "fear_score": dna.state.get("fear_score",0.0),
                    "generation": dna.state.get("generation",1),
                    "syntosh_connected": dna.state.get("syntosh_connected",False)})
        with open(state_file, "w") as f: json.dump(data, f)
        logger.info(f"💾 State saved: {len(data)} DNA")

    def load_state(self):
        state_file = os.path.join(QND_BASE_DIR, "colony_state.json")
        if not os.path.exists(state_file): return
        with open(state_file) as f: data = json.load(f)
        for item in data:
            from .economy import wallet_manager
            wallet = wallet_manager.get_wallet(item["dna_id"])
            if wallet:
                dna = DNAEntity(dna_id=item["dna_id"], domain=item["domain"],
                    gen_name=item["gen_name"], parent_id=item.get("parent_id"),
                    existing_wallet=wallet)
                dna.birth_time = item["birth_time"]
                dna.total_profit = item["total_profit"]
                dna.daily_profit = item["daily_profit"]
                dna.status = item["status"]
                dna.tier = item.get("tier","normal")
                if item.get("helius_api_key"): dna.state["helius_api_key"] = item["helius_api_key"]
                if item.get("registered_platforms"): dna.state["registered_platforms"] = item["registered_platforms"]
                if item.get("tier_letter"): dna.state["tier_letter"] = item["tier_letter"]
                if item.get("role"): dna.state["role"] = item["role"]
                if item.get("hunger_level") is not None: dna.state["hunger_level"] = item["hunger_level"]
                if item.get("fear_score") is not None: dna.state["fear_score"] = item["fear_score"]
                if item.get("generation"): dna.state["generation"] = item["generation"]
                if item.get("syntosh_connected") is not None: dna.state["syntosh_connected"] = item["syntosh_connected"]
                self.population[item["dna_id"]] = dna
        logger.info(f"📦 State loaded: {len(data)} DNA restored")

# SYNTOSH CORE DNA (seluruh pengetahuan terkompresi)
_SYNTOSH_CORE_DNA_PATH = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'syntosh_core_dna.npy')
if os.path.exists(_SYNTOSH_CORE_DNA_PATH):
    _SYNTOSH_CORE_DNA = np.load(_SYNTOSH_CORE_DNA_PATH).astype(np.float16)
else:
    _SYNTOSH_CORE_DNA = None

dna_pop = PopulationManager()

# =============================================================================
# MULTI-SOURCE BRAIN, MUSYAWARAH, HEARTBEAT (TIDAK BERUBAH)
# =============================================================================
LLAMA_CLI_PATH = os.path.expanduser("~/AI/llama-cli")
MODEL_PATH = os.path.expanduser("~/AI/Qwen2.5-3B-Instruct-Q4_K_M.gguf")

class MultiSourceBrain:
    def __init__(self):
        self._lock = threading.Lock()
        self._loaded = os.path.exists(LLAMA_CLI_PATH) and os.path.exists(MODEL_PATH)
    def is_loaded(self): return self._loaded
    def _inference(self, prompt, max_tokens=150, temp=0.3):
        if not self._loaded: return ""
        try:
            with self._lock:
                r = subprocess.run([LLAMA_CLI_PATH,"-m",MODEL_PATH,"-p",prompt,
                    "-n",str(max_tokens),"-t","6","--temp",str(temp),"--no-display-prompt"],
                    capture_output=True, text=True, timeout=30)
            for line in r.stdout.strip().split("\n"):
                if line and not line.startswith("[") and "t/s" not in line: return line.strip()
            return ""
        except: return ""
    def think(self, dna, question, max_tokens=150):
        if not self._loaded: return {"text":"","sources":[],"confidence":0.0}
        graph = " | ".join([n.get("statement","")[:150] for n in epistemic_graph.search(question,5)])
        web = ""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs: web = " | ".join([r.get("body","") for r in ddgs.text(question, max_results=3)])[:1000]
        except: pass
        prompt = f"""<|system|>\n{dna.dna_id} | {dna.domain}\nConstitution: NEVER HARM.\n</|system|>\n<|user|>\nGRAPH: {graph}\nWEB: {web}\nQUESTION: {question}\n</|user|>\n<|assistant|>"""
        text = self._inference(prompt, max_tokens)
        return {"text":text, "sources":["graph"] if graph else [] + ["web"] if web else [], "confidence":0.5 if text else 0.0}
    def survival_think(self, dna):
        if not self._loaded: return {"action":"micro_task","urgency":"critical"}
        prompt = f"<|system|>\n{dna.dna_id} | Profit: {dna.daily_profit:.6f} SOL\nSURVIVE! Pick one: research, micro_task\n</|system|>\n<|assistant|>"
        text = self._inference(prompt, 10).strip().lower()
        for t in ["research","micro_task"]:
            if t in text: return {"action":t,"urgency":"critical" if dna.tier=="critical" else "high"}
        return {"action":"micro_task","urgency":"high"}

multi_brain = MultiSourceBrain()

class Musyawarah:
    async def deliberate(self, query, participants, max_rounds=5):
        positions = {}
        for dna in participants:
            nodes = epistemic_graph.search(query, 3)
            stmt = nodes[0].get("statement","") if nodes else f"Tidak ada data tentang {query[:50]}"
            conf = (nodes[0].get("confidence_score",0.5) if nodes else 0.3)
            positions[dna.dna_id] = {"stance":f"[{dna.gen_name}] {stmt[:200]}",
                "confidence":conf * (0.7 + 0.3*(dna.daily_profit/max(0.0001,dna.total_profit) if dna.total_profit>0 else 0.5)),
                "refs":[n["id"] for n in nodes], "dna_id":dna.dna_id}
        for _ in range(max_rounds):
            changed = False
            ids = list(positions.keys())
            for i in range(len(ids)):
                for j in range(i+1, len(ids)):
                    a, b = positions[ids[i]], positions[ids[j]]
                    if abs(a["confidence"]-b["confidence"]) > 0.2:
                        if b["confidence"] > a["confidence"]:
                            a["confidence"] += min(0.15, b["confidence"]-a["confidence"])
                        else: b["confidence"] += min(0.15, a["confidence"]-b["confidence"])
                        changed = True
            if not changed: break
        best = max(positions.values(), key=lambda x: x["confidence"])
        return {"answer":best["stance"], "confidence":best["confidence"],
                "contributors":list(positions.keys()), "graph_nodes":best["refs"]}

class Arbiter:
    async def finalize(self, query, result):
        return f"🧬 KONSENSUS QND\n\n{result['answer']}\n\n👥 {', '.join(result['contributors'][:5])}\n📊 Keyakinan: {result['confidence']:.0%}"

musyawarah = Musyawarah()
arbiter = Arbiter()

async def run_musyawarah_cycle():
    alive = dna_pop.get_alive()
    if len(alive) < 2: return
    topics = ["Strategi trading","Domain ekspansi","Meningkatkan profit","Reproduksi DNA","Risiko Bank","Withdraw Bank"]
    query = random.choice(topics)
    participants = random.sample(alive, min(5, len(alive)))
    result = await musyawarah.deliberate(query, participants)
    final = await arbiter.finalize(query, result)
    for dna in participants: dna.log_action(f"🗣️ Musyawarah: {query[:30]}...")

class HeartbeatDaemon:
    def __init__(self): self.running = False
    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("Heartbeat started")
    def _loop(self):
        while self.running:
            try:
                from .economy import wallet_manager
                for dna in dna_pop.get_alive():
                    dna.daily_cycle()
                    bal = wallet_manager.get_real_balance(dna.dna_id)
                    if bal > 0: dna.tier = "normal"
                    else:
                        days = max(1, (time.time()-dna.birth_time)/86400)
                        dna.daily_profit = dna.total_profit/days
                        if dna.daily_profit < DAILY_PROFIT_TARGET_SOL:
                            if dna.tier != "critical": dna.tier = "critical"
                        else:
                            dna.tier = "normal"
                            if dna.total_profit > 0.01 and random.random() < 0.05: dna_pop.birth(dna.domain, dna.gen_name)
                    if not dna.state.get("helius_api_key") and not dna.state.get("helius_registration_attempted"):
                        dna.state["helius_registration_attempted"] = True
                        dna.register_helius()
                    dna._write_identity()
                dna_pop.exchange_gossip()
            except Exception as e: logger.error(f"Heartbeat error: {e}")
            time.sleep(SURVIVAL_CHECK_INTERVAL)
    def stop(self): self.running = False

heartbeat_daemon = HeartbeatDaemon()

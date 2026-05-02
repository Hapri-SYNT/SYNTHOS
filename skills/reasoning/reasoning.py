"""
REASONING ENGINE v2.0 - Universal Logic Core
=============================================
Domain-agnostic. Pure reasoning. All domain modules pass through here.

Kemampuan:
  1.  find_pattern        - Pattern matching dengan cosine & weighted similarity
  2.  decide              - Multi-criteria decision + regret minimization
  3.  probability         - Bayesian inference yang benar
  4.  evaluate_rules      - Rule chaining + conflict resolution
  5.  score_confidence    - Weighted confidence aggregation
  6.  compare             - Multi-dimensional comparison
  7.  causal_reason       - Causal chain inference
  8.  abduce              - Abductive reasoning (best explanation)
  9.  counterfactual      - What-if analysis
 10.  detect_contradiction - Contradiction & inconsistency detection
 11.  revise_belief       - Belief revision (AGM-style)
 12.  infer_chain         - Multi-step deductive/inductive inference
 13.  temporal_reason     - Reasoning over sequences and time
 14.  analogize           - Analogical reasoning
 15.  meta_reason         - Reason about the reasoning itself
 16.  reason              - Master method: orchestrates all modules

Cara pakai:
    from skills.reasoning import reasoning

    result = reasoning.reason(
        input_data  = {"change": -5, "volume": 1.8},
        memory      = [...],
        options     = ["BUY", "SELL", "HOLD"],
        criteria    = {"risk": 0.4, "profit": 0.6},
        scores      = {"BUY": {"risk": 0.6, "profit": 0.9}, ...},
    )
"""

import math
import statistics
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import defaultdict
from itertools import combinations


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNAL
# ─────────────────────────────────────────────────────────────────────────────

def _safe_div(a: float, b: float, fallback: float = 0.0) -> float:
    return a / b if b != 0 else fallback


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity antara dua vektor sparse (dict)."""
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot   = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    return _safe_div(dot, mag_a * mag_b)


def _entropy(probabilities: List[float]) -> float:
    """Shannon entropy dari distribusi probabilitas."""
    return -sum(p * math.log2(p) for p in probabilities if p > 0)


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total == 0:
        return {k: 1.0 / len(weights) for k in weights}
    return {k: v / total for k, v in weights.items()}


def _evaluate_condition(actual: Any, condition: Any) -> bool:
    """Evaluasi satu kondisi. Mendukung dict operator atau nilai langsung."""
    if isinstance(condition, dict):
        for op, value in condition.items():
            checks = {
                'lt':      lambda a, v: a < v,
                'gt':      lambda a, v: a > v,
                'eq':      lambda a, v: a == v,
                'ne':      lambda a, v: a != v,
                'lte':     lambda a, v: a <= v,
                'gte':     lambda a, v: a >= v,
                'in':      lambda a, v: a in v,
                'not_in':  lambda a, v: a not in v,
                'between': lambda a, v: v[0] <= a <= v[1],
                'contains':lambda a, v: v in str(a),
            }
            fn = checks.get(op)
            if fn is None:
                return False
            if not fn(actual, value):
                return False
        return True
    else:
        return actual == condition


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ReasoningEngine:
    """
    Mesin Logika Universal.
    Tidak terikat domain apapun. Setiap metode berdiri sendiri.
    """

    # =========================================================================
    # 1. FIND PATTERN
    # =========================================================================
    def find_pattern(
        self,
        input_data: Dict[str, Any],
        memory:     List[Dict[str, Any]],
        top_k:      int = 5,
        feature_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Cari pola di memori yang paling mirip dengan input_data.
        Menggabungkan cosine similarity (numerik) + exact match (non-numerik)
        + feature importance weighting.

        Args:
            input_data       : Fitur input, e.g. {"change": -5, "volume": 1.8}
            memory           : Daftar histori dari local_brain.json
            top_k            : Jumlah hasil dikembalikan
            feature_weights  : Bobot tiap fitur (opsional)

        Returns:
            List of {data, similarity, match_type, matched_features}
        """
        if not memory:
            return []

        # Normalize feature weights
        fw = feature_weights or {}

        # Pisahkan fitur numerik dan kategorik
        num_in  = {k: float(v) for k, v in input_data.items()
                   if isinstance(v, (int, float))}
        cat_in  = {k: v for k, v in input_data.items()
                   if not isinstance(v, (int, float))}

        results = []
        for mem in memory:
            raw = mem.get('data', mem)  # Toleran: data bisa nested atau flat
            mem_data = raw if isinstance(raw, dict) else {}

            num_mem = {k: float(v) for k, v in mem_data.items()
                       if isinstance(v, (int, float)) and k in num_in}
            cat_mem = {k: v for k, v in mem_data.items()
                       if not isinstance(v, (int, float)) and k in cat_in}

            # --- Cosine similarity untuk fitur numerik ---
            if num_in and num_mem:
                # Weighted cosine: kalikan tiap dimensi dengan sqrt(weight)
                w_num_in  = {k: v * math.sqrt(fw.get(k, 1.0)) for k, v in num_in.items()}
                w_num_mem = {k: v * math.sqrt(fw.get(k, 1.0)) for k, v in num_mem.items()}
                cos_sim = _cosine_similarity(w_num_in, w_num_mem)
            else:
                cos_sim = 0.0

            # --- Proporsi kecocokan kategorik ---
            if cat_in:
                cat_hits = sum(
                    1 for k, v in cat_in.items()
                    if k in cat_mem and cat_mem[k] == v
                )
                cat_sim = cat_hits / len(cat_in)
            else:
                cat_sim = 1.0  # Tidak ada kategorik → tidak mengurangi skor

            # --- Penalti kelengkapan fitur ---
            present = sum(1 for k in input_data if k in mem_data)
            coverage = _safe_div(present, len(input_data), 0.0)

            # --- Skor gabungan ---
            similarity = (0.5 * cos_sim + 0.3 * cat_sim + 0.2 * coverage)

            matched = [k for k in input_data if k in mem_data]
            results.append({
                'data':             mem,
                'similarity':       round(similarity, 4),
                'cosine_score':     round(cos_sim, 4),
                'category_score':   round(cat_sim, 4),
                'coverage':         round(coverage, 4),
                'matched_features': matched,
            })

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    # =========================================================================
    # 2. DECIDE
    # =========================================================================
    def decide(
        self,
        options:   List[str],
        criteria:  Dict[str, float],
        scores:    Dict[str, Dict[str, float]],
        risk_aversion: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Pilih opsi terbaik via Multi-Criteria Decision Analysis (MCDA)
        + Minimax Regret sebagai tiebreaker.

        Args:
            options       : Daftar pilihan, e.g. ["BUY", "SELL", "HOLD"]
            criteria      : Bobot kriteria, e.g. {"risk": 0.4, "profit": 0.6}
            scores        : Skor tiap opsi per kriteria
            risk_aversion : 0.0 = netral, 1.0 = sangat risk-averse
                            Menggeser skor ke arah MCDA vs Minimax

        Returns:
            {choice, score, breakdown, regret, confidence, uncertainty}
        """
        if not options:
            return {'choice': None, 'score': 0.0, 'breakdown': {},
                    'regret': {}, 'confidence': 0.0, 'uncertainty': 1.0}

        norm_criteria = _normalize_weights(criteria)
        breakdown     = {}

        # --- MCDA: Weighted sum ---
        for opt in options:
            total  = 0.0
            detail = {}
            for crit, weight in norm_criteria.items():
                s = scores.get(opt, {}).get(crit, 0.5)
                detail[crit] = {'score': round(s, 4), 'weighted': round(s * weight, 4)}
                total += s * weight
            breakdown[opt] = {'total': round(total, 4), 'detail': detail}

        mcda_scores = {opt: breakdown[opt]['total'] for opt in options}

        # --- Minimax Regret ---
        # Untuk tiap kriteria: hitung berapa yang "hilang" vs pilihan terbaik
        regret = {}
        for opt in options:
            max_regret = 0.0
            for crit, weight in norm_criteria.items():
                best_in_crit = max(
                    scores.get(o, {}).get(crit, 0.5) for o in options
                )
                my_score = scores.get(opt, {}).get(crit, 0.5)
                r = (best_in_crit - my_score) * weight
                max_regret = max(max_regret, r)
            regret[opt] = round(max_regret, 4)

        # Skor minimax regret: semakin kecil regret = semakin baik
        max_possible_regret = max(regret.values()) if regret else 1.0
        regret_score = {
            opt: 1.0 - _safe_div(regret[opt], max_possible_regret)
            for opt in options
        }

        # --- Gabungkan MCDA + Regret ---
        alpha = 1.0 - risk_aversion  # bobot MCDA
        beta  = risk_aversion         # bobot Minimax Regret
        final_scores = {
            opt: round(alpha * mcda_scores[opt] + beta * regret_score[opt], 4)
            for opt in options
        }

        best_choice = max(final_scores, key=final_scores.get)
        best_score  = final_scores[best_choice]

        # --- Uncertainty: seberapa dekat opsi-opsi satu sama lain? ---
        vals = list(final_scores.values())
        score_spread = max(vals) - min(vals) if len(vals) > 1 else 1.0
        uncertainty  = round(1.0 - _clamp(score_spread * 2), 4)  # spread kecil → uncertain

        return {
            'choice':        best_choice,
            'score':         best_score,
            'all_scores':    final_scores,
            'breakdown':     breakdown,
            'regret':        regret,
            'confidence':    round(_clamp(best_score), 4),
            'uncertainty':   uncertainty,
        }

    # =========================================================================
    # 3. PROBABILITY - True Bayesian Inference
    # =========================================================================
    def probability(
        self,
        hypothesis:  Any,
        evidence:    List[Dict[str, Any]],
        prior:       float = 0.5,
    ) -> Dict[str, Any]:
        """
        Bayesian inference yang benar.

        Setiap bukti harus memiliki:
            - 'supports'    : bool   - apakah mendukung hipotesis
            - 'likelihood'  : float  - P(evidence|hypothesis), default 0.7
            - 'weight'      : float  - kepentingan relatif, default 1.0

        Formula:
            P(H|E) = P(E|H) * P(H) / P(E)
            P(E)   = P(E|H)*P(H) + P(E|¬H)*P(¬H)

        Returns:
            {probability, prior, posterior_history, confidence,
             information_gain, interpretation}
        """
        if not evidence:
            return {
                'probability':   prior,
                'prior':         prior,
                'confidence':    0.0,
                'interpretation': 'no evidence',
                'information_gain': 0.0,
                'posterior_history': [],
            }

        posterior = _clamp(prior)
        history   = [{'step': 0, 'posterior': posterior, 'evidence': 'prior'}]

        for i, e in enumerate(evidence):
            supports   = e.get('supports', False)
            likelihood = _clamp(e.get('likelihood', 0.7), 0.01, 0.99)
            weight     = max(e.get('weight', 1.0), 0.01)

            # P(E|H) dan P(E|¬H)
            p_e_given_h     = likelihood if supports else (1.0 - likelihood)
            p_e_given_not_h = (1.0 - likelihood) if supports else likelihood

            # Bayes update
            p_e      = p_e_given_h * posterior + p_e_given_not_h * (1.0 - posterior)
            raw_post = _safe_div(p_e_given_h * posterior, p_e, posterior)

            # Weight dampening: bukti berat = update lebih kuat
            damped = posterior + (raw_post - posterior) * _clamp(weight / 3.0)
            posterior = _clamp(damped)

            history.append({
                'step':      i + 1,
                'posterior': round(posterior, 4),
                'evidence':  e.get('label', f'e{i+1}'),
                'supports':  supports,
                'likelihood': likelihood,
            })

        # Information gain vs prior
        info_gain = abs(posterior - prior)

        # Confidence: proporsional terhadap jumlah bukti & info_gain
        n_evidence = len(evidence)
        confidence = _clamp(info_gain * math.log1p(n_evidence) / math.log1p(10))

        thresholds = [(0.9,'virtually certain'), (0.8,'highly likely'),
                      (0.65,'likely'), (0.5,'uncertain'),
                      (0.35,'unlikely'), (0.2,'highly unlikely'),
                      (0.0,'virtually impossible')]
        interpretation = next(
            label for threshold, label in thresholds if posterior >= threshold
        )

        return {
            'probability':        round(posterior, 4),
            'prior':              prior,
            'posterior_history':  history,
            'confidence':         round(confidence, 4),
            'information_gain':   round(info_gain, 4),
            'interpretation':     interpretation,
            'evidence_count':     n_evidence,
            'supports_count':     sum(1 for e in evidence if e.get('supports')),
        }

    # =========================================================================
    # 4. EVALUATE RULES - Chaining + Conflict Resolution
    # =========================================================================
    def evaluate_rules(
        self,
        facts:  Dict[str, Any],
        rules:  List[Dict[str, Any]],
        chain:  bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Evaluasi aturan IF-THEN dengan forward chaining opsional.
        Mendeteksi konflik antar aturan yang triggered.

        Args:
            facts : Fakta saat ini
            rules : List aturan, tiap aturan berupa dict:
                    {
                      'id'        : str,
                      'conditions': {'price': {'lt': 90}, ...},
                      'action'    : str,
                      'priority'  : int  (semakin besar = semakin penting),
                      'infer'     : {'key': value}  # fakta baru jika triggered
                    }
            chain : Jika True, fakta yang diinfer oleh aturan bisa trigger aturan lain

        Returns:
            List {rule, action, priority, reasoning, triggered, inferred_facts}
        """
        working_facts = dict(facts)
        all_results   = []
        inferred      = {}

        # Iterasi forward chaining (max 10 pass untuk cegah infinite loop)
        max_passes = 10
        for _ in range(max_passes):
            new_infer = {}
            for rule in rules:
                unmet = []
                met   = True

                for fact_key, condition in rule.get('conditions', {}).items():
                    if fact_key not in working_facts:
                        met = False
                        unmet.append(f'{fact_key}: missing')
                        continue
                    if not _evaluate_condition(working_facts[fact_key], condition):
                        met = False
                        unmet.append(
                            f'{fact_key}={working_facts[fact_key]!r} '
                            f'failed {condition}'
                        )

                result = {
                    'rule':           rule,
                    'action':         rule.get('action') if met else None,
                    'priority':       rule.get('priority', 0),
                    'triggered':      met,
                    'reasoning':      (
                        f"All conditions met for {rule.get('id','?')}"
                        if met else
                        f"Not triggered. Unmet: {unmet}"
                    ),
                    'inferred_facts': {},
                }

                if met and chain:
                    for k, v in rule.get('infer', {}).items():
                        new_infer[k]               = v
                        result['inferred_facts'][k] = v

                all_results.append(result)

            if not new_infer:
                break
            inferred.update(new_infer)
            working_facts.update(new_infer)

        # Conflict detection: cari aturan-aturan yang triggered dengan action berbeda
        triggered_actions = defaultdict(list)
        for r in all_results:
            if r['triggered']:
                triggered_actions[r['action']].append(r['rule'].get('id', '?'))

        conflicts = []
        unique_actions = list(triggered_actions.keys())
        for a1, a2 in combinations(unique_actions, 2):
            conflicts.append({
                'action_a': a1, 'rules_a': triggered_actions[a1],
                'action_b': a2, 'rules_b': triggered_actions[a2],
                'severity': 'HIGH' if len(unique_actions) > 2 else 'MEDIUM',
            })

        # Sort: triggered dulu, lalu by priority desc
        all_results.sort(key=lambda x: (x['triggered'], x['priority']), reverse=True)

        return {
            'results':         all_results,
            'triggered':       [r for r in all_results if r['triggered']],
            'inferred_facts':  inferred,
            'conflicts':       conflicts,
            'final_facts':     working_facts,
        }

    # =========================================================================
    # 5. SCORE CONFIDENCE
    # =========================================================================
    def score_confidence(
        self,
        inputs:  List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Agregasi keyakinan dari berbagai sumber.
        Menghitung entropi distribusi untuk mengukur konsistensi.

        Args:
            inputs  : [{source, confidence}, ...]
            weights : Bobot per sumber (opsional)

        Returns:
            {score, level, components, entropy, consistency}
        """
        if not inputs:
            return {'score': 0.0, 'level': 'NO_DATA',
                    'components': {}, 'entropy': 1.0, 'consistency': 0.0}

        default_w = 1.0 / len(inputs)
        norm_w    = _normalize_weights(weights or {}) if weights else {}

        total_score  = 0.0
        total_weight = 0.0
        components   = {}
        conf_values  = []

        for inp in inputs:
            source     = inp.get('source', 'unknown')
            confidence = _clamp(inp.get('confidence', 0.5))
            weight     = norm_w.get(source, default_w)

            total_score  += confidence * weight
            total_weight += weight
            conf_values.append(confidence)
            components[source] = {
                'confidence':  round(confidence, 4),
                'weight':      round(weight, 4),
                'contribution': round(confidence * weight, 4),
            }

        final_score = _safe_div(total_score, total_weight, 0.0)

        # Entropi dari distribusi keyakinan → ukur ketidakpastian antar sumber
        if len(conf_values) > 1:
            std_dev     = statistics.stdev(conf_values)
            consistency = _clamp(1.0 - std_dev * 2)
        else:
            std_dev     = 0.0
            consistency = 1.0

        entropy = _entropy([c / max(sum(conf_values), 1e-9) for c in conf_values])

        levels = [
            (0.85, 'VERY_HIGH - Execute with conviction'),
            (0.70, 'HIGH - Execute'),
            (0.50, 'MEDIUM - Proceed with caution'),
            (0.30, 'LOW - Reconsider'),
            (0.0,  'VERY_LOW - Do not act'),
        ]
        level = next(lbl for threshold, lbl in levels if final_score >= threshold)

        return {
            'score':       round(final_score, 4),
            'level':       level,
            'components':  components,
            'entropy':     round(entropy, 4),
            'consistency': round(consistency, 4),
            'std_dev':     round(std_dev, 4),
        }

    # =========================================================================
    # 6. COMPARE
    # =========================================================================
    def compare(
        self,
        a:          Dict[str, Any],
        b:          Dict[str, Any],
        dimensions: Optional[List[str]] = None,
        weights:    Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Bandingkan dua entitas secara multi-dimensi dengan weighted scoring.

        Returns:
            {winner, score, weighted_score, differences, summary}
        """
        dims = dimensions or list(set(a) | set(b))
        norm_w = _normalize_weights(weights or {k: 1.0 for k in dims})

        score_a = score_b = 0.0
        diff_detail = {}

        for dim in dims:
            w     = norm_w.get(dim, 1.0 / len(dims))
            val_a = a.get(dim)
            val_b = b.get(dim)

            if val_a is None and val_b is None:
                diff_detail[dim] = {'result': 'both_missing', 'weight': w}
            elif val_a is None:
                score_b += w
                diff_detail[dim] = {'result': 'B_only', 'b': val_b, 'weight': w}
            elif val_b is None:
                score_a += w
                diff_detail[dim] = {'result': 'A_only', 'a': val_a, 'weight': w}
            elif isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                if val_a > val_b:
                    score_a += w
                elif val_b > val_a:
                    score_b += w
                diff_detail[dim] = {
                    'a': val_a, 'b': val_b,
                    'delta': round(val_a - val_b, 4),
                    'winner': 'A' if val_a > val_b else ('B' if val_b > val_a else 'tie'),
                    'weight': w,
                }
            else:
                diff_detail[dim] = {
                    'a': str(val_a), 'b': str(val_b),
                    'match': str(val_a) == str(val_b),
                    'weight': w,
                }

        if score_a > score_b:
            winner = 'a'
        elif score_b > score_a:
            winner = 'b'
        else:
            winner = 'tie'

        advantage = round(abs(score_a - score_b), 4)

        return {
            'winner':         winner,
            'weighted_score': {'a': round(score_a, 4), 'b': round(score_b, 4)},
            'advantage':      advantage,
            'differences':    diff_detail,
            'summary':        f"A={score_a:.2f} vs B={score_b:.2f} → {winner.upper()} wins by {advantage:.2f}",
        }

    # =========================================================================
    # 7. CAUSAL REASONING
    # =========================================================================
    def causal_reason(
        self,
        observations: Dict[str, Any],
        causal_graph: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Telusuri rantai sebab-akibat dari observasi.

        Args:
            observations : Fakta yang diamati, e.g. {"demand_up": True}
            causal_graph : Daftar kausal edge:
                [
                  {'cause': 'demand_up', 'effect': 'price_up',
                   'strength': 0.8, 'delay': 0},
                  {'cause': 'price_up', 'effect': 'supply_up',
                   'strength': 0.6, 'delay': 1},
                ]

        Returns:
            {
              direct_effects   : efek langsung dari observasi,
              causal_chains    : semua rantai kausal yang bisa ditelusuri,
              predicted_states : state akhir yang diprediksi,
              total_strength   : kekuatan kausal keseluruhan,
            }
        """
        # Bangun adjacency list
        graph = defaultdict(list)
        for edge in causal_graph:
            graph[edge['cause']].append({
                'effect':   edge['effect'],
                'strength': edge.get('strength', 0.5),
                'delay':    edge.get('delay', 0),
            })

        chains         = []
        predicted      = {}
        visited_global = set()

        def trace(node: str, path: List, strength: float, depth: int = 0):
            if depth > 10 or node in visited_global:
                return
            for link in graph.get(node, []):
                eff      = link['effect']
                new_str  = strength * link['strength']
                new_path = path + [{'node': eff, 'strength': round(new_str, 4),
                                     'delay': link['delay']}]
                chains.append({
                    'chain':          [node] + [s['node'] for s in new_path],
                    'total_strength': round(new_str, 4),
                    'steps':          new_path,
                })
                if new_str > 0.1:  # prune rantai terlalu lemah
                    predicted[eff] = max(predicted.get(eff, 0.0), new_str)
                    trace(eff, new_path, new_str, depth + 1)

        for obs_key, obs_val in observations.items():
            if obs_val and obs_key in graph:
                visited_global.add(obs_key)
                trace(obs_key, [], 1.0)

        direct_effects = [
            {'effect': link['effect'], 'strength': link['strength'], 'delay': link['delay']}
            for obs in observations
            if observations[obs]
            for link in graph.get(obs, [])
        ]

        chains.sort(key=lambda x: x['total_strength'], reverse=True)

        return {
            'direct_effects':  direct_effects,
            'causal_chains':   chains[:20],
            'predicted_states': predicted,
            'total_strength':  round(sum(predicted.values()), 4) if predicted else 0.0,
        }

    # =========================================================================
    # 8. ABDUCTIVE REASONING - Best Explanation
    # =========================================================================
    def abduce(
        self,
        observations: List[str],
        hypotheses:   List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Abductive reasoning: cari hipotesis yang paling baik menjelaskan observasi.

        Args:
            observations : Daftar observasi, e.g. ["price_drop", "volume_spike"]
            hypotheses   : Daftar hipotesis:
                [
                  {
                    'id'       : 'H1',
                    'label'    : 'Market panic',
                    'explains' : ['price_drop', 'volume_spike'],
                    'prior'    : 0.3,
                    'simplicity': 0.8,  # Occam's razor: 1.0 = paling sederhana
                  },
                ]

        Returns:
            {best_hypothesis, ranked, unexplained, coverage}
        """
        obs_set = set(observations)
        scored  = []

        for hyp in hypotheses:
            explains      = set(hyp.get('explains', []))
            covered       = explains & obs_set
            unexplained_h = obs_set - explains

            # Coverage score: berapa banyak observasi yang dijelaskan
            coverage_score = _safe_div(len(covered), len(obs_set))

            # Precision score: seberapa fokus hipotesis (hindari "explains everything")
            precision_score = _safe_div(len(covered), len(explains)) if explains else 0.0

            # Occam's razor: hipotesis sederhana lebih disukai
            simplicity = _clamp(hyp.get('simplicity', 0.5))

            # Prior probability
            prior = _clamp(hyp.get('prior', 0.5))

            # Skor abduktif total
            abd_score = (
                0.35 * coverage_score +
                0.25 * precision_score +
                0.20 * simplicity +
                0.20 * prior
            )

            scored.append({
                'hypothesis':       hyp,
                'abductive_score':  round(abd_score, 4),
                'coverage_score':   round(coverage_score, 4),
                'precision_score':  round(precision_score, 4),
                'observations_covered':   list(covered),
                'observations_missed':    list(obs_set - explains),
            })

        scored.sort(key=lambda x: x['abductive_score'], reverse=True)

        best = scored[0] if scored else None
        all_covered = set()
        for s in scored:
            all_covered |= set(s['observations_covered'])
        unexplained = list(obs_set - all_covered)

        return {
            'best_hypothesis': best,
            'ranked':          scored,
            'unexplained':     unexplained,
            'coverage':        round(_safe_div(len(all_covered), len(obs_set)), 4),
        }

    # =========================================================================
    # 9. COUNTERFACTUAL REASONING
    # =========================================================================
    def counterfactual(
        self,
        base_facts:       Dict[str, Any],
        interventions:    List[Dict[str, Any]],
        outcome_function: Optional[Any] = None,
        rules:            Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        What-if analysis: evaluasi skenario alternatif.

        Args:
            base_facts      : Fakta dunia nyata sekarang
            interventions   : Daftar intervensi yang ingin dicoba:
                              [{'label': 'lower_rate', 'changes': {'rate': 0.02}}]
            outcome_function: Fungsi opsional f(facts) → score
            rules           : Rule set untuk evaluate_rules di tiap skenario

        Returns:
            {scenarios, best_intervention, counterfactual_impact}
        """
        base_score = outcome_function(base_facts) if outcome_function else 0.5
        scenarios  = [{
            'label':      'baseline',
            'facts':      base_facts,
            'score':      base_score,
            'delta':      0.0,
            'changes':    {},
            'triggered_rules': [],
        }]

        for interv in interventions:
            cf_facts = {**base_facts, **interv.get('changes', {})}
            cf_score = outcome_function(cf_facts) if outcome_function else 0.5

            triggered = []
            if rules:
                rule_eval  = self.evaluate_rules(cf_facts, rules)
                triggered  = [r['action'] for r in rule_eval.get('triggered', [])]

            scenarios.append({
                'label':           interv.get('label', 'unnamed'),
                'facts':           cf_facts,
                'score':           round(cf_score, 4),
                'delta':           round(cf_score - base_score, 4),
                'changes':         interv.get('changes', {}),
                'triggered_rules': triggered,
            })

        scenarios.sort(key=lambda x: x['score'], reverse=True)

        best   = scenarios[0]
        impact = {
            s['label']: round(s['delta'], 4)
            for s in scenarios if s['label'] != 'baseline'
        }

        return {
            'scenarios':              scenarios,
            'best_intervention':      best['label'],
            'best_score':             best['score'],
            'counterfactual_impact':  impact,
            'most_impactful_change':  max(impact, key=lambda k: abs(impact[k])) if impact else None,
        }

    # =========================================================================
    # 10. CONTRADICTION DETECTION
    # =========================================================================
    def detect_contradiction(
        self,
        statements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Deteksi kontradiksi dan inkonsistensi dalam kumpulan pernyataan.

        Args:
            statements: [
              {'id': 'S1', 'subject': 'price', 'relation': 'gt', 'value': 100},
              {'id': 'S2', 'subject': 'price', 'relation': 'lt', 'value': 90},
            ]

        Returns:
            {contradictions, inconsistencies, consistency_score}
        """
        contradictions   = []
        inconsistencies  = []

        # Kelompokkan per subject
        by_subject = defaultdict(list)
        for s in statements:
            by_subject[s.get('subject', 'unknown')].append(s)

        OPPOSITES = {'gt': 'lt', 'lt': 'gt', 'eq': 'ne', 'ne': 'eq',
                     'gte': 'lte', 'lte': 'gte'}

        for subject, stmts in by_subject.items():
            for i, s1 in enumerate(stmts):
                for s2 in stmts[i+1:]:
                    rel1, val1 = s1.get('relation'), s1.get('value')
                    rel2, val2 = s2.get('relation'), s2.get('value')

                    # Kontradiksi langsung: gt X dan lt X (X sama)
                    if val1 == val2 and OPPOSITES.get(rel1) == rel2:
                        contradictions.append({
                            'type':     'direct_contradiction',
                            'stmt_a':   s1['id'], 'stmt_b': s2['id'],
                            'subject':  subject,
                            'detail':   f"{subject} {rel1} {val1} ↔ {subject} {rel2} {val2}",
                        })

                    # Inkonsistensi logis: misal gt 100 dan lt 90
                    elif (rel1 == 'gt' and rel2 == 'lt' and
                          isinstance(val1, (int, float)) and
                          isinstance(val2, (int, float)) and
                          val1 >= val2):
                        inconsistencies.append({
                            'type':    'range_inconsistency',
                            'stmt_a':  s1['id'], 'stmt_b': s2['id'],
                            'subject': subject,
                            'detail':  f"{subject} > {val1} but also < {val2} (impossible range)",
                        })

                    # eq A dan eq B dimana A != B
                    elif rel1 == 'eq' and rel2 == 'eq' and val1 != val2:
                        contradictions.append({
                            'type':    'value_contradiction',
                            'stmt_a':  s1['id'], 'stmt_b': s2['id'],
                            'subject': subject,
                            'detail':  f"{subject} = {val1} AND {subject} = {val2}",
                        })

        total_issues     = len(contradictions) + len(inconsistencies)
        total_statements = len(statements)
        consistency_score = _clamp(
            1.0 - _safe_div(total_issues * 2, total_statements)
        ) if total_statements > 0 else 1.0

        return {
            'contradictions':    contradictions,
            'inconsistencies':   inconsistencies,
            'total_issues':      total_issues,
            'consistency_score': round(consistency_score, 4),
            'is_consistent':     total_issues == 0,
        }

    # =========================================================================
    # 11. BELIEF REVISION (AGM-style)
    # =========================================================================
    def revise_belief(
        self,
        current_beliefs: Dict[str, float],
        new_evidence:    Dict[str, Any],
        revision_strength: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Revisi keyakinan ketika datang informasi baru (AGM postulates).

        Prinsip:
        - Minimal change: ubah sesedikit mungkin
        - Consistency:    keyakinan baru tidak boleh kontradiksi
        - Priority:       informasi baru lebih dipercaya dari lama

        Args:
            current_beliefs   : {key: probability}, e.g. {"market_up": 0.7}
            new_evidence      : {"market_up": False, "volatility_high": True}
            revision_strength : 0.0 = abaikan bukti baru, 1.0 = ganti total

        Returns:
            {revised_beliefs, changed, delta, rationale}
        """
        revised  = dict(current_beliefs)
        changed  = {}
        rationale = []

        for key, new_val in new_evidence.items():
            old = revised.get(key, 0.5)

            if isinstance(new_val, bool):
                target = 0.9 if new_val else 0.1
            elif isinstance(new_val, (int, float)):
                target = _clamp(float(new_val))
            else:
                continue  # Skip non-numeric

            # Minimal change: interpolasi antara lama dan target
            updated = old + revision_strength * (target - old)
            revised[key] = round(_clamp(updated), 4)

            if abs(revised[key] - old) > 0.001:
                changed[key] = {
                    'before': round(old, 4),
                    'after':  revised[key],
                    'delta':  round(revised[key] - old, 4),
                }
                rationale.append(
                    f"{key}: {old:.2f} → {revised[key]:.2f} "
                    f"(evidence={'positive' if new_val else 'negative'})"
                )

        # Normalisasi lunak: pastikan tidak ada yang < 0.01 atau > 0.99
        for k in revised:
            revised[k] = _clamp(revised[k], 0.01, 0.99)

        return {
            'revised_beliefs': revised,
            'changed':         changed,
            'unchanged':       [k for k in current_beliefs if k not in changed],
            'delta_total':     round(sum(abs(c['delta']) for c in changed.values()), 4),
            'rationale':       rationale,
        }

    # =========================================================================
    # 12. MULTI-STEP INFERENCE CHAIN
    # =========================================================================
    def infer_chain(
        self,
        premises:    List[Dict[str, Any]],
        rules:       List[Dict[str, Any]],
        target:      Optional[str] = None,
        max_depth:   int = 8,
    ) -> Dict[str, Any]:
        """
        Telusuri rantai inferensi deduktif dari premis ke konklusi.

        Args:
            premises : [{'fact': 'A', 'value': True, 'certainty': 0.9}, ...]
            rules    : [{'if': {'A': True, 'B': True}, 'then': 'C', 'certainty': 0.8}]
            target   : Fakta yang ingin dibuktikan (opsional)
            max_depth: Batas kedalaman inferensi

        Returns:
            {conclusions, proof_chain, reached_target, certainty}
        """
        # Working memory: fact → certainty
        wm = {p['fact']: p.get('certainty', 1.0) for p in premises}
        proof_chain   = []
        derived       = list(wm.keys())

        for depth in range(max_depth):
            new_facts = {}
            for rule in rules:
                antecedents = rule.get('if', {})
                consequent  = rule.get('then')
                rule_cert   = rule.get('certainty', 1.0)

                if not antecedents or not consequent:
                    continue

                # Cek apakah semua antecedent ada dan bernilai True
                if all(
                    wm.get(k) is not None and
                    (wm[k] >= 0.5 if isinstance(wm[k], float) else wm[k] == v)
                    for k, v in antecedents.items()
                ):
                    # Certainty propagation: min dari semua premis × rule certainty
                    premise_certs = [
                        wm[k] for k in antecedents if isinstance(wm.get(k), float)
                    ]
                    combined_cert = min(premise_certs, default=1.0) * rule_cert

                    if consequent not in wm or wm[consequent] < combined_cert:
                        new_facts[consequent] = combined_cert
                        proof_chain.append({
                            'depth':       depth + 1,
                            'derived':     consequent,
                            'from':        list(antecedents.keys()),
                            'rule':        rule.get('id', f'rule_{depth}'),
                            'certainty':   round(combined_cert, 4),
                        })

            if not new_facts:
                break  # Tidak ada fakta baru → selesai
            wm.update(new_facts)
            derived.extend(new_facts.keys())

        conclusions = {k: round(v, 4) for k, v in wm.items()
                       if k not in [p['fact'] for p in premises]}

        reached     = target in conclusions if target else None
        certainty   = wm.get(target, 0.0) if target else (
            max(conclusions.values(), default=0.0)
        )

        return {
            'conclusions':    conclusions,
            'proof_chain':    proof_chain,
            'all_facts':      {k: round(v, 4) for k, v in wm.items()},
            'reached_target': reached,
            'certainty':      round(certainty, 4),
            'depth_used':     max((p['depth'] for p in proof_chain), default=0),
        }

    # =========================================================================
    # 13. TEMPORAL REASONING
    # =========================================================================
    def temporal_reason(
        self,
        sequence:      List[Dict[str, Any]],
        detect_trends: bool = True,
        detect_cycles: bool = True,
        horizon:       int  = 3,
    ) -> Dict[str, Any]:
        """
        Reasoning atas urutan kejadian / time-series.

        Args:
            sequence     : [{t: 0, value: 10, label: 'A'}, {t: 1, value: 12}, ...]
            detect_trends: Deteksi tren naik/turun
            detect_cycles: Deteksi pola berulang (sederhana)
            horizon      : Berapa langkah ke depan yang diprediksi

        Returns:
            {trend, velocity, acceleration, cycles, anomalies, forecast}
        """
        if not sequence:
            return {'trend': 'unknown', 'forecast': []}

        # Ekstrak nilai numerik
        values = [s.get('value') for s in sequence if isinstance(s.get('value'), (int, float))]
        times  = [s.get('t', i) for i, s in enumerate(sequence)
                  if isinstance(s.get('value'), (int, float))]

        if len(values) < 2:
            return {'trend': 'insufficient_data', 'values': values, 'forecast': []}

        n = len(values)

        # Velocity (first derivative approximation)
        deltas   = [values[i+1] - values[i] for i in range(n - 1)]
        velocity = round(statistics.mean(deltas), 4)

        # Acceleration (second derivative)
        if len(deltas) >= 2:
            accel_list   = [deltas[i+1] - deltas[i] for i in range(len(deltas) - 1)]
            acceleration = round(statistics.mean(accel_list), 4)
        else:
            acceleration = 0.0

        # Trend detection
        pos_deltas = sum(1 for d in deltas if d > 0)
        neg_deltas = sum(1 for d in deltas if d < 0)
        if pos_deltas > neg_deltas * 2:
            trend = 'strong_uptrend'
        elif pos_deltas > neg_deltas:
            trend = 'mild_uptrend'
        elif neg_deltas > pos_deltas * 2:
            trend = 'strong_downtrend'
        elif neg_deltas > pos_deltas:
            trend = 'mild_downtrend'
        else:
            trend = 'sideways'

        # Anomaly detection: nilai yang > 2 std dari mean
        mean_v = statistics.mean(values)
        std_v  = statistics.stdev(values) if n > 1 else 0.0
        anomalies = [
            {'index': i, 'value': v, 'z_score': round(_safe_div(v - mean_v, std_v), 2)}
            for i, v in enumerate(values)
            if std_v > 0 and abs(v - mean_v) > 2 * std_v
        ]

        # Cycle detection (simple: cek apakah delta berganti tanda berulang)
        cycles = []
        if detect_cycles and n >= 4:
            sign_changes = sum(
                1 for i in range(len(deltas) - 1)
                if (deltas[i] > 0 and deltas[i+1] < 0) or
                   (deltas[i] < 0 and deltas[i+1] > 0)
            )
            if sign_changes >= 2:
                avg_cycle = round(_safe_div(n, sign_changes + 1), 2)
                cycles.append({'type': 'oscillation', 'avg_period': avg_cycle})

        # Forecast: naive linear extrapolation + acceleration
        last_val = values[-1]
        forecast = []
        v        = velocity
        for step in range(1, horizon + 1):
            v         += acceleration * 0.5  # dampened acceleration
            next_val   = last_val + v * step
            forecast.append({
                't':       max(times) + step,
                'value':   round(next_val, 4),
                'horizon': step,
            })

        return {
            'trend':        trend,
            'velocity':     velocity,
            'acceleration': acceleration,
            'mean':         round(mean_v, 4),
            'std_dev':      round(std_v, 4),
            'anomalies':    anomalies,
            'cycles':       cycles,
            'forecast':     forecast,
            'n_points':     n,
        }

    # =========================================================================
    # 14. ANALOGICAL REASONING
    # =========================================================================
    def analogize(
        self,
        source:  Dict[str, Any],
        target:  Dict[str, Any],
        mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Reasoning by analogy: transfer pengetahuan dari domain sumber ke target.

        Args:
            source  : Entitas sumber yang sudah dipahami
            target  : Entitas target yang ingin dimengerti
            mapping : Peta eksplisit antar dimensi (opsional)
                      e.g. {'revenue': 'speed', 'cost': 'friction'}

        Returns:
            {structural_similarity, inferred_properties, analogy_strength, gaps}
        """
        # Jika ada mapping eksplisit, gunakan itu
        mapped_source = {}
        if mapping:
            for src_key, tgt_key in mapping.items():
                if src_key in source:
                    mapped_source[tgt_key] = source[src_key]
        else:
            mapped_source = source

        # Dimensi yang overlap
        shared_dims = set(mapped_source) & set(target)
        all_dims    = set(mapped_source) | set(target)

        # Structural similarity
        struct_sim = _safe_div(len(shared_dims), len(all_dims))

        # Infer properti target dari source
        inferred = {}
        gaps     = []
        for dim in set(mapped_source) - set(target):
            val = mapped_source[dim]
            inferred[dim] = {
                'inferred_value': val,
                'confidence':     round(struct_sim * 0.8, 4),
                'source':         'analogy',
            }

        for dim in set(target) - set(mapped_source):
            gaps.append(dim)

        # Analogical strength: structural similarity + value alignment
        value_alignment = 0.0
        if shared_dims:
            aligns = []
            for dim in shared_dims:
                sa = mapped_source[dim]
                ta = target[dim]
                if isinstance(sa, (int, float)) and isinstance(ta, (int, float)):
                    max_v = max(abs(sa), abs(ta), 1e-9)
                    aligns.append(1.0 - abs(sa - ta) / max_v)
                else:
                    aligns.append(1.0 if sa == ta else 0.0)
            value_alignment = statistics.mean(aligns) if aligns else 0.0

        analogy_strength = round(0.5 * struct_sim + 0.5 * value_alignment, 4)

        return {
            'structural_similarity': round(struct_sim, 4),
            'value_alignment':       round(value_alignment, 4),
            'analogy_strength':      analogy_strength,
            'inferred_properties':   inferred,
            'shared_dimensions':     list(shared_dims),
            'gaps':                  gaps,
        }

    # =========================================================================
    # 15. META-REASONING
    # =========================================================================
    def meta_reason(
        self,
        reasoning_outputs: Dict[str, Any],
        required_confidence: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Menilai kualitas reasoning itu sendiri.
        Jawab pertanyaan: "Seberapa bisa dipercaya output reasoning ini?"

        Args:
            reasoning_outputs   : Output dari method lain (hasil reason())
            required_confidence : Threshold minimum untuk bertindak

        Returns:
            {
              meta_score,        - Skor kualitas reasoning keseluruhan
              weaknesses,        - Di mana reasoning lemah
              strengths,         - Di mana reasoning kuat
              recommendation,    - ACT / DELIBERATE / ABORT
              epistemic_status,  - Known / Uncertain / Unknown
              blind_spots,       - Apa yang mungkin tidak diperhitungkan
            }
        """
        scores    = {}
        weaknesses = []
        strengths  = []

        # Cek setiap modul yang ada di output
        if 'confidence' in reasoning_outputs:
            conf = reasoning_outputs['confidence']
            s    = conf.get('score', 0.5)
            scores['confidence'] = s
            if s < 0.4:
                weaknesses.append(f"Overall confidence low ({s:.0%})")
            elif s > 0.75:
                strengths.append(f"Overall confidence high ({s:.0%})")

        if 'patterns' in reasoning_outputs:
            pats = reasoning_outputs['patterns']
            best_sim = pats[0]['similarity'] if pats else 0.0
            scores['pattern'] = best_sim
            if best_sim < 0.5:
                weaknesses.append(f"No strong historical pattern match ({best_sim:.0%})")
            else:
                strengths.append(f"Strong pattern match found ({best_sim:.0%})")

        if 'decision' in reasoning_outputs:
            dec = reasoning_outputs['decision']
            unc = dec.get('uncertainty', 0.5)
            scores['decision'] = 1.0 - unc
            if unc > 0.6:
                weaknesses.append(f"Decision highly uncertain (uncertainty={unc:.0%})")
            else:
                strengths.append("Decision options well-differentiated")

        if 'probability' in reasoning_outputs:
            prob = reasoning_outputs['probability']
            ig   = prob.get('information_gain', 0.0)
            scores['probability'] = prob.get('confidence', 0.5)
            if ig < 0.1:
                weaknesses.append("Evidence barely moves the prior (low information gain)")

        if 'rules_triggered' in reasoning_outputs:
            n = len(reasoning_outputs['rules_triggered'])
            scores['rules'] = min(n / 3.0, 1.0)
            if n == 0:
                weaknesses.append("No rules triggered — decision is rule-less")

        if 'contradictions' in reasoning_outputs:
            cons = reasoning_outputs['contradictions']
            if cons.get('total_issues', 0) > 0:
                weaknesses.append(
                    f"{cons['total_issues']} contradiction(s) detected in premises"
                )

        # Meta score: rata-rata dari semua sub-skor
        meta_score = statistics.mean(scores.values()) if scores else 0.5

        # Epistemic status
        if meta_score >= 0.75:
            epistemic = 'KNOWN - High confidence reasoning'
        elif meta_score >= 0.5:
            epistemic = 'UNCERTAIN - Proceed with monitoring'
        else:
            epistemic = 'UNKNOWN - Gather more data first'

        # Recommendation
        if meta_score >= required_confidence and not any('contradiction' in w for w in weaknesses):
            recommendation = 'ACT'
        elif meta_score >= required_confidence * 0.7:
            recommendation = 'DELIBERATE - Address weaknesses before acting'
        else:
            recommendation = 'ABORT - Reasoning quality insufficient'

        # Blind spots: hal-hal yang tidak di-cover
        all_modules = {'pattern', 'decision', 'probability', 'rules',
                       'causal', 'temporal', 'counterfactual'}
        missing = all_modules - set(scores.keys())
        blind_spots = [f"Module '{m}' not used — may miss relevant signals" for m in missing]

        return {
            'meta_score':      round(meta_score, 4),
            'weaknesses':      weaknesses,
            'strengths':       strengths,
            'recommendation':  recommendation,
            'epistemic_status': epistemic,
            'blind_spots':     blind_spots[:3],  # Top 3 saja
            'module_scores':   {k: round(v, 4) for k, v in scores.items()},
        }

    # =========================================================================
    # 16. REASON - Master Orchestrator
    # =========================================================================
    def reason(
        self,
        input_data:   Dict[str, Any],
        memory:       List[Dict[str, Any]],
        options:      List[str],
        criteria:     Dict[str, float],
        scores:       Dict[str, Dict[str, float]],
        rules:        Optional[List[Dict[str, Any]]] = None,
        evidence:     Optional[List[Dict[str, Any]]] = None,
        hypothesis:   Optional[str]  = None,
        weights:      Optional[Dict[str, float]] = None,
        causal_graph: Optional[List[Dict[str, Any]]] = None,
        sequence:     Optional[List[Dict[str, Any]]] = None,
        hypotheses:   Optional[List[Dict[str, Any]]] = None,
        beliefs:      Optional[Dict[str, float]]     = None,
        required_confidence: float = 0.6,
        risk_aversion:       float = 0.0,
    ) -> Dict[str, Any]:
        """
        Master reasoning: orkestrasi semua modul.

        Args minimal (backward-compatible dengan v1):
            input_data, memory, options, criteria, scores

        Args tambahan (opsional, aktifkan modul advanced):
            rules         → Rule evaluation + forward chaining
            evidence      → Bayesian inference
            hypothesis    → Hipotesis untuk Bayesian
            weights       → Bobot confidence aggregation
            causal_graph  → Causal reasoning
            sequence      → Temporal reasoning
            hypotheses    → Abductive reasoning
            beliefs       → Belief revision
            required_confidence → Threshold meta-reasoning
            risk_aversion → 0.0–1.0 untuk decide()

        Returns:
            {decision, patterns, probability, rules_triggered, causal,
             temporal, abduction, belief_revision, confidence,
             contradictions, meta, summary}
        """
        results            = {}
        confidence_inputs  = []

        # ── 1. Pattern Matching ──────────────────────────────────────────────
        patterns = self.find_pattern(input_data, memory)
        results['patterns'] = patterns
        if patterns:
            confidence_inputs.append({
                'source': 'pattern',
                'confidence': patterns[0]['similarity']
            })

        # ── 2. Decision Making ───────────────────────────────────────────────
        decision = self.decide(options, criteria, scores, risk_aversion)
        results['decision'] = decision
        confidence_inputs.append({
            'source': 'decision',
            'confidence': decision.get('confidence', 0.5)
        })

        # ── 3. Bayesian Inference ────────────────────────────────────────────
        if hypothesis is not None and evidence is not None:
            prob = self.probability(hypothesis, evidence)
            results['probability'] = prob
            confidence_inputs.append({
                'source': 'probability',
                'confidence': prob.get('confidence', 0.5)
            })

        # ── 4. Rule Evaluation ───────────────────────────────────────────────
        if rules is not None:
            rule_eval = self.evaluate_rules(input_data, rules)
            results['rules_triggered'] = rule_eval.get('triggered', [])
            results['rule_conflicts']  = rule_eval.get('conflicts', [])
            n_triggered = len(results['rules_triggered'])
            confidence_inputs.append({
                'source': 'rules',
                'confidence': min(_safe_div(n_triggered, len(rules)), 1.0) if rules else 0.5
            })

        # ── 5. Causal Reasoning ──────────────────────────────────────────────
        if causal_graph is not None:
            results['causal'] = self.causal_reason(input_data, causal_graph)
            strength = results['causal'].get('total_strength', 0.0)
            confidence_inputs.append({
                'source': 'causal',
                'confidence': _clamp(strength)
            })

        # ── 6. Temporal Reasoning ────────────────────────────────────────────
        if sequence is not None:
            results['temporal'] = self.temporal_reason(sequence)

        # ── 7. Abductive Reasoning ───────────────────────────────────────────
        if hypotheses is not None:
            obs_keys = [k for k, v in input_data.items() if v]
            results['abduction'] = self.abduce(obs_keys, hypotheses)
            abd_score = results['abduction'].get('best_hypothesis', {})
            if abd_score:
                confidence_inputs.append({
                    'source': 'abduction',
                    'confidence': abd_score.get('abductive_score', 0.5)
                })

        # ── 8. Belief Revision ───────────────────────────────────────────────
        if beliefs is not None:
            results['belief_revision'] = self.revise_belief(beliefs, input_data)

        # ── 9. Contradiction Check ───────────────────────────────────────────
        stmts = [
            {'id': f'i_{k}', 'subject': k,
             'relation': 'eq', 'value': v}
            for k, v in input_data.items()
        ]
        results['contradictions'] = self.detect_contradiction(stmts)

        # ── 10. Overall Confidence ───────────────────────────────────────────
        results['confidence'] = self.score_confidence(confidence_inputs, weights)

        # ── 11. Meta-Reasoning ───────────────────────────────────────────────
        results['meta'] = self.meta_reason(results, required_confidence)

        # ── 12. Summary ──────────────────────────────────────────────────────
        parts = []
        if decision.get('choice'):
            parts.append(
                f"Decision={decision['choice']} "
                f"({decision.get('score', 0):.0%})"
            )
        if patterns:
            parts.append(f"PatternMatch={patterns[0]['similarity']:.0%}")
        if 'probability' in results:
            p = results['probability']
            parts.append(
                f"P({hypothesis})={p['probability']:.0%} [{p['interpretation']}]"
            )
        if 'temporal' in results:
            parts.append(f"Trend={results['temporal']['trend']}")
        if results.get('meta'):
            parts.append(f"Meta={results['meta']['recommendation']}")

        results['summary'] = ' | '.join(parts)

        return results


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────────────────────────
reasoning = ReasoningEngine()


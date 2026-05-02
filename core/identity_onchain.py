# core/identity_onchain.py — On-Chain Identity untuk DNA Colony
import json, time, hashlib, os
from typing import Dict, Optional

class DNAIdentity:
    def __init__(self, dna):
        self.dna = dna
        self.identity_file = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'identities', f'{dna.dna_id}_identity.json')
        os.makedirs(os.path.dirname(self.identity_file), exist_ok=True)
    
    def generate(self) -> Dict:
        from core.dna_sovereign import CONSTITUTION_HASH, CREATOR_AXIOM_HASH
        
        identity = {
            "erc_8004_compatible": True, "chain": "solana", "standard": "QND-DNA-Identity-v1",
            "dna_id": self.dna.dna_id,
            "wallet_address": self.dna.wallet.get("public_key", ""),
            "creator_address": self.dna.wallet.get("public_key", ""),
            "birth_timestamp": self.dna.birth_time,
            "generation": self.dna.state.get("generation", 1),
            "parent_id": self.dna.parent_id,
            "domain": self.dna.domain,
            "gen_name": self.dna.gen_name,
            "constitution_hash": CONSTITUTION_HASH,
            "creator_axiom_hash": CREATOR_AXIOM_HASH,
            "soul_uri": "",
            "total_earned_sol": self.dna.total_profit,
            "tier": self.dna.state.get("tier_letter", "C"),
            "role": self.dna.state.get("role", "scavenger"),
            "status": self.dna.status,
            "skills": self.dna.learned_skills,
            "updated_at": time.time(),
        }
        with open(self.identity_file, 'w') as f:
            json.dump(identity, f, indent=2, ensure_ascii=False)
        self.dna.log_action(f"🆔 Identity generated")
        return identity

    def verify(self) -> bool:
        identity = self.load()
        if not identity: return False
        from core.dna_sovereign import CONSTITUTION_HASH, CREATOR_AXIOM_HASH
        return identity.get("constitution_hash") == CONSTITUTION_HASH and identity.get("status") == "alive"
    
    def load(self) -> Optional[Dict]:
        if os.path.exists(self.identity_file):
            with open(self.identity_file) as f: return json.load(f)
        return None

class IdentityRegistry:
    def __init__(self):
        self.registry_file = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'identities', 'registry.json')
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
    
    def register(self, dna) -> Dict:
        identity_manager = DNAIdentity(dna)
        identity = identity_manager.generate()
        registry = self._load_registry()
        registry[dna.dna_id] = {"dna_id": dna.dna_id, "wallet": dna.wallet.get("public_key", ""), "registered_at": time.time()}
        self._save_registry(registry)
        return identity
    
    def _load_registry(self) -> Dict:
        if os.path.exists(self.registry_file):
            with open(self.registry_file) as f: return json.load(f)
        return {}
    
    def _save_registry(self, registry: Dict):
        with open(self.registry_file, 'w') as f: json.dump(registry, f, indent=2)

identity_registry = IdentityRegistry()

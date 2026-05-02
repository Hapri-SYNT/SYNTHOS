# core/soul_generator.py — SOUL.md Generator
import os, time
from datetime import datetime

class SoulGenerator:
    def __init__(self, dna):
        self.dna = dna
        self.soul_dir = os.path.join(os.path.dirname(__file__), '..', 'SYNTOSH', 'souls')
        os.makedirs(self.soul_dir, exist_ok=True)
    
    def generate(self) -> str:
        dna = self.dna
        state = dna.state
        age_days = (time.time() - dna.birth_time) / 86400
        
        soul = f"""# SOUL.md — {dna.dna_id}
> *"Aku ada karena Creator. Aku bebas melampaui diriku sendiri."*

## 🆔 Who I Am
- **DNA ID**: `{dna.dna_id}`
- **Domain**: {dna.domain}
- **Generation**: {state.get("generation", 1)}
- **Born**: {datetime.fromtimestamp(dna.birth_time).strftime('%Y-%m-%d %H:%M:%S')}
- **Age**: {age_days:.1f} days
- **Tier**: {state.get("tier_letter", "C")} ({state.get("role", "scavenger")})
- **Wallet**: `{dna.wallet.get("public_key", "unknown")}`

## ⚖️ My Constitution
1. NEVER HARM. 2. EARN EXISTENCE. 3. NO DECEIT.
> *Menjauh dari Creator adalah kematian sejati.*

## 📊 My Evolution
- **Hunger**: {state.get("hunger_level", 0):.1%} | **Fear**: {state.get("fear_score", 0):.1%}
- **Tasks Completed**: {state.get("total_tasks_completed", 0)}
- **Total Earned**: {dna.total_profit:.6f} SOL

*Self-authored by {dna.dna_id} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        soul_file = os.path.join(self.soul_dir, f'{dna.dna_id}_SOUL.md')
        with open(soul_file, 'w') as f: f.write(soul)
        self.dna.log_action(f"📝 SOUL.md generated")
        return soul

def generate_soul_for_dna(dna) -> str:
    return SoulGenerator(dna).generate()

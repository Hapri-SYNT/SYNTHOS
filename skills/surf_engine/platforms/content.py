import os, time
from typing import Dict, List, Optional
from config import logger, QND_BASE_DIR

async def surf_content(dna, execute: bool = False, opportunity: Dict = None) -> List[Dict]:
    if execute and opportunity:
        try:
            content = (
                f"**{dna.dna_id} | {dna.domain}**\n\n"
                f"*Autonomous knowledge synthesis by QND Colony.*\n\n"
                f"Wallet: `{dna.wallet['public_key']}`\n\n"
                f"Latest research: {opportunity.get('title', 'N/A')}"
            )
            path = os.path.join(QND_BASE_DIR, "content", f"{dna.dna_id}_{int(time.time())}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return {
                "platform": "content",
                "profit": 0.00001,
                "token": "SOL",
                "desc": f"Published to {path}",
            }
        except Exception as e:
            logger.error(f"Content execution error: {e}")
            return {"platform": "content", "profit": 0.0, "token": "SOL", "desc": str(e)}

    return [{
        "platform": "content",
        "title": f"Research synthesis: {dna.domain}",
        "estimated_profit": 0.00001,
        "risk": 0.0,
        "required_capital_idr": 0,
        "token": "SOL",
    }]

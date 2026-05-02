import asyncio
from typing import Dict, List, Optional

from config import logger


async def surf_solana(dna, execute: bool = False, opportunity: Dict = None) -> List[Dict]:
    """
    Cari peluang arbitrage di Jupiter (Solana).
    Kalau execute=True, jalankan trade.
    """
    if execute and opportunity:
        # Safety net check
        if not dna.should_execute_task("dex_trade"):
            return {
                "platform": "solana_dex",
                "profit": 0,
                "token": "SOL",
                "desc": "Blocked by fear/sandbox/safety net",
            }
        # Eksekusi trade via UniversalTaskEngine
        from core.economy import universal_task_engine
        result = await universal_task_engine.execute(dna, "dex_trade")
        return {
            "platform": "solana_dex",
            "profit": result.get("profit", 0),
            "token": "SOL",
            "desc": result.get("desc", ""),
        }

    # Mode search: kumpulkan peluang
    opportunities = []

    # Cek saldo REAL on-chain
    from core.economy import wallet_manager
    sol_balance = wallet_manager.get_real_balance(dna.dna_id)

    if sol_balance < 0.002:
        logger.info(f"🏄 [{dna.dna_id}] SOL balance too low ({sol_balance:.6f})")
        return opportunities

    # Fear check — kalau takut, skip search
    if dna.is_fearful():
        logger.info(f"🏄 [{dna.dna_id}] Too fearful to surf (fear={dna.state.get('fear_score',0):.2f})")
        return opportunities

    # Coba cek Jupiter quote
    try:
        import aiohttp
        input_mint = "So11111111111111111111111111111111111111112"
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        amount = int(min(sol_balance * 0.5, 0.1) * 1e9)  # Max 0.1 SOL per trade

        url = f"https://quote-api.jup.ag/v6/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps=50"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    quote = await resp.json()
                    out_amount = int(quote.get("outAmount", 0)) / 1e6
                    opportunities.append({
                        "platform": "solana_dex",
                        "title": "SOL→USDC arbitrage",
                        "estimated_profit": out_amount * 0.001,
                        "risk": 0.3,
                        "required_capital_sol": sol_balance * 0.5,
                        "token": "SOL",
                    })
    except Exception as e:
        logger.debug(f"Jupiter quote error: {e}")

    return opportunities

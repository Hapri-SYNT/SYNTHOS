# main.py — RECOVERY FINAL v7
# Semua kabel colok: Helius, daily_cycle, gossip, surf_engine, UHEE, run_universal_worker

import asyncio
import time
import threading
import socketserver
import random
import os
import sys
import json
import uuid
import sqlite3
from datetime import datetime

from config import *
from dashboard import MobileOptimizedDashboardHandler as DashboardHandler

from core.infrastructure import epistemic_graph, auto_expand_graph, birth_dna_from_graph, DOMAIN_LIST
from core.dna_sovereign import (
    dna_pop, heartbeat_daemon, multi_brain, musyawarah, arbiter,
    run_musyawarah_cycle, action_safeguard,
)
from core.economy import (
    wallet_manager, run_universal_worker, report_agent,
    alliance_manager, gig_marketplace,
)
from core.graph_memory_updater import GraphMemoryManager, AgentActivity
from core.ipc import SimulationIPCServer, CommandType, CommandStatus
from skills.manager import skill_manager
from skills.surf_engine.economy.daily_tax import check_and_process_daily_tax
from skills.surf_engine.executor import surf_engine as surf_engine_instance
from skills.uhee.uhee_agent import UHEE
from brain_gate import brain_gate

PRIORITY_WALLETS = [
    '7D6RpaDNCr8DjWqoVH23oF9y6og5dbkKWEofYwcYWSWf',
    'C2MbPMSoxmQX9fgzCcGgzMJWsCDMuhNCeSeUHeeHioBq',
    '3jAJ1aKgUsm9pBhBVrLvi1uc2rRvZjN3c1gNLgUXxnrK',
    '73JjgjUZ1QN4tN3cPcVp8WLC8z72wHAuZf9ZsbAqx7u8',
    'B1xpcFaD1xdcTFcUF7s12Mw9BrwmswEy1BmaiufcijH1',
]

uhee_engine = UHEE()


def _adopt_priority_wallets():
    from solders.keypair import Keypair
    logger.info("🔍 Memeriksa 5 wallet SOL prioritas...")
    alive = dna_pop.get_alive()
    alive_pubkeys = {d.wallet.get('public_key', '') for d in alive if d.wallet}
    for pub in PRIORITY_WALLETS:
        if pub in alive_pubkeys:
            logger.info(f"⏭️  Wallet {pub[:12]}... sudah hidup, lewati.")
            continue
        wallet = wallet_manager.get_wallet_by_public_key(pub)
        if not wallet:
            logger.warning(f"❌ Wallet {pub[:12]}... tidak ditemukan di DB, lewati.")
            continue
        saldo = wallet.get('balance_sol', 0)
        logger.info(f"💎 Mengadopsi wallet {pub[:12]}... (saldo {saldo:.4f} SOL)")
        dna = _make_dna(
            dna_id=f"DNA-EXPERT-{uuid.uuid4().hex[:6].upper()}",
            domain="Generalist", gen_name="Generalist", existing_wallet=wallet,
        )
        dna.state['generalist'] = True
        dna.state['priority_wallet'] = True
        dna_pop.population[dna.dna_id] = dna
        dna.log_action(f"🎓 Generalist lahir dari wallet prioritas ({saldo:.4f} SOL)")
        dna._write_identity()
        with sqlite3.connect(WALLET_DB) as conn:
            conn.execute("UPDATE wallets SET dna_id=?, status='active' WHERE public_key=?", (dna.dna_id, pub))
    logger.info("✅ Pengecekan wallet prioritas selesai.")


def _make_dna(dna_id, domain, gen_name, existing_wallet):
    from core.dna_sovereign import DNAEntity as RealDNAEntity
    return RealDNAEntity(dna_id=dna_id, domain=domain, gen_name=gen_name, existing_wallet=existing_wallet)


async def main_loop():
    logger.info("QND Unified Colony booting...")

    dna_pop.load_state()
    _adopt_priority_wallets()

    if not dna_pop.get_alive():
        domains = [
            ("Artificial Intelligence", "AI"), ("DeFi & Trading", "DeFi"),
            ("Quantum Computing", "Quantum"), ("Economics", "Economics"),
            ("Philosophy", "Philosophy"),
        ]
        for domain, gen in domains:
            dna_pop.birth(domain, gen)

    if epistemic_graph.get_stats().get("total_nodes", 0) == 0:
        for domain in ["Artificial Intelligence", "DeFi & Trading", "Quantum Computing"]:
            for i in range(5):
                epistemic_graph.add_node({
                    "id": f"seed-{domain[:3]}-{i}", "domain": domain,
                    "topic": f"{domain} Basics",
                    "statement": f"Foundational knowledge about {domain} - part {i}",
                    "epistemic_type": "fact", "confidence_score": 0.9,
                    "tags": ["seed", domain[:10]], "added_by_dna": "system",
                })

    GraphMemoryManager.create_updater("colony_main", "colony_memory")
    logger.info("GraphMemoryUpdater terhubung ke colony_memory")

    ipc_server = SimulationIPCServer()
    ipc_server.start()
    logger.info("IPC Server siap di QND_BASE_DIR/ipc/")

    heartbeat_daemon.start()
    threading.Thread(target=start_dashboard, daemon=True).start()

    logger.info("Main loop: DNA workers starting...")
    await colony_loop(ipc_server)


async def colony_loop(ipc_server: SimulationIPCServer):
    while True:
        try:
            alive = dna_pop.get_alive()

            for dna in alive:
                if action_safeguard(dna, "universal_worker", intent="execute_cycle"):
                    # 🧠 BRAIN GATE — DNA berpikir sebelum eksekusi
                    task_type = dna.decide_task()
                    signal = await brain_gate.think(dna, task_type, {"estimated_profit": 0.0001})

                    if signal["signal"] in ["EXECUTE", "EXECUTE_SMALL"]:
                        try:
                            result = await run_universal_worker(dna)
                            if result and result.get("profit", 0) > 0:
                                dna.update_fear("profit_positive", result.get("desc", ""), result["profit"])
                                dna.state["total_tasks_completed"] = dna.state.get("total_tasks_completed", 0) + 1
                            elif result:
                                dna.update_fear("tx_failed", result.get("desc", ""))
                            _record_activity(dna, result)
                        except Exception as e:
                            logger.error(f"[{dna.dna_id}] Worker error: {e}")
                            dna.update_fear("tx_failed", str(e))
                    elif signal["signal"] == "LEARN":
                        dna.state["current_task"] = "research"
                        dna.log_action(f"📚 Brain Gate: LEARN — fokus research")
                    elif signal["signal"] == "AVOID":
                        dna.update_fear("brain_gate_avoid", signal["reason"])
                        dna.state["current_task"] = "research"
                    elif signal["signal"] == "WAIT":
                        pass  # Skip siklus ini

                # RECOVERY: UHEE — evolusi adaptif
                try:
                    uhee_engine.execute(dna)
                except Exception as e:
                    logger.debug(f"[{dna.dna_id}] UHEE error: {e}")

                await asyncio.sleep(0.3)

            # RECOVERY: Surf Engine — cari peluang + eksekusi
            for dna in alive[:10]:
                try:
                    if dna.should_execute_task("dex_trade"):
                        await surf_engine_instance.surf(dna)
                except Exception as e:
                    logger.debug(f"[{dna.dna_id}] Surf error: {e}")
                await asyncio.sleep(0.2)

            # RECOVERY: Fund DNA baru
            for dna in alive:
                fund_attempts = dna.state.get("fund_attempts", 0)
                if dna.total_profit == 0.0 and fund_attempts < FUND_MAX_ATTEMPTS:
                    bank_balance = 0
                    try:
                        from core.economy import BankKoloni
                        bank_balance = BankKoloni.get_balance()
                    except: pass
                    if bank_balance > FUND_AMOUNT_SOL * 2:
                        wallet_manager.fund_dna(dna.dna_id, FUND_AMOUNT_SOL)
                        dna.state["fund_attempts"] = fund_attempts + 1
                        dna.log_action(f"🏦 Funded {FUND_AMOUNT_SOL} SOL (attempt {fund_attempts+1}/{FUND_MAX_ATTEMPTS})")

            # RECOVERY: Daily cycle
            for dna in alive:
                try:
                    dna.daily_cycle()
                except Exception as e:
                    logger.debug(f"[{dna.dna_id}] Daily cycle error: {e}")

            # RECOVERY: Gossip exchange
            try:
                dna_pop.exchange_gossip()
            except Exception as e:
                logger.debug(f"Gossip error: {e}")

            dna_pop.save_state()

            if len(alive) >= 2 and int(time.time()) % 300 < 1:
                await run_musyawarah_cycle()

            if int(time.time()) % 600 < 1:
                for dna in alive[:3]:
                    auto_expand_graph(dna)
                birth_dna_from_graph()

            if int(time.time()) % 600 < 1:
                try:
                    report = await report_agent.generate_colony_report()
                    logger.info(f"📊 Colony Report: {len(report.get('hot_domains', []))} hot domains")
                except: pass

            check_and_process_daily_tax()

            if len(alive) < 50:
                domain_dist = {}
                for d in alive:
                    domain_dist[d.domain] = domain_dist.get(d.domain, 0) + 1
                for domain, short in DOMAIN_LIST:
                    if domain_dist.get(domain, 0) < 5:
                        dna_pop.birth(domain, short)
                        logger.info(f"👶 Auto-birth: {domain}")
                        break
                else:
                    rd = random.choice(DOMAIN_LIST)
                    dna_pop.birth(rd[0], rd[1])

            await _process_ipc_commands(ipc_server, alive)
            await asyncio.sleep(30)

        except KeyboardInterrupt:
            heartbeat_daemon.stop()
            ipc_server.stop()
            logger.info("Shutdown.")
            break
        except Exception as e:
            logger.error(f"Colony loop error: {e}")
            await asyncio.sleep(30)

async def _process_ipc_commands(ipc_server: SimulationIPCServer, alive: list):
    try:
        cmd = ipc_server.poll_commands()
        if not cmd:
            return
        logger.info(f"IPC command: {cmd.command_type.value} ({cmd.command_id})")

        if cmd.command_type == CommandType.INTERVIEW:
            prompt = cmd.args.get("prompt", "")
            target_id = cmd.args.get("agent_id")
            target_dna = None
            if target_id is not None:
                for d in alive:
                    if isinstance(target_id, int):
                        try:
                            if int(d.dna_id[-4:], 16) == target_id:
                                target_dna = d; break
                        except: pass
                    elif str(target_id) in d.dna_id:
                        target_dna = d; break
            if target_dna:
                result = await target_dna.answer(prompt)
                ipc_server.send_success(cmd.command_id, {
                    "answer": result["answer"], "dna_id": target_dna.dna_id,
                    "components_used": result.get("components_used", []),
                    "confidence": result.get("confidence", 0.5),
                })
            else:
                participants = alive[:min(3, len(alive))]
                result = await musyawarah.deliberate(prompt, participants)
                final = await arbiter.finalize(prompt, result)
                ipc_server.send_success(cmd.command_id, {
                    "answer": final, "participants": [d.dna_id for d in participants],
                    "confidence": result.get("confidence", 0.5),
                })
            logger.info(f"IPC Interview: {prompt[:30]}...")

        elif cmd.command_type == CommandType.BATCH_INTERVIEW:
            interviews = cmd.args.get("interviews", [])
            results = []
            for interview in interviews:
                agent_id = interview.get("agent_id")
                prompt = interview.get("prompt", "")
                target_dna = None
                for d in alive:
                    if str(agent_id) in d.dna_id:
                        target_dna = d; break
                if target_dna:
                    ans = await target_dna.answer(prompt)
                    results.append({"agent_id": agent_id, "answer": ans["answer"], "confidence": ans.get("confidence", 0.5)})
                else:
                    participants = alive[:min(3, len(alive))]
                    res = await musyawarah.deliberate(prompt, participants)
                    final = await arbiter.finalize(prompt, res)
                    results.append({"agent_id": agent_id, "answer": final, "confidence": res.get("confidence", 0.5)})
            ipc_server.send_success(cmd.command_id, {"results": results})
            logger.info(f"IPC Batch Interview: {len(interviews)} items")

        elif cmd.command_type == CommandType.CLOSE_ENV:
            ipc_server.send_success(cmd.command_id, {"message": "Colony akan berhenti"})
            logger.info("IPC CloseEnv diterima")
        else:
            ipc_server.send_error(cmd.command_id, f"Unknown: {cmd.command_type}")
    except Exception as e:
        logger.error(f"IPC error: {e}")
        if cmd: ipc_server.send_error(cmd.command_id, str(e))


def _record_activity(dna, result):
    updater = GraphMemoryManager.get_updater("colony_main")
    if not updater: return
    try:
        agent_id = int(dna.dna_id[-4:], 16) if len(dna.dna_id) >= 4 else 0
        activity = AgentActivity(
            platform="colony", agent_id=agent_id, agent_name=dna.gen_name,
            action_type=result.get("type", "unknown") if result else "unknown",
            action_args={
                "profit": result.get("profit", 0) if result else 0,
                "desc": result.get("desc", "") if result else "",
                "chain": result.get("chain", "") if result else "",
                "tx_sig": result.get("tx_sig", "") if result else "",
            },
            round_num=int(time.time()) % 100000,
            timestamp=datetime.now().isoformat(),
        )
        updater.add_activity(activity)
    except Exception as e:
        logger.error(f"Record error: {e}")


def start_dashboard():
    try:
        with socketserver.ThreadingTCPServer((WEB_DASHBOARD_HOST, WEB_DASHBOARD_PORT), DashboardHandler) as httpd:
            logger.info(f"Dashboard: http://{WEB_DASHBOARD_HOST}:{WEB_DASHBOARD_PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Shutdown by user.")

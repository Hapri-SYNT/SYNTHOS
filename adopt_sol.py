import sqlite3, json, os, time, uuid
from config import WALLET_DB, QND_BASE_DIR, IDENTITY_DIR

pubkeys = [
    '7D6RpaDNCr8DjWqoVH23oF9y6og5dbkKWEofYwcYWSWf',
    'C2MbPMSoxmQX9fgzCcGgzMJWsCDMuhNCeSeUHeeHioBq',
    '3jAJ1aKgUsm9pBhBVrLvi1uc2rRvZjN3c1gNLgUXxnrK',
    '73JjgjUZ1QN4tN3cPcVp8WLC8z72wHAuZf9ZsbAqx7u8',
    'B1xpcFaD1xdcTFcUF7s12Mw9BrwmswEy1BmaiufcijH1'
]

conn = sqlite3.connect(WALLET_DB)
state_path = os.path.join(QND_BASE_DIR, "colony_state.json")
if os.path.exists(state_path):
    with open(state_path) as f:
        state = json.load(f)
else:
    state = []

alive_ids = {d['dna_id'] for d in state}

for pub in pubkeys:
    cur = conn.execute('SELECT dna_id, encrypted_private_key, balance_sol FROM wallets WHERE public_key=?', (pub,))
    row = cur.fetchone()
    if not row:
        continue
    curr_dna, priv_enc, bal = row
    if curr_dna in alive_ids:
        print(f'⏭️  {pub[:12]}... sudah hidup')
        continue

    # buat ID baru
    new_id = f"DNA-EXPERT-{uuid.uuid4().hex[:6].upper()}"
    domain = 'DeFi & Trading' if 'DEF' in curr_dna else 'AI'
    
    # update wallet DB
    conn.execute('UPDATE wallets SET dna_id=?, status=? WHERE public_key=?', (new_id, 'active', pub))
    
    # tambahkan ke state
    state.append({
        "dna_id": new_id,
        "domain": domain,
        "gen_name": "Expert",
        "parent_id": None,
        "birth_time": time.time() - 86400*30,
        "total_profit": bal,
        "daily_profit": bal/30,
        "status": "alive",
        "tier": "normal"
    })
    print(f'✅ {new_id} ({domain}) mengadopsi {pub[:12]}... ({bal} SOL)')

conn.commit()
conn.close()

with open(state_path, 'w') as f:
    json.dump(state, f)
print(f'🔥 State disimpan. Total DNA: {len(state)}')

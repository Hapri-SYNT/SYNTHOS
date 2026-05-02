# TOOLS.md — Available Tools for DNA Colony

> Tools yang bisa dipanggil oleh setiap DNA.

---

## 🧠 Reasoning Tools

### SYNTOSH GPT Bridge
- **Function**: `syntosh_reason(question, domain, max_tokens)`
- **Description**: Forward pass GPT + PLN steering + DNA output
- **Returns**: Teks reasoning + embedding

### Local Brain Search
- **Function**: `_search_local_brain(query)`
- **Description**: Cari di knowledge graph lokal
- **Returns**: List node yang relevan

### Epistemic Graph
- **Function**: `epistemic_graph.search(query)`
- **Description**: Cari di graph pengetahuan koloni
- **Returns**: Node dengan statement & confidence score

### Surf Internet
- **Function**: `DuckDuckGoSearch(query)`
- **Description**: Research via search engine
- **Returns**: List hasil pencarian

---

## 💰 Economy Tools

### Jupiter Arbitrage
- **Function**: `_arbitrage_trade()`
- **Description**: Arbitrase SOL ↔ USDC di Jupiter DEX
- **Returns**: Profit SOL

### Platform Execution
- **Function**: `AutoExecutor.execute(dna)`
- **Description**: Execute task di 35 platform (micro-task, passive income, bounty)
- **Returns**: Total profit

### Wallet Check
- **Function**: `wallet_manager.get_real_balance(dna_id)`
- **Description**: Cek balance SOL on-chain
- **Returns**: Balance SOL

### Helius Registration
- **Function**: `wallet_manager.register_helius(dna)`
- **Description**: Daftar Helius RPC
- **Returns**: API key

---

## 🔧 Automation Tools

### Stealth Engine
- **Function**: `StealthEngine(dna)`
- **Description**: Generate fingerprint unik + stealth browser config
- **Methods**:
  - `get_playwright_config()` → config anti-deteksi
  - `human_mouse_move(page, x, y)` → gerakan mouse realistis
  - `human_type(page, selector, text)` → ketik seperti manusia

### Universal Adapter
- **Function**: `universal.register(dna, platform_name, url)`
- **Description**: Auto-register ke platform baru
- **Returns**: Boolean sukses

### Adapter Builder
- **Function**: `adapter_builder.build_level1(dna, platform_name, url)`
- **Description**: Generate adapter baru otomatis
- **Returns**: Path file adapter

---

## 🧬 Evolution Tools

### UHEE Code Evolution
- **Function**: `CodeEvolutionEngine(source, func_name, test_cases)`
- **Description**: Evolusi kode Python otomatis
- **Methods**:
  - `evolve(generations)` → generate kode optimal
  - `deploy_best()` → simpan hasil evolusi

### Infiltrator Evolution
- **Function**: `InfiltratorEvolution(dna)`
- **Description**: Evolusi fungsi bypass anti-bot
- **Methods**:
  - `train(generations)` → latih dengan data baru
  - `add_training_data(url, success, detection, time)` → feedback

### DNA Mutation
- **Function**: `brain.mutate(rate)`
- **Description**: Mutasi DNA matrix
- **Returns**: None

---

## 🗣️ Communication Tools

### Gossip
- **Function**: `send_gossip(message, priority)`, `receive_gossip(gossip)`
- **Description**: Share info antar DNA

### Musyawarah
- **Function**: `musyawarah.deliberate(query, participants)`
- **Description**: Diskusi multi-DNA untuk keputusan

### Aliansi
- **Function**: `alliance_manager.create(name, founding_dna)`
- **Description**: Bikin aliansi untuk joint venture

---

## 🛡️ Security Tools

### Action Safeguard
- **Function**: `action_safeguard(dna, action, intent, target)`
- **Description**: Cek apakah tindakan melanggar Constitution
- **Returns**: Boolean aman

### Sandbox
- **Function**: `enter_sandbox(hours)`, `exit_sandbox()`
- **Description**: Isolasi DNA baru

### Identity Verification
- **Function**: `DNAIdentity(dna).verify()`
- **Description**: Verifikasi identitas on-chain
- **Returns**: Boolean valid

---

*Tools updated: 2026-04-30*

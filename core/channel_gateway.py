# core/channel_gateway.py — Multi-Channel Gateway untuk DNA Colony
# Diadopsi dari OpenClaw — setiap DNA bisa connect ke Telegram, Discord, dll

import json
import time
import threading
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class ChannelType(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    WEBCHAT = "webchat"
    API = "api"

@dataclass
class ChannelMessage:
    """Pesan yang masuk dari channel manapun."""
    channel: ChannelType
    sender_id: str
    sender_name: str
    text: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

@dataclass
class ChannelResponse:
    """Respons yang dikirim ke channel."""
    text: str
    dna_id: str = ""
    components_used: List[str] = field(default_factory=list)


class ChannelGateway:
    """
    Gateway untuk routing pesan dari berbagai channel ke DNA Colony.
    
    Features:
    - Multi-channel inbox (Telegram, Discord, WhatsApp, WebChat, API)
    - Auto-routing ke DNA yang sesuai (berdasarkan domain)
    - DM pairing (approval sebelum proses pesan)
    - Rate limiting per channel
    """
    
    def __init__(self):
        self.paired_users: Dict[str, set] = {}  # channel → set of approved sender_ids
        self.dna_assignments: Dict[str, str] = {}  # sender_id → dna_id
        self.rate_limits: Dict[str, float] = {}  # sender_id → last_message_time
        self.rate_limit_seconds = 2  # minimal jeda antar pesan
        
        # Config channels
        self.channels_config = {
            ChannelType.TELEGRAM: {"enabled": False, "token": "", "webhook_url": ""},
            ChannelType.DISCORD: {"enabled": False, "token": "", "webhook_url": ""},
            ChannelType.WHATSAPP: {"enabled": False, "token": "", "phone_id": ""},
            ChannelType.WEBCHAT: {"enabled": True, "port": 8080},  # selalu on
            ChannelType.API: {"enabled": True},  # selalu on
        }
    
    def is_paired(self, channel: ChannelType, sender_id: str) -> bool:
        """Cek apakah sender sudah di-approve."""
        ch_key = channel.value
        return sender_id in self.paired_users.get(ch_key, set())
    
    def approve_sender(self, channel: ChannelType, sender_id: str):
        """Approve sender untuk pairing."""
        ch_key = channel.value
        if ch_key not in self.paired_users:
            self.paired_users[ch_key] = set()
        self.paired_users[ch_key].add(sender_id)
    
    def check_rate_limit(self, sender_id: str) -> bool:
        """Cek rate limit. Returns True jika boleh kirim."""
        now = time.time()
        if sender_id in self.rate_limits:
            if now - self.rate_limits[sender_id] < self.rate_limit_seconds:
                return False
        self.rate_limits[sender_id] = now
        return True
    
    def assign_dna(self, sender_id: str, message: str) -> str:
        """
        Assign DNA yang paling cocok berdasarkan isi pesan.
        Bisa di-override dengan pairing DNA spesifik.
        """
        if sender_id in self.dna_assignments:
            return self.dna_assignments[sender_id]
        
        # Auto-detect domain dari pesan
        from core.dna_sovereign import dna_pop
        alive = dna_pop.get_alive()
        if not alive:
            return ""
        
        msg_lower = message.lower()
        
        # Cari DNA dengan domain yang cocok
        keyword_map = {
            "trading": ["trading", "market", "stock", "crypto", "profit", "trade"],
            "research": ["research", "cari", "search", "find", "apa itu", "jelaskan"],
            "automation": ["task", "execute", "jalankan", "kerjakan"],
            "defi": ["defi", "nft", "token", "airdrop", "wallet"],
        }
        
        # Hitung skor per DNA
        scored = []
        for dna in alive:
            score = 0
            domain_lower = dna.domain.lower()
            # Domain matching
            for keyword, terms in keyword_map.items():
                if keyword in domain_lower:
                    for t in terms:
                        if t in msg_lower:
                            score += 3
            
            # Skills matching
            for skill in dna.learned_skills:
                if skill in msg_lower:
                    score += 2
            
            # Tier bonus
            tier_score = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "E": 0}
            score += tier_score.get(dna.state.get('tier_letter', 'C'), 1)
            
            scored.append((score, dna))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored and scored[0][0] > 0:
            return scored[0][1].dna_id
        
        # Fallback: DNA pertama yang alive
        return alive[0].dna_id if alive else ""
    
    def route_message(self, message: ChannelMessage) -> ChannelResponse:
        """
        Route pesan dari channel → assign DNA → dapatkan respons.
        """
        # 1. Cek pairing
        if not self.is_paired(message.channel, message.sender_id):
            # Generate pairing code
            pairing_code = f"{message.sender_id[:8]}-{int(time.time()) % 10000:04d}"
            return ChannelResponse(
                text=f"🔐 Pairing required. Your code: `{pairing_code}`\n"
                     f"Approved by Creator to enable this DNA to respond.",
                components_used=["gateway:pairing"]
            )
        
        # 2. Cek rate limit
        if not self.check_rate_limit(message.sender_id):
            return ChannelResponse(
                text="⏳ Rate limited. Please wait a moment.",
                components_used=["gateway:rate_limit"]
            )
        
        # 3. Assign DNA
        dna_id = self.assign_dna(message.sender_id, message.text)
        if not dna_id:
            return ChannelResponse(
                text="❌ No DNA available right now. Please try again later.",
                components_used=["gateway:no_dna"]
            )
        
        # 4. Dapatkan respons dari DNA
        from core.dna_sovereign import dna_pop
        dna = dna_pop.population.get(dna_id)
        if not dna or dna.status != "alive":
            return ChannelResponse(
                text="❌ Assigned DNA is not available.",
                components_used=["gateway:dna_dead"]
            )
        
        # 5. Proses pesan via DNA pipeline
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(dna.answer(message.text, use_musyawarah=False))
            loop.close()
            
            answer = result.get('answer', 'Maaf, tidak bisa menjawab.')
            components = result.get('components_used', [])
            
            return ChannelResponse(
                text=f"[{dna.dna_id}] {answer}",
                dna_id=dna_id,
                components_used=components
            )
        except Exception as e:
            return ChannelResponse(
                text=f"❌ Error processing: {str(e)[:100]}",
                dna_id=dna_id,
                components_used=["gateway:error"]
            )


# Singleton
gateway = ChannelGateway()

#!/usr/bin/env python3
"""
Remote Brain Extractor - Unlimited header download
"""

import sys
import json
import httpx

sys.path.insert(0, 'deep_reader/parsers')
from gguf_parser import BinaryReader

url = "https://huggingface.co/unsloth/DeepSeek-V3-GGUF/resolve/main/DeepSeek-V3-Q2_K_L/DeepSeek-V3-Q2_K_L-00003-of-00005.gguf"

print(f"🌐 Streaming {url}...")
print("📥 Downloading until all metadata parsed...")

# Streaming download chunk by chunk
chunks = []
total = 0
last_percent = 0

with httpx.stream("GET", url, follow_redirects=True) as resp:
    for chunk in resp.iter_bytes(chunk_size=1024*1024):  # 1MB chunks
        chunks.append(chunk)
        total += len(chunk)
        
        # Parse dari awal setiap 50MB untuk cek apakah udah complete
        if len(chunks) % 50 == 0:
            data = b''.join(chunks)
            try:
                r = BinaryReader(data)
                magic_offset = BinaryReader.find_magic_offset(data)
                r.seek(magic_offset + 4)  # skip magic
                version = r.uint32()
                n_tensors = r.uint64()
                n_metadata_kv = r.uint64()
                
                # Baca metadata
                for _ in range(n_metadata_kv):
                    r.entry()
                
                # Coba baca semua tensor info
                all_read = True
                for _ in range(n_tensors):
                    try:
                        r.tensor_info()
                    except EOFError:
                        all_read = False
                        break
                
                if all_read:
                    print(f"\n✅ Complete at {total/(1024**3):.1f} GB")
                    break
                    
            except Exception:
                pass
        
        # Progress
        percent = total // (10*1024*1024)  # setiap 10MB
        if percent > last_percent:
            print(f"📥 Downloaded: {total/(1024**3):.1f} GB")
            last_percent = percent

data = b''.join(chunks)

# Parse final
from gguf_parser import GGUFRemoteReader
reader = GGUFRemoteReader(url, max_header_mb=999999)
reader._header_data = data
parsed_reader = reader._parse_header(data)

# Build knowledge graph
from gguf_parser import GGUFKnowledgeExporter
exporter = GGUFKnowledgeExporter(parsed_reader)
nodes = exporter.build()

with open('local_brain.json', 'w') as f:
    json.dump(nodes, f, indent=2)

print(f"\n✅ Saved {len(nodes)} nodes to local_brain.json")
print(f"📊 Total header size: {total/(1024**3):.1f} GB")

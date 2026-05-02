import re
from typing import List

def is_duplicate(new_text: str, existing_texts: List[str], threshold: float = 0.8) -> bool:
    """Cek duplikasi sederhana menggunakan kosinus TF-IDF. 
    Bisa diganti dengan embedding lokal nanti."""
    # Implementasi sederhana: cek substring panjang
    for old in existing_texts:
        if len(new_text) < 100 or len(old) < 100:
            continue
        # Hitung persentase kata yang sama
        new_words = set(new_text.lower().split())
        old_words = set(old.lower().split())
        if not new_words or not old_words:
            continue
        overlap = len(new_words & old_words) / len(new_words | old_words)
        if overlap > threshold:
            return True
    return False

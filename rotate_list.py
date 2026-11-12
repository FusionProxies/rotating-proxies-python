"""Rotate through a proxy list with ProxyRotator.

By default it loads the public free proxy list from github.com/monosans/proxy-list.
Pass your own file (one proxy per line) to use yours.

    pip install -r requirements.txt
    python rotate_list.py [proxies.txt]
"""
import sys

import requests

from proxy_rotator import ProxyRotator

LIST = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"

if len(sys.argv) > 1:
    lines = open(sys.argv[1], encoding="utf-8").read().split()
else:
    lines = requests.get(LIST, timeout=30).text.split()
proxies = [p if "://" in p else "http://" + p for p in lines][:60]
proxies = [p.replace("socks5://", "socks5h://") for p in proxies]  # resolve DNS on the proxy

rotator = ProxyRotator(proxies, max_failures=1, timeout=10)
print(f"loaded {len(proxies)} proxies")
for i in range(5):
    try:
        r = rotator.get("https://ipinfo.io/json")
        d = r.json()
        print(f"request {i + 1}: exit IP {d.get('ip')} ({d.get('country')})")
    except RuntimeError as e:
        print(f"request {i + 1}: {e}")
print(rotator.stats())

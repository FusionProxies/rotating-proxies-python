"""The other way to rotate: a rotating residential gateway does it for you.

One endpoint, a new residential IP on every connection, no list to maintain.
Sticky sessions keep an IP when you need it.

    export FUSION_USER=... FUSION_PASS=...
    python rotate_gateway.py
"""
import os
import random

import requests

USER, PASS = os.environ["FUSION_USER"], os.environ["FUSION_PASS"]
GATEWAY = "resi.fusionproxy.net:12286"


def get_ip(username: str) -> str:
    proxy = f"http://{username}:{PASS}@{GATEWAY}"
    for attempt in range(3):  # residential devices can drop a connection; retry once or twice
        try:
            with requests.Session() as s:  # new session = new connection = new IP
                return s.get("https://ipinfo.io/ip", proxies={"http": proxy, "https": proxy}, timeout=30).text.strip()
        except requests.RequestException:
            if attempt == 2:
                raise


print("rotating:", [get_ip(f"{USER}-country-us") for _ in range(4)])
sid = random.randint(1000000, 9999999)
print("sticky:  ", [get_ip(f"{USER}-country-us-sessid-{sid}-sessTime-600s") for _ in range(4)])

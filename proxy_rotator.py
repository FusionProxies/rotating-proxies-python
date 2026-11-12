"""ProxyRotator: rotate through a list of proxies, retire dead ones, rest blocked ones.

    from proxy_rotator import ProxyRotator

    rotator = ProxyRotator(["http://1.2.3.4:8080", "socks5h://5.6.7.8:1080"])
    r = rotator.get("https://example.com")      # tries proxies until one works
    print(rotator.stats())
"""
import random
import threading
import time

import requests

BLOCK_CODES = {403, 407, 429}


class ProxyRotator:
    def __init__(self, proxies: list[str], max_failures: int = 3, cooldown: float = 300, timeout: float = 15):
        self.proxies = {p: {"fails": 0, "ok": 0, "rest_until": 0.0} for p in proxies}
        self.max_failures = max_failures  # consecutive failures before a proxy is retired
        self.cooldown = cooldown          # seconds a blocked proxy rests before it is used again
        self.timeout = timeout
        self._lock = threading.Lock()
        self._order = list(self.proxies)
        random.shuffle(self._order)
        self._i = 0

    def next_proxy(self) -> str | None:
        """Round-robin over proxies that are alive and not resting."""
        with self._lock:
            now = time.time()
            for _ in range(len(self._order)):
                p = self._order[self._i % len(self._order)]
                self._i += 1
                s = self.proxies[p]
                if s["fails"] < self.max_failures and s["rest_until"] <= now:
                    return p
            return None

    def report(self, proxy: str, ok: bool, blocked: bool = False) -> None:
        with self._lock:
            s = self.proxies[proxy]
            if ok:
                s["ok"] += 1
                s["fails"] = 0
            elif blocked:
                s["rest_until"] = time.time() + self.cooldown  # the site blocked this IP: rest it
            else:
                s["fails"] += 1                                 # network failure: count toward retirement

    def get(self, url: str, attempts: int = 10, **kwargs) -> requests.Response:
        """GET through the next healthy proxy, moving on after failures and blocks."""
        last_error = None
        for _ in range(attempts):
            proxy = self.next_proxy()
            if proxy is None:
                break
            try:
                r = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=self.timeout, **kwargs)
            except requests.RequestException as e:
                self.report(proxy, ok=False)
                last_error = e
                continue
            if r.status_code in BLOCK_CODES:
                self.report(proxy, ok=False, blocked=True)
                last_error = RuntimeError(f"HTTP {r.status_code} via {proxy}")
                continue
            self.report(proxy, ok=True)
            return r
        raise RuntimeError(f"no proxy worked after {attempts} attempts: {last_error}")

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            alive = [p for p, s in self.proxies.items() if s["fails"] < self.max_failures]
            resting = [p for p in alive if self.proxies[p]["rest_until"] > now]
            return {"total": len(self.proxies), "alive": len(alive), "resting": len(resting),
                    "retired": len(self.proxies) - len(alive)}

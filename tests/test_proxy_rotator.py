"""Tests for ProxyRotator. No network: requests.get is replaced by a fake."""
import sys
import threading
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import proxy_rotator  # noqa: E402
from proxy_rotator import ProxyRotator  # noqa: E402

PROXIES = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]


class FakeResponse:
    def __init__(self, status):
        self.status_code = status


def fake_get(behaviour, calls):
    """behaviour: proxy -> status code, or an exception instance to raise."""
    def get(url, proxies=None, timeout=None, **kwargs):
        proxy = proxies["https"]
        calls.append(proxy)
        what = behaviour[proxy]
        if isinstance(what, Exception):
            raise what
        return FakeResponse(what)
    return get


def test_round_robin_uses_every_proxy():
    r = ProxyRotator(PROXIES)
    assert sorted(r.next_proxy() for _ in PROXIES) == sorted(PROXIES)


def test_dead_proxy_is_retired_after_max_failures(monkeypatch):
    calls = []
    behaviour = {"http://p1:8080": requests.ConnectionError("refused"), "http://p2:8080": 200, "http://p3:8080": 200}
    monkeypatch.setattr(proxy_rotator.requests, "get", fake_get(behaviour, calls))
    r = ProxyRotator(PROXIES, max_failures=2)
    for _ in range(10):
        assert r.get("https://example.com/").status_code == 200
    assert calls.count("http://p1:8080") == 2  # tried twice, then never again
    assert r.stats() == {"total": 3, "alive": 2, "resting": 0, "retired": 1}


def test_blocked_proxy_rests_and_comes_back(monkeypatch):
    calls = []
    behaviour = {"http://p1:8080": 429, "http://p2:8080": 200, "http://p3:8080": 200}
    monkeypatch.setattr(proxy_rotator.requests, "get", fake_get(behaviour, calls))
    clock = [1000.0]
    monkeypatch.setattr(proxy_rotator.time, "time", lambda: clock[0])
    r = ProxyRotator(PROXIES, cooldown=300)
    for _ in range(6):
        r.get("https://example.com/")
    assert calls.count("http://p1:8080") == 1
    assert r.stats()["resting"] == 1
    clock[0] += 301  # cooldown over: p1 is used again
    behaviour["http://p1:8080"] = 200
    for _ in range(3):
        r.get("https://example.com/")
    assert calls.count("http://p1:8080") == 2 and r.stats()["resting"] == 0


def test_success_resets_the_failure_count():
    r = ProxyRotator(["http://p1:8080"], max_failures=2)
    r.report("http://p1:8080", ok=False)
    r.report("http://p1:8080", ok=True)
    r.report("http://p1:8080", ok=False)
    assert r.next_proxy() == "http://p1:8080"


def test_all_proxies_failing_raises(monkeypatch):
    behaviour = {p: requests.Timeout("slow") for p in PROXIES}
    monkeypatch.setattr(proxy_rotator.requests, "get", fake_get(behaviour, []))
    r = ProxyRotator(PROXIES, max_failures=1)
    with pytest.raises(RuntimeError, match="no proxy worked"):
        r.get("https://example.com/")
    assert r.next_proxy() is None


def test_thread_safe_under_load(monkeypatch):
    calls = []
    lock = threading.Lock()
    behaviour = {p: 200 for p in PROXIES}

    def get(url, proxies=None, timeout=None, **kwargs):
        with lock:
            calls.append(proxies["https"])
        return FakeResponse(behaviour[proxies["https"]])

    monkeypatch.setattr(proxy_rotator.requests, "get", get)
    r = ProxyRotator(PROXIES)
    threads = [threading.Thread(target=lambda: [r.get("https://example.com/") for _ in range(50)]) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 400
    assert all(abs(calls.count(p) - 400 / 3) <= 2 for p in PROXIES)  # round robin stays even

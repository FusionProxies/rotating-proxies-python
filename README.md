<p align="center">
  <a href="https://fusionproxy.net/?utm_source=github&utm_medium=rotating-proxies-python">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-dark.png">
      <img src="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-light.png" alt="Fusion Proxy" height="52">
    </picture>
  </a>
</p>

# Rotating proxies in Python

Two ways to send each request from a different IP in Python:

1. **Rotate a proxy list yourself**: [`proxy_rotator.py`](proxy_rotator.py) is a small, thread-safe `ProxyRotator` (about 80 lines, only `requests`) that cycles through your proxies, **retires dead ones**, **rests blocked ones** and retries the request on the next proxy.
2. **Use a rotating gateway**: one endpoint that hands out a new residential IP per connection, with sticky sessions when you need to keep one.

```bash
pip install -r requirements.txt
python rotate_list.py                 # rotates the free proxy list
python rotate_gateway.py              # rotating residential gateway (FUSION_USER, FUSION_PASS)
```

## 1. Rotate a list with ProxyRotator

```python
from proxy_rotator import ProxyRotator

rotator = ProxyRotator([
    "http://203.0.113.10:8080",
    "socks5h://198.51.100.7:1080",
    "http://user:pass@192.0.2.44:3128",
])

r = rotator.get("https://example.com")   # tries proxies until one works
print(rotator.stats())                   # {'total': 3, 'alive': 2, 'resting': 1, 'retired': 1}
```

What it does for every request:

| Outcome | Action |
|---|---|
| Success | Count it, reset the proxy's failure counter |
| Connection error or timeout | Count a failure; after `max_failures` in a row the proxy is retired |
| `403`, `407` or `429` | The site blocked this IP: the proxy rests for `cooldown` seconds, then comes back |

Then it moves on to the next proxy, up to `attempts` times. Proxies are taken round-robin from a shuffled list, so the load spreads evenly, and the class is safe to share between threads.

`rotate_list.py` runs it against the first 60 proxies of a public free proxy list ([monosans/proxy-list](https://github.com/monosans/proxy-list) by default). Real output:

```
loaded 60 proxies
request 1: exit IP 45.174.243.96 (MX)
request 2: no proxy worked after 10 attempts: HTTP 429 via socks5h://161.35.70.249:1080
request 3: exit IP 165.99.90.12 (BD)
request 4: exit IP 156.59.69.150 (HK)
request 5: no proxy worked after 10 attempts: HTTP 429 via socks5h://180.222.187.50:10800
{'total': 60, 'alive': 43, 'resting': 16, 'retired': 17}
```

That is the honest picture of free proxies: a quarter dead within hours, many already rate-limited by popular sites, random countries. The rotator handles it, but you pay in failed attempts and time.

## 2. Use a rotating gateway

A rotating residential gateway does the rotation on its side. Every new connection gets a new household IP from the country you choose, and there is no list to check or refresh:

```python
proxy = "http://USERNAME-country-us:PASSWORD@resi.fusionproxy.net:12286"
requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=30)
```

Need the same IP for a while (logins, carts, multi-page flows)? Add a session ID:

```python
proxy = "http://USERNAME-country-us-sessid-4821937-sessTime-600s:PASSWORD@resi.fusionproxy.net:12286"
```

`rotate_gateway.py`:

```
rotating: ['23.125.82.189', '47.201.170.57', '100.15.55.71', '75.65.237.101']
sticky:   ['75.201.158.13', '75.201.158.13', '75.201.158.13', '75.201.158.13']
```

`requests.Session` keeps connections open, and a kept connection keeps its IP. Use a new session (or no session) when you want a new IP, and one session with a sticky username when you want to keep it.

## Which one?

| | Your own list + ProxyRotator | Rotating gateway |
|---|---|---|
| Setup | Find and check proxies, refresh the list | One endpoint |
| IP quality | Whatever you have; free lists are slow and widely blocked | Residential IPs |
| Location | Whatever the list has | Country, state or city you choose |
| Keep an IP | Pin a proxy yourself | `-sessid-` in the username |
| Cost | Free or per proxy | Per GB |

## Related

- [proxy-checker](https://github.com/FusionProxies/proxy-checker): check a list before you rotate it
- [python-requests-retry](https://github.com/FusionProxies/python-requests-retry): retries and backoff
- [python-async-scraping](https://github.com/FusionProxies/python-async-scraping): many requests at once

[Fusion Proxy rotating residential proxies](https://fusionproxy.net/proxies/rotating?utm_source=github&utm_medium=rotating-proxies-python) from $2.95/GB, with a [free trial](https://fusionproxy.net/free-trial?utm_source=github&utm_medium=rotating-proxies-python).

## License

MIT, see [LICENSE](LICENSE).

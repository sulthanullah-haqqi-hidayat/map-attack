import requests
import time

_cache = {}

def ip_to_latlng(ip):
    if ip in _cache:
        return _cache[ip]
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
        res = r.json()
        lat, lon = res.get("lat"), res.get("lon")
        if lat is not None and lon is not None:
            _cache[ip] = (lat, lon)
            return lat, lon
    except Exception:
        pass
    return None, None

def batch_ip_to_latlng(ip_list):
    # Simple batching with sleep to avoid quota limit
    result = {}
    for ip in ip_list:
        lat, lon = ip_to_latlng(ip)
        result[ip] = (lat, lon)
        time.sleep(1)  # avoid quota ban
    return result

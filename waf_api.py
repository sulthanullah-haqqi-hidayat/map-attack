import requests

API_URL = "https://ALAMAT API SAFALINE/api/open/records"
TOKEN = "TOKEN API SAFELINE"

headers = {
    "X-SLCE-API-TOKEN": TOKEN
}

def fetch_attack_logs(page_size=20, page=1):
    params = {"page_size": page_size, "page": page}
    resp = requests.get(API_URL, headers=headers, params=params)
    data = resp.json()
    # Perbaikan di sini
    return data.get("data", {}).get("data", [])


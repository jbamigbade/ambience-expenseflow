import httpx
import json

url = "https://expense-manager-dashboard-654812449031.us-west1.run.app/api/pending"
try:
    print("Fetching pending approvals (this may take up to a minute due to sequential API calls)...")
    resp = httpx.get(url, timeout=120.0)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print("Error:", e)


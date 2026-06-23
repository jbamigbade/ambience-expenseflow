import urllib.request
import urllib.error
import json

url = "https://expense-manager-dashboard-654812449031.us-west1.run.app/api/pending"
print(f"Connecting to {url}...")
try:
    with urllib.request.urlopen(url, timeout=20) as response:
        status = response.getcode()
        body = response.read().decode('utf-8')
        data = json.loads(body)
        print(f"Status: {status}")
        print(f"Total pending claims: {len(data.get('pending_claims', []))}")
        print(f"Sample claim keys: {list(data.get('pending_claims', [{}])[0].keys())}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    print(e.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print(f"Error: {e}")

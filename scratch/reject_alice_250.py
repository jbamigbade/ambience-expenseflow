import httpx
import json

session_id = "1896927488018219008"
url = f"https://expense-manager-dashboard-654812449031.us-west1.run.app/api/action/{session_id}"

payload = {
    "approved": False,
    "interrupt_id": "review_decision"
}

try:
    print(f"Rejecting session {session_id} via dashboard...")
    resp = httpx.post(url, json=payload, timeout=60.0)
    print(f"Status: {resp.status_code}")
    print(resp.text)
except Exception as e:
    print("Error:", e)

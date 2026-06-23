import urllib.request
import sys

url = "https://expense-manager-dashboard-654812449031.us-west1.run.app"

print("Starting Cloud Run verification...")

# 1. Verify /login
try:
    req = urllib.request.Request(f"{url}/login", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        status = response.status
        html = response.read().decode('utf-8')
        print(f"[/login] Status code: {status}")
        if status == 200:
            print("[/login] SUCCESS: Endpoint returned HTTP 200!")
        else:
            print(f"[/login] FAILURE: Expected 200, got {status}")
            sys.exit(1)
            
        # Verify login page contains the expected references
        if "login-google" in html or "Google" in html:
            print("[/login] SUCCESS: Login page correctly renders Google OAuth sign-in buttons!")
        else:
            print("[/login] WARNING: Google sign-in buttons not found in HTML!")
except Exception as e:
    print(f"[/login] ERROR hitting endpoint: {e}")
    sys.exit(1)

print("\nAll programmatic endpoint checks completed!")

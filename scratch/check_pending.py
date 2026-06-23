import urllib.request
import json
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    url = "https://expense-manager-dashboard-654812449031.us-west1.run.app/api/pending"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        print("Sending request to dashboard /api/pending...")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("Successfully fetched.")
            print(f"Total pending claims: {len(data.get('pending_claims', []))}")
            print(f"Hidden CLI sessions count: {data.get('hidden_cli_sessions_count')}")
            
            for idx, claim in enumerate(data.get('pending_claims', []), start=1):
                print(f"\n[{idx}] Claim Detail:")
                print(f"  - Session ID: {claim.get('session_id')}")
                print(f"  - Submitter: {claim.get('employee_name')}")
                print(f"  - Category: {claim.get('category')}")
                print(f"  - Amount: ${claim.get('amount')}")
                print(f"  - Description: '{claim.get('description')}'")
                print(f"  - Office Receipt URL: {claim.get('office_receipt_url')}")
                print(f"  - Parking Receipt URL: {claim.get('parking_receipt_url')}")
                print(f"  - Manager Approval Letter: {claim.get('manager_approval_letter_url')}")
                print(f"  - Business Purpose: {claim.get('business_purpose')}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()

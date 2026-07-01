import json
import subprocess
import time
import urllib.request
import urllib.parse
import uuid
import sys
import shutil

# Project configuration
PROJECT = "project-5d38f91a-29a3-45bd-8d4"
TOPIC = "expense-reports"
BASE_URL = "https://expense-manager-dashboard-654812449031.us-west1.run.app"
GCLOUD = shutil.which("gcloud") or shutil.which("gcloud.cmd") or r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Dummy attachment content
DUMMY_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"

def http_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"GET {url} failed: {e}")
        return None

def http_post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"POST {url} failed: {e}")
        return None

def create_multipart_body(files):
    boundary = b'----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = []
    for key, (filename, content, content_type) in files.items():
        body.append(b'--' + boundary)
        body.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode('utf-8'))
        body.append(f'Content-Type: {content_type}'.encode('utf-8'))
        body.append(b'')
        body.append(content)
    body.append(b'--' + boundary + b'--')
    body.append(b'')
    return b'\r\n'.join(body), f'multipart/form-data; boundary={boundary.decode("utf-8")}'

def http_post_multipart(endpoint, files):
    url = f"{BASE_URL}{endpoint}"
    body, content_type = create_multipart_body(files)
    req = urllib.request.Request(url, data=body, headers={'Content-Type': content_type})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"POST MULTIPART {url} failed: {e}")
        return None

def publish_expense(payload):
    # Wrap in standard ADK runtime structure
    message = json.dumps({
        "input": {
            "message": json.dumps(payload),
            "user_id": "default-user"
        }
    })
    
    print(f"Publishing event for claimant: {payload['employee_name']} of amount: ${payload['amount']}...")
    subprocess.run([
        GCLOUD,
        "pubsub",
        "topics",
        "publish",
        TOPIC,
        f"--project={PROJECT}",
        f"--message={message}"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Event published successfully.")

def poll_pending_claims(claimant, max_retries=15, sleep_sec=3):
    print(f"Waiting for claim for '{claimant}' to appear in /api/pending...")
    for i in range(max_retries):
        time.sleep(sleep_sec)
        pending = http_get("/api/pending")
        if not pending:
            continue
        claims = pending.get("pending_claims", [])
        for c in claims:
            if c.get("employee_name") == claimant:
                print(f"Found claim! Session ID: {c.get('session_id')}, Amount: ${c.get('amount')}, Policy Status: {c.get('policy_status')}")
                return c
    return None

def poll_firestore_status(claim_id, target_statuses, max_retries=15, sleep_sec=3):
    print(f"Waiting for claim_id {claim_id} to reach statuses {target_statuses} in Firestore...")
    for i in range(max_retries):
        time.sleep(sleep_sec)
        expenses = http_get("/api/expenses")
        if not expenses:
            continue
        for e in expenses:
            if e.get("claim_id") == claim_id or e.get("session_id") == claim_id:
                status = e.get("status")
                print(f"Current status: {status} (claim_id: {e.get('claim_id')})")
                if status in target_statuses:
                    return e
    return None

def run_tests():
    print("==================================================")
    print("STARTING E2E VERIFICATION TEST FOR PHASE 2 PERSISTENCE")
    print("==================================================")
    
    # --------------------------------------------------
    # TEST A: Under-$100 expense (Auto-approved by AI, stored in Firestore)
    # --------------------------------------------------
    print("\n--- TEST A: Under-$100 Expense (Auto-approval flow) ---")
    test_a_id = f"test_a_{int(time.time())}"
    claimant_a = f"auto.approved.{test_a_id}@company.com"
    payload_a = {
        "claim_id": test_a_id,
        "employee_name": claimant_a,
        "amount": 45.50,
        "category": "printer_ink",
        "description": "Tutoring center printer ink",
        "business_purpose": "Ink for student worksheets",
        "office_receipt_url": "https://example.com/mock-receipt.pdf"
    }
    
    publish_expense(payload_a)
    
    # Under $100 should be auto-approved by the agent runtime directly without human intervention
    # Let's poll /api/expenses directly (which triggers sync_completed_sessions) to verify it is auto_approved
    claim_a = poll_firestore_status(test_a_id, ["auto_approved", "approved"], max_retries=20, sleep_sec=5)
    if claim_a:
        print(f"SUCCESS: Test A auto-approved! Final Status: {claim_a.get('status')}")
    else:
        print("ERROR: Test A failed to reach auto-approved status in Firestore.")
        
    # --------------------------------------------------
    # TEST B: High-value expense ($700 travel compliant, approved by manager)
    # --------------------------------------------------
    print("\n--- TEST B: High-Value Expense ($700 Compliant Approval) ---")
    test_b_id = f"test_b_{int(time.time())}"
    claimant_b = f"compliant.{test_b_id}@company.com"
    payload_b = {
        "claim_id": test_b_id,
        "employee_name": claimant_b,
        "amount": 700.00,
        "category": "hotel",
        "description": "3 nights hotel stay in Seattle",
        "business_purpose": "Attend annual education conference",
        "check_in_date": "2026-07-10",
        "check_out_date": "2026-07-13", # 3 nights, 700 / 3 = 233.33/night (below 350 limit, compliant)
        "hotel_receipt_url": "https://example.com/hotel-receipt.pdf"
    }
    
    publish_expense(payload_b)
    
    # Wait for it to appear in pending claims
    claim_b_pending = poll_pending_claims(claimant_b)
    if not claim_b_pending:
        print("ERROR: Test B claim did not appear in /api/pending!")
        return
        
    session_id_b = claim_b_pending["session_id"]
    print(f"Test B claim is pending. Initiating Human Approval action for session {session_id_b}...")
    
    action_url = f"/api/action/{session_id_b}"
    action_payload = {
        "approved": True,
        "interrupt_id": claim_b_pending["interrupt_id"]
    }
    action_resp = http_post_json(action_url, action_payload)
    print(f"Approval action response: {action_resp}")
    
    # Now verify in Firestore that status is "approved"
    claim_b_final = poll_firestore_status(session_id_b, ["approved"], max_retries=10, sleep_sec=3)
    if claim_b_final:
        print(f"SUCCESS: Test B status is approved in Firestore!")
        # Fetch detailed record
        details = http_get(f"/api/expenses/{claim_b_final['claim_id']}")
        if details:
            print(f" -> Firestore Documents linked: {len(details.get('documents', []))}")
            print(f" -> Firestore Decisions recorded: {len(details.get('decisions', []))}")
            print(f" -> Firestore Audit timeline records: {len(details.get('audit_logs', []))}")
    else:
        print("ERROR: Test B status was not updated to approved in Firestore.")

    # --------------------------------------------------
    # TEST C: Missing document expense (Flight > $1200 missing approval letter)
    # --------------------------------------------------
    print("\n--- TEST C: Missing Document Expense (Flight > $1200 block/upload/approve) ---")
    test_c_id = f"test_c_{int(time.time())}"
    claimant_c = f"flight.blocked.{test_c_id}@company.com"
    payload_c = {
        "claim_id": test_c_id,
        "employee_name": claimant_c,
        "amount": 1500.00,
        "category": "flight",
        "description": "Cross-country business class flight",
        "business_purpose": "Consulting onsite with client",
        "flight_ticket_receipt_url": "https://example.com/flight-receipt.pdf"
        # Missing manager_approval_letter_url! Should trigger block!
    }
    
    publish_expense(payload_c)
    
    # Wait for it to appear in pending claims
    claim_c_pending = poll_pending_claims(claimant_c)
    if not claim_c_pending:
        print("ERROR: Test C claim did not appear in /api/pending!")
        return
        
    session_id_c = claim_c_pending["session_id"]
    
    # Fetch from Firestore using GET /api/expenses/{test_c_id} to check policy status and missing documents
    time.sleep(2) # Wait for Firestore sync to settle
    claim_c_firestore = http_get(f"/api/expenses/{test_c_id}")
    if claim_c_firestore and "expense" in claim_c_firestore:
        expense_c = claim_c_firestore["expense"]
        print(f"Test C Firestore Policy Status: {expense_c.get('policy_status')}")
        print(f"Test C Firestore Missing Documents: {expense_c.get('missing_documents')}")
        if "Manager Approval Letter" in expense_c.get("missing_documents", []):
            print("SUCCESS: Flight is correctly flagged as missing Manager Approval Letter.")
        else:
            print(f"ERROR: Flight was not flagged with missing Manager Approval Letter in Firestore. Missing: {expense_c.get('missing_documents')}")
    else:
        print("ERROR: Could not fetch Test C from Firestore.")
        
    # Let's upload the required document
    print(f"Uploading manager_approval_letter for session {session_id_c}...")
    upload_url = f"/api/upload/{session_id_c}/manager_approval_letter"
    files = {
        "file": ("signed_approval_letter.pdf", DUMMY_PDF_CONTENT, "application/pdf")
    }
    upload_resp = http_post_multipart(upload_url, files)
    print(f"Upload Response: {upload_resp}")
    
    # Re-fetch pending claim to confirm missing_documents is empty and policy_status becomes COMPLIANT/pending_review
    time.sleep(3)
    pending_refetched = http_get("/api/pending")
    claim_c_updated = None
    for c in pending_refetched.get("pending_claims", []):
        if c.get("session_id") == session_id_c:
            claim_c_updated = c
            break
            
    if claim_c_updated:
        print(f"Updated Missing Documents: {claim_c_updated.get('missing_documents')}")
        print(f"Updated Policy Status: {claim_c_updated.get('policy_status')}")
        assert not claim_c_updated.get("missing_documents"), "Error: Missing documents still present!"
        print("SUCCESS: Missing documents now satisfied! Human approval button is now enabled.")
    else:
        print("ERROR: Could not re-fetch Test C from pending queue!")
        return
        
    # Let's Approve it!
    print(f"Initiating approval action for Test C...")
    action_url_c = f"/api/action/{session_id_c}"
    action_payload_c = {
        "approved": True,
        "interrupt_id": claim_c_updated["interrupt_id"]
    }
    action_resp_c = http_post_json(action_url_c, action_payload_c)
    print(f"Approval action response: {action_resp_c}")
    
    # Now verify in Firestore that status is "approved"
    claim_c_final = poll_firestore_status(session_id_c, ["approved"], max_retries=10, sleep_sec=3)
    if claim_c_final:
        print(f"SUCCESS: Test C is approved in Firestore after uploading document!")
    else:
        print("ERROR: Test C failed to transition to approved in Firestore.")

    # --------------------------------------------------
    # TEST D: Rejected expense (Parking citation)
    # --------------------------------------------------
    print("\n--- TEST D: Rejected Expense (Parking Citation Reject) ---")
    test_d_id = f"test_d_{int(time.time())}"
    claimant_d = f"citation.reject.{test_d_id}@company.com"
    payload_d = {
        "claim_id": test_d_id,
        "employee_name": claimant_d,
        "category": "parking_citation",
        "amount": 75.00,
        "description": "Parking citation on business trip",
        "business_purpose": "Attending meeting"
        # No manager_approval_letter_url! Parking citation without letter is non-reimbursable.
    }
    
    publish_expense(payload_d)
    
    # Wait for it to appear in pending claims
    claim_d_pending = poll_pending_claims(claimant_d)
    if not claim_d_pending:
        print("ERROR: Test D claim did not appear in /api/pending!")
        return
        
    session_id_d = claim_d_pending["session_id"]
    print(f"Test D claim is pending. Rejecting claim for session {session_id_d}...")
    
    action_url_d = f"/api/action/{session_id_d}"
    action_payload_d = {
        "approved": False,
        "interrupt_id": claim_d_pending["interrupt_id"]
    }
    action_resp_d = http_post_json(action_url_d, action_payload_d)
    print(f"Reject action response: {action_resp_d}")
    
    # Verify in Firestore that status is "rejected"
    claim_d_final = poll_firestore_status(session_id_d, ["rejected"], max_retries=10, sleep_sec=3)
    if claim_d_final:
        print(f"SUCCESS: Test D is rejected in Firestore!")
        # Verify decision and audit log
        details_d = http_get(f"/api/expenses/{claim_d_final['claim_id']}")
        if details_d:
            decisions = details_d.get("decisions", [])
            if decisions:
                print(f" -> Decision recorded: {decisions[0].get('decision')} by {decisions[0].get('decided_by')} for reason {decisions[0].get('decision_reason')}")
                print(f" -> AI agent response text: {decisions[0].get('final_agent_response')}")
    else:
        print("ERROR: Test D failed to transition to rejected in Firestore.")

if __name__ == "__main__":
    run_tests()

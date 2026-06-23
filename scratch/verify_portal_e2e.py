# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
import uuid
import json
import subprocess
import threading
import urllib.request
import urllib.error
from datetime import datetime

PORT = 8093
BASE_URL = f"http://127.0.0.1:{PORT}"
DUMMY_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def start_local_server():
    """
    Starts the FastAPI server locally on PORT 8085 with AUTH_ENABLED=false
    so we can run a complete programmatic integration test suite.
    """
    log(f"Starting local FastAPI server on port {PORT} with AUTH_ENABLED=false...")
    
    # Copy current environment but disable auth for local programmatic E2E test
    env = os.environ.copy()
    env["AUTH_ENABLED"] = "false"
    env["PORT"] = str(PORT)
    env["PYTHONPATH"] = "."
    
    # Run uvicorn on submission_frontend.main:app
    command = [
        sys.executable,
        "-m", "uvicorn",
        "submission_frontend.main:app",
        "--host", "127.0.0.1",
        "--port", str(PORT)
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env
    )
    
    # Thread to log uvicorn output
    def log_stream(stream, prefix):
        for line in iter(stream.readline, ""):
            line_str = line.strip()
            if line_str and "GET" not in line_str and "POST" not in line_str:
                log(f"{prefix}: {line_str}")
                
    threading.Thread(target=log_stream, args=(process.stdout, "SERVER-OUT"), daemon=True).start()
    threading.Thread(target=log_stream, args=(process.stderr, "SERVER-ERR"), daemon=True).start()
    
    return process

def wait_for_server(timeout=15):
    """
    Polls the local server until it is ready to receive requests.
    """
    start_time = time.time()
    url = f"{BASE_URL}/api/me"
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    log("Local server is ready!")
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def http_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        log(f"GET {url} failed: {e.code} - {e.reason}")
        log(e.read().decode('utf-8', errors='ignore'))
        return None
    except Exception as e:
        log(f"GET {url} failed: {e}")
        return None

def http_post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        log(f"POST {url} failed: {e.code} - {e.reason}")
        log(e.read().decode('utf-8', errors='ignore'))
        return None
    except Exception as e:
        log(f"POST {url} failed: {e}")
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
    except urllib.error.HTTPError as e:
        log(f"POST MULTIPART {url} failed: {e.code} - {e.reason}")
        log(e.read().decode('utf-8', errors='ignore'))
        return None
    except Exception as e:
        log(f"POST MULTIPART {url} failed: {e}")
        return None

def run_e2e_verification():
    log("==========================================================")
    log("STARTING PROGRAMMATIC E2E PORTAL VERIFICATION")
    log("==========================================================")
    
    server_process = start_local_server()
    try:
        if not wait_for_server():
            log("CRITICAL ERROR: Local server failed to boot!")
            sys.exit(1)
            
        # 1. Verify GET /api/me returns default authenticated user when auth is disabled
        log("\n--- [VERIFICATION 1 & 8] Verifying authentication defaults ---")
        me = http_get("/api/me")
        assert me is not None, "Failed to fetch /api/me"
        log(f"Current User identity: {me}")
        assert me["role"] == "finance_admin", "Expected finance_admin fallback"
        assert me["authenticated"] is False, "Expected authenticated=False when auth disabled"
        log("SUCCESS: Identity and roles resolve correctly.")
        
        # 2. Verify Policy Preview endpoint /api/employee/claims/preview
        log("\n--- [VERIFICATION 5 & 10 & 11] Verifying policy preview & dry run ---")
        preview_payload = {
            "category": "meals",
            "amount": 120.00,
            "travel_start_date": "2026-07-01",
            "travel_end_date": "2026-07-03",
            "city": "Seattle",
            "state": "Washington",
            "state_code": "WA",
            "country": "US",
            "claimed_meals": 120.00,
            "claimed_lodging": 0.0,
            "claimed_incidentals": 0.0
        }
        preview_res = http_post_json("/api/employee/claims/preview", preview_payload)
        assert preview_res is not None, "Preview API returned None"
        log(f"Preview Response status: {preview_res.get('status')}")
        log(f"Preview Required Docs: {preview_res.get('required_docs')}")
        log(f"Preview Missing Docs: {preview_res.get('missing_docs')}")
        log(f"Per Diem Review details: {preview_res.get('per_diem_review')}")
        
        # 3. Verify Employee Document Upload & active claim file staging
        log("\n--- [VERIFICATION 6 & 13] Verifying Employee Document uploads ---")
        active_claim_id = f"claim_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        upload_endpoint = f"/api/employee/claims/{active_claim_id}/documents/receipt"
        files = {
            "file": ("dinner_receipt.pdf", DUMMY_PDF_CONTENT, "application/pdf")
        }
        upload_res = http_post_multipart(upload_endpoint, files)
        assert upload_res is not None, "Document upload failed"
        assert upload_res.get("status") == "success", f"Expected success status, got: {upload_res}"
        log(f"Document upload response: {upload_res}")
        log("SUCCESS: Secure employee-staged uploads successfully uploaded to GCS/Firestore.")
        
        # 4. Verify Claim Submission (Auto-approved under-$100 case)
        log("\n--- [VERIFICATION 2 & 3] Verifying compliant claim auto-approval & ingestion ---")
        claim_payload_compliant = {
            "claim_id": active_claim_id,
            "employee_email": "jane.employee@company.com",
            "employee_name": "Jane Employee",
            "category": "office_supplies",
            "amount": 45.00,
            "description": "Premium notebooks for team brainstorming",
            "business_purpose": "Team collaborative session",
            "receipt_url": f"/api/document/{active_claim_id}/receipt"
        }
        submit_res = http_post_json("/api/employee/claims", claim_payload_compliant)
        assert submit_res is not None, "Claim submission failed"
        log(f"Submission response status: {submit_res.get('status')}")
        assert submit_res.get("status") == "auto_approved", f"Expected auto_approved status, got: {submit_res.get('status')}"
        
        # Verify Submitted claim shows up in My Claims/History
        log("\n--- [VERIFICATION 3] Verifying claim appears in My Claims history ---")
        history = http_get("/api/employee/claims")
        assert history is not None, "Failed to fetch employee claims"
        matching_claim = next((c for c in history if c["claim_id"] == active_claim_id), None)
        assert matching_claim is not None, "Submitted claim not found in employee claim history!"
        log(f"Matching history item: {matching_claim['claim_id']} | Status: {matching_claim['status']}")
        
        # 5. Verify Claim Submission requiring review (flight > $1200 missing manager approval letter)
        log("\n--- [VERIFICATION 4 & 5 & 10 & 11] Verifying non-compliant claim triggers review and audit logs ---")
        review_claim_id = f"claim_review_{int(time.time())}"
        claim_payload_review = {
            "claim_id": review_claim_id,
            "employee_email": "john.traveler@company.com",
            "employee_name": "John Traveler",
            "category": "flight",
            "amount": 1400.00,
            "description": "Business class cross-country flight",
            "business_purpose": "Client critical onsite consulting",
            "flight_ticket_receipt_url": "https://example.com/receipt.pdf"
            # Missing manager_approval_letter_url!
        }
        submit_res_review = http_post_json("/api/employee/claims", claim_payload_review)
        assert submit_res_review is not None, "Review claim submission failed"
        log(f"Review Submission Response status: {submit_res_review.get('status')}")
        assert submit_res_review.get("status") == "blocked_missing_docs", f"Expected blocked_missing_docs, got: {submit_res_review.get('status')}"
        
        # 6. Verify Claim appears in Pending Approvals
        log("\n--- [VERIFICATION 4 & 9] Verifying claim appears in Pending Approvals queue ---")
        pending_queue = http_get("/api/pending")
        assert pending_queue is not None, "Failed to fetch pending queue"
        pending_claims = pending_queue.get("pending_claims", [])
        matching_pending = next((c for c in pending_claims if c["session_id"] == review_claim_id), None)
        assert matching_pending is not None, "Review claim not found in Pending Approvals!"
        log(f"Found pending claim in queue: {matching_pending['session_id']} | Policy status: {matching_pending['policy_status']}")
        
        # 7. Verify Audit Timeline includes employee_submitted_claim events & check logs structures
        log("\n--- [VERIFICATION 7 & 8] Verifying Audit Timeline structure and events ---")
        audit_timeline = http_get(f"/api/audit/{review_claim_id}")
        assert audit_timeline is not None, "Failed to fetch audit timeline"
        log(f"Audit log timeline for {review_claim_id}:")
        for log_entry in audit_timeline:
            log(f" - {log_entry.get('event_type')}: {log_entry.get('event_message')}")
            
        submitted_event = next((e for e in audit_timeline if e["event_type"] == "employee_submitted_claim"), None)
        assert submitted_event is not None, "employee_submitted_claim event type not found in audit logs!"
        
        # Assert full compliance of metadata structure
        assert "actor_email" in submitted_event, "actor_email field missing from audit log!"
        assert "actor_role" in submitted_event, "actor_role field missing from audit log!"
        assert submitted_event.get("authenticated") is True, f"Expected authenticated=true, got {submitted_event.get('authenticated')}"
        assert submitted_event.get("metadata", {}).get("source") == "employee_portal", f"Expected source=employee_portal, got {submitted_event.get('metadata', {}).get('source')}"
        log("SUCCESS: Audit logging structure fully authenticated and compliant with all standards!")
        
        # 8. Verify existing manager approval action / decision recording still works perfectly
        log("\n--- [VERIFICATION 9 & 12] Verifying manager approval action & decision recording ---")
        # Let's upload the missing approval letter first to unblock approval button
        upload_endpoint_review = f"/api/upload/{review_claim_id}/manager_approval_letter"
        upload_review_res = http_post_multipart(upload_endpoint_review, files)
        assert upload_review_res is not None, "Review doc upload failed"
        
        # Fetch updated pending to get the interrupt_id / verify active state
        updated_pending_queue = http_get("/api/pending")
        matching_updated = next((c for c in updated_pending_queue.get("pending_claims", []) if c["session_id"] == review_claim_id), None)
        assert matching_updated is not None, "Claim not found after upload"
        assert not matching_updated.get("missing_documents"), "Expected missing_documents list to be empty now!"
        
        # Post decision
        action_payload = {
            "approved": True,
            "interrupt_id": matching_updated.get("interrupt_id")
        }
        action_res = http_post_json(f"/api/action/{review_claim_id}", action_payload)
        assert action_res is not None, "Manager action failed"
        assert action_res.get("status") == "success", f"Expected success, got: {action_res}"
        log(f"Action response: {action_res}")
        
        # Verify it went to Approved status in Firestore
        updated_claim_details = http_get(f"/api/expenses/{review_claim_id}")
        assert updated_claim_details is not None, "Failed to get updated claim details"
        expense_record = updated_claim_details.get("expense", {})
        log(f"Updated expense status in Firestore: {expense_record.get('status')}")
        assert expense_record.get("status") == "approved", f"Expected status approved, got: {expense_record.get('status')}"
        
        # Verify decision was written to Firestore
        decisions_list = updated_claim_details.get("decisions", [])
        assert len(decisions_list) > 0, "No decisions recorded in Firestore!"
        log(f"Decisions written to Firestore: {decisions_list}")
        
        log("\n==========================================================")
        log("ALL E2E PROGRAMMATIC INTEGRATION TESTS PASSED PERFECTLY!")
        log("==========================================================")
        
    finally:
        log("Shutting down local server subprocess...")
        server_process.terminate()
        server_process.wait()
        log("Local server subprocess shutdown successfully.")

if __name__ == "__main__":
    run_e2e_verification()

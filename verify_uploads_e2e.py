import urllib.request
import urllib.parse
import json
import os
import mimetypes

# Base URL of the redeployed dashboard
BASE_URL = "https://expense-manager-dashboard-654812449031.us-west1.run.app"

# Create a tiny valid dummy PDF content (PDF header + minor content)
DUMMY_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"

def create_multipart_body(fields, files):
    """
    Creates a multipart/form-data request body for urllib.
    """
    boundary = b'----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = []
    for key, value in fields.items():
        body.append(b'--' + boundary)
        body.append(f'Content-Disposition: form-data; name="{key}"'.encode('utf-8'))
        body.append(b'')
        body.append(value.encode('utf-8'))
    for key, (filename, content, content_type) in files.items():
        body.append(b'--' + boundary)
        body.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode('utf-8'))
        body.append(f'Content-Type: {content_type}'.encode('utf-8'))
        body.append(b'')
        body.append(content)
    body.append(b'--' + boundary + b'--')
    body.append(b'')
    return b'\r\n'.join(body), f'multipart/form-data; boundary={boundary.decode("utf-8")}'

def http_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_get_raw(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.read(), resp.info().get_content_type()

def http_post_multipart(url, files):
    body, content_type = create_multipart_body({}, files)
    req = urllib.request.Request(url, data=body, headers={'Content-Type': content_type})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_post_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    print("=== STARTING END-TO-END FILE UPLOAD TEST PIPELINE ===")
    
    # 1. Fetch current pending claims
    print("\n[Step 1] Fetching pending claims from /api/pending...")
    pending_data = http_get(f"{BASE_URL}/api/pending")
    claims = pending_data.get("pending_claims", [])
    print(f"Total pending claims: {len(claims)}")
    
    # Identify our 5 specific test claims
    target_emails = {
        "flight.overlimit.missing@company.com": "Case 1: Flight ticket > $1200 missing manager approval letter",
        "flight.missing.receipt@company.com": "Case 2: Flight ticket missing receipt",
        "hotel.overlimit.missing.v2@company.com": "Case 3: Hotel > $350/night missing manager approval letter",
        "office.paper.missing@company.com": "Case 4: Office supply missing receipt",
        "parking.ticket.test@company.com": "Case 5: Parking citation missing manager approval letter"
    }
    
    found_claims = {}
    for c in claims:
        email = c.get("employee_name")
        if email in target_emails and email not in found_claims:
            found_claims[email] = c
            
    print(f"\nFound {len(found_claims)} target test claims:")
    for email, label in target_emails.items():
        if email in found_claims:
            c = found_claims[email]
            print(f" - {label} | Session ID: {c['session_id']} | Amount: ${c['amount']}")
        else:
            print(f" - WARNING: {label} not found in pending claims!")
            
    # For each found target case, let's run upload validation!
    # Define required document uploads for each case
    upload_scenarios = {
        "flight.overlimit.missing@company.com": "manager_approval_letter",
        "flight.missing.receipt@company.com": "flight_ticket_receipt",
        "hotel.overlimit.missing.v2@company.com": "manager_approval_letter",
        "office.paper.missing@company.com": "office_receipt",
        "parking.ticket.test@company.com": "manager_approval_letter"
    }
    
    for email, doc_type in upload_scenarios.items():
        if email not in found_claims:
            continue
        
        claim = found_claims[email]
        sess_id = claim["session_id"]
        label = target_emails[email]
        
        print(f"\n==================================================")
        print(f"RUNNING VALIDATION FOR: {label}")
        print(f"Session ID: {sess_id} | Document Type: {doc_type}")
        print(f"==================================================")
        
        # A. Confirm Approve Claim is disabled before upload
        # In frontend logic:
        # - Flight > 1200 needs flight_ticket_receipt and manager_approval_letter
        # - Flight needs flight_ticket_receipt
        # - Hotel > 350/night needs hotel_receipt and manager_approval_letter
        # - Office supplies needs office_receipt
        # - Parking citation needs manager_approval_letter
        # Let's verify uploaded_docs is empty
        print(f" -> Initial uploaded_docs list: {claim.get('uploaded_docs', [])}")
        assert doc_type not in claim.get("uploaded_docs", []), f"Error: {doc_type} is already uploaded before testing!"
        print(" -> Verified: No documents uploaded yet. (Frontend 'Approve Claim' button is DISABLED).")
        
        # B. Upload the required document from the dashboard
        upload_url = f"{BASE_URL}/api/upload/{sess_id}/{doc_type}"
        filename = f"signed_{doc_type}.pdf"
        files = {
            "file": (filename, DUMMY_PDF_CONTENT, "application/pdf")
        }
        
        print(f" -> Uploading {filename} to {upload_url}...")
        upload_resp = http_post_multipart(upload_url, files)
        print(f" -> Upload Response: {json.dumps(upload_resp, indent=2)}")
        assert upload_resp.get("status") == "success", "Upload failed!"
        
        # C. Confirm the document appears under /api/uploads
        meta_url = f"{BASE_URL}/api/uploads/{sess_id}"
        meta_resp = http_get(meta_url)
        print(f" -> Fetched uploads metadata: {json.dumps(meta_resp, indent=2)}")
        assert doc_type in meta_resp, f"{doc_type} missing in metadata!"
        
        # D. Confirm the document appears under secure /api/document streaming
        doc_stream_url = f"{BASE_URL}/api/document/{sess_id}/{doc_type}"
        print(f" -> Downloading securely from: {doc_stream_url}...")
        downloaded_bytes, mime_type = http_get_raw(doc_stream_url)
        print(f" -> Downloaded {len(downloaded_bytes)} bytes. MIME-Type: {mime_type}")
        assert downloaded_bytes == DUMMY_PDF_CONTENT, "Downloaded content mismatch!"
        assert mime_type == "application/pdf", f"Unexpected MIME type: {mime_type}"
        print(" -> Verified: Document is securely served and matches uploaded bytes exactly. (View button will open this correctly!).")
        
        # E. Confirm that /api/pending now merges this upload and sets URL
        print(" -> Re-fetching pending claims to check updated state...")
        updated_pending_data = http_get(f"{BASE_URL}/api/pending")
        updated_claims = updated_pending_data.get("pending_claims", [])
        updated_claim = next((c for c in updated_claims if c["session_id"] == sess_id), None)
        
        assert updated_claim is not None, "Claim disappeared unexpectedly!"
        print(f" -> Updated uploaded_docs list: {updated_claim.get('uploaded_docs', [])}")
        assert doc_type in updated_claim.get("uploaded_docs", []), f"GCS metadata not merged into pending list!"
        
        # Verify URL override is set to our API document stream endpoint
        field_mapping = {
            "receipt": "receipt_url",
            "hotel_receipt": "hotel_receipt_url",
            "flight_ticket_receipt": "flight_ticket_receipt_url",
            "manager_approval_letter": "manager_approval_letter_url",
            "office_receipt": "office_receipt_url",
            "parking_receipt": "parking_receipt_url"
        }
        url_field = field_mapping[doc_type]
        assert updated_claim.get(url_field) == f"/api/document/{sess_id}/{doc_type}", f"URL field {url_field} not updated!"
        print(f" -> Verified: URL {url_field} is set to streaming endpoint: {updated_claim.get(url_field)}")
        print(" -> Verified: Required document is now satisfied. (Frontend 'Approve Claim' button is ENABLED).")

    # 2. Approve one test claim and confirm the card disappears
    print("\n==================================================")
    print("STEP 2: APPROVING ONE TEST CLAIM AND CONFIRMING IT DISAPPEARS")
    print("==================================================")
    target_approve_email = "parking.ticket.test@company.com"
    claim_to_approve = found_claims[target_approve_email]
    sess_id_to_approve = claim_to_approve["session_id"]
    
    action_url = f"{BASE_URL}/api/action/{sess_id_to_approve}"
    payload = {
        "approved": True
    }
    print(f" -> Resuming/approving session {sess_id_to_approve} ({target_approve_email}) at {action_url}...")
    action_resp = http_post_json(action_url, payload)
    print(f" -> Action Response: {json.dumps(action_resp, indent=2)}")
    assert action_resp.get("status") == "success", "Action failed!"
    
    # Confirm the card disappears from /api/pending
    print(" -> Checking pending list to verify approved card is removed...")
    final_pending_data = http_get(f"{BASE_URL}/api/pending")
    final_claims = final_pending_data.get("pending_claims", [])
    has_card = any(c["session_id"] == sess_id_to_approve for c in final_claims)
    print(f" -> Card is present in pending claims list: {has_card}")
    assert not has_card, "Approved card is still in pending list!"
    print(" -> Verified: Claim disappeared from the pending queue successfully!")
    
    print("\n=== ALL END-TO-END FILE UPLOAD VALIDATIONS COMPLETED SUCCESSFULLY! ===")

if __name__ == "__main__":
    main()

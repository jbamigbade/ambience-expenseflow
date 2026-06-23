import os
import sys
from google.cloud import firestore

# Force UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

test_claims = [
    {
        "id": 1,
        "email": "auth.approval.test@company.com",
        "claim_id": "ffc3853a-0894-4fd8-ac15-838112ea932f",
        "desc": "Auth Audit Approval Test"
    },
    {
        "id": 2,
        "email": "auth.rejection.test@company.com",
        "claim_id": "ab480b88-ca0a-4287-bf6d-5f2f845b5dc7",
        "desc": "Auth Audit Rejection Test"
    },
    {
        "id": 3,
        "email": "auth.flight.docs.test@company.com",
        "claim_id": "d6672fbc-8607-4987-b4bb-88ac7d3f1f4b",
        "desc": "Flight Missing Document Test"
    },
    {
        "id": 4,
        "email": "auth.hotel.docs.test@company.com",
        "claim_id": "cd0e2a89-04cd-43c9-9b0d-f6f1eef12037",
        "desc": "Hotel Approval Letter Test"
    }
]

def verify():
    print("=== Verification of Fresh Claims State in Firestore ===")
    
    for tc in test_claims:
        print(f"\n--- {tc['desc']} ({tc['email']}) ---")
        print(f"  Claim ID:   {tc['claim_id']}")
        
        # 1. Check Expense Document
        exp_doc = db.collection("expenses").document(tc['claim_id']).get()
        if not exp_doc.exists:
            print("  [ERROR] Expense document not found in Firestore!")
            continue
            
        exp_data = exp_doc.to_dict()
        print(f"  Status:     {exp_data.get('status')}")
        print(f"  Session ID: {exp_data.get('session_id')}")
        print(f"  Missing:    {exp_data.get('missing_documents')}")
        
        # 2. Check Decision Document
        dec_query = db.collection("decisions").where("claim_id", "==", tc['claim_id']).limit(1).get()
        dec_docs = list(dec_query)
        if dec_docs:
            dec_data = dec_docs[0].to_dict()
            print("  [FOUND] Decision record:")
            print(f"    decision:       {dec_data.get('decision')}")
            print(f"    actor_email:    {dec_data.get('actor_email')}")
            print(f"    actor_role:     {dec_data.get('actor_role')}")
            print(f"    decided_by:     {dec_data.get('decided_by')}")
            print(f"    decided_role:   {dec_data.get('decided_role')}")
            print(f"    authenticated:  {dec_data.get('authenticated')}")
        else:
            print("  [PENDING] No decision document registered yet.")
            
        # 3. Check Audit Logs
        logs_query = db.collection("audit_logs").where("session_id", "==", exp_data.get('session_id')).get()
        logs = list(logs_query)
        if logs:
            print("  [FOUND] Audit log records:")
            # Sort logs by timestamp if available
            logs_sorted = sorted(logs, key=lambda x: x.to_dict().get("timestamp", ""))
            for idx, log_doc in enumerate(logs_sorted, 1):
                ld = log_doc.to_dict()
                print(f"    Log {idx}:")
                print(f"      action:        {ld.get('action')}")
                print(f"      actor_email:   {ld.get('actor_email')}")
                print(f"      actor_role:    {ld.get('actor_role')}")
                print(f"      actor:         {ld.get('actor')}")
                print(f"      authenticated: {ld.get('authenticated')}")
                print(f"      timestamp:     {ld.get('timestamp')}")
        else:
            print("  [PENDING] No audit logs registered yet.")

if __name__ == "__main__":
    verify()

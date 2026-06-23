import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

def check_legacy():
    print("=== Scanning Legacy Decisions ===")
    decisions_ref = db.collection("decisions")
    # Fetch 3 older decisions that do not have actor_email
    query = decisions_ref.where("authenticated", "==", False).limit(3)
    docs = list(query.get())
    
    if docs:
        for idx, doc in enumerate(docs, 1):
            d = doc.to_dict()
            print(f"Legacy Decision {idx} (ID: {doc.id}):")
            print(f"  Employee Name: {d.get('employee_name') or d.get('claim_details', {}).get('employee_name')}")
            print(f"  Actor Display: {d.get('actor_display')}")
            print(f"  Actor Role:    {d.get('actor_role')}")
            print(f"  Authenticated: {d.get('authenticated')}")
            print(f"  Auth Note:     {d.get('auth_note')}")
            print(f"  Actor Email (should be None/missing): {d.get('actor_email')}")
            print(f"  Decided By (should be None/missing):  {d.get('decided_by')}")
    else:
        print("No legacy decisions with authenticated == False found!")

    print("\n=== Scanning Legacy Audit Logs ===")
    logs_ref = db.collection("audit_logs")
    query = logs_ref.where("authenticated", "==", False).limit(3)
    docs = list(query.get())
    
    if docs:
        for idx, doc in enumerate(docs, 1):
            d = doc.to_dict()
            print(f"Legacy Audit Log {idx} (ID: {doc.id}):")
            print(f"  Action:        {d.get('action')}")
            print(f"  Actor:         {d.get('actor')}")
            print(f"  Actor Role:    {d.get('actor_role')}")
            print(f"  Authenticated: {d.get('authenticated')}")
            print(f"  Auth Note:     {d.get('auth_note')}")
            print(f"  Actor Email (should be None/missing): {d.get('actor_email')}")
    else:
        print("No legacy audit logs with authenticated == False found!")

if __name__ == "__main__":
    check_legacy()

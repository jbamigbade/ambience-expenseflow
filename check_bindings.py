import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

test_emails = [
    "auth.approval.test@company.com",
    "auth.rejection.test@company.com",
    "auth.flight.docs.test@company.com",
    "auth.hotel.docs.test@company.com"
]

print("=== Scanning current status and Session IDs ===")
for idx, email in enumerate(test_emails, 1):
    query = db.collection("expenses").where("employee_name", "==", email)
    docs = list(query.get())
    if docs:
        docs.sort(key=lambda x: x.to_dict().get("created_at", ""), reverse=True)
        doc = docs[0]
        d = doc.to_dict()
        print(f"Test Claim {idx} ({email}):")
        print(f"  Claim ID:      {doc.id}")
        print(f"  Session ID:    {d.get('session_id')}")
        print(f"  Status:        {d.get('status')}")
    else:
        print(f"Test Claim {idx} ({email}) not found.")

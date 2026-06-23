import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

print("Analyzing decisions collection...")
decisions_ref = db.collection("decisions")
dec_docs = list(decisions_ref.get())

dec_total = len(dec_docs)
dec_with_email = 0
dec_without_email = 0

for doc in dec_docs:
    d = doc.to_dict()
    if d.get("actor_email"):
        dec_with_email += 1
    else:
        dec_without_email += 1

print(f"Decisions Total: {dec_total}")
print(f"Decisions with actor_email: {dec_with_email}")
print(f"Decisions without actor_email: {dec_without_email}")
print("-" * 40)

print("Analyzing audit_logs collection...")
audit_logs_ref = db.collection("audit_logs")
audit_docs = list(audit_logs_ref.get())

audit_total = len(audit_docs)
audit_with_email = 0
audit_without_email = 0

for doc in audit_docs:
    d = doc.to_dict()
    if d.get("actor_email"):
        audit_with_email += 1
    else:
        audit_without_email += 1

print(f"Audit Logs Total: {audit_total}")
print(f"Audit Logs with actor_email: {audit_with_email}")
print(f"Audit Logs without actor_email: {audit_without_email}")

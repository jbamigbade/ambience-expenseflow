import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

print("=== Previewing Decisions Backfill ===")
dec_docs = list(db.collection("decisions").get())
to_update_dec = 0

for doc in dec_docs:
    d = doc.to_dict()
    if not d.get("actor_email"):
        to_update_dec += 1
        print(f"Dec doc {doc.id}: decision={d.get('decision')}, decided_by={d.get('decided_by')}, actor_email={d.get('actor_email')}")

print(f"Total Decisions to Backfill: {to_update_dec}")
print("-" * 60)

print("=== Previewing Audit Logs Backfill ===")
audit_docs = list(db.collection("audit_logs").get())
to_update_audit = 0

for doc in audit_docs:
    d = doc.to_dict()
    if not d.get("actor_email"):
        # We only backfill if it represents a manager action/approval record (or let's check what audit logs are legacy manager actions)
        is_manager_action = d.get("event_type") in ["manager_decision", "document_uploaded"] or d.get("actor") in ["manager", "finance_admin"]
        if is_manager_action:
            to_update_audit += 1
            print(f"Audit doc {doc.id}: event_type={d.get('event_type')}, actor={d.get('actor')}, actor_email={d.get('actor_email')}")

print(f"Total Audit Logs to Backfill: {to_update_audit}")

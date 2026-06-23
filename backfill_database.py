import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

print("Starting safe legacy-backfill/normalization step...")

dec_ref = db.collection("decisions")
dec_docs = list(dec_ref.get())

dec_updated = 0
dec_skipped = 0

for doc in dec_docs:
    d = doc.to_dict()
    if d.get("actor_email"):
        dec_skipped += 1
        continue
    
    # Legacy record detected
    update_data = {
        "actor_display": "Legacy Manager",
        "actor_role": d.get("actor_role") or d.get("decided_by") or "manager",
        "authenticated": False,
        "auth_note": "Approved before Google Auth actor tracking was enabled"
    }
    
    doc.reference.update(update_data)
    dec_updated += 1

print(f"Decisions updated: {dec_updated}")
print(f"Decisions skipped (already had actor_email): {dec_skipped}")

audit_ref = db.collection("audit_logs")
audit_docs = list(audit_ref.get())

audit_updated = 0
audit_skipped = 0

for doc in audit_docs:
    d = doc.to_dict()
    if d.get("actor_email"):
        audit_skipped += 1
        continue
    
    # We only backfill if it represents a manager action/approval record
    is_manager_action = (
        d.get("event_type") in ["manager_decision", "document_uploaded"] or
        d.get("actor") in ["manager", "user", "finance_admin", "Legacy Manager"]
    )
    
    if is_manager_action:
        existing_role = d.get("actor_role") or (d.get("actor") if d.get("actor") in ["manager", "finance_admin"] else "manager")
        update_data = {
            "actor_display": "Legacy Manager",
            "actor_role": existing_role,
            "authenticated": False,
            "auth_note": "Approved before Google Auth actor tracking was enabled"
        }
        doc.reference.update(update_data)
        audit_updated += 1
    else:
        audit_skipped += 1

print(f"Audit logs updated: {audit_updated}")
print(f"Audit logs skipped: {audit_skipped}")

print("Legacy-backfill/normalization completed successfully.")

import os
import sys
from google.cloud import firestore
from datetime import datetime

# Force UTF-8 encoding for stdout on Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add submission_frontend to path so we can import main.py
sys.path.append(os.path.abspath("submission_frontend"))
import main

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

test_emails = [
    "employee.ny.within@company.com",
    "employee.ny.over@company.com",
    "employee.sc.over@company.com",
    "employee.mn.within@company.com",
    "employee.unknown.policy@company.com"
]

def recalculate():
    print("=== Force Recalculating and Correcting Per Diem Claims in Firestore ===")
    
    for email in test_emails:
        print(f"\nProcessing Email: {email}")
        query = db.collection("expenses").where("employee_email", "==", email)
        docs = list(query.get())
        
        if not docs:
            print(f"  [WARNING] No document found for {email}")
            continue
            
        for doc in docs:
            data = doc.to_dict()
            claim_id = doc.id
            print(f"  Updating Claim ID: {claim_id} (Currently: {data.get('policy_status')})")
            
            # Reconstruct details
            claim_details = {
                "company_id": data.get("company_id") or "demo_company",
                "employee_email": email,
                "employee_name": data.get("employee_name") or "Unknown Claimant",
                "employee_id": data.get("employee_id") or "",
                "category": data.get("category") or "meals",
                "amount": float(data.get("amount") or 0.0),
                "claimed_meals": float(data.get("claimed_meals") or 0.0),
                "claimed_lodging": float(data.get("claimed_lodging") or 0.0),
                "claimed_incidentals": float(data.get("claimed_incidentals") or 0.0),
                "travel_start_date": data.get("travel_start_date"),
                "travel_end_date": data.get("travel_end_date"),
                "check_in_date": data.get("check_in_date"),
                "check_out_date": data.get("check_out_date"),
                "city": data.get("city"),
                "state": data.get("state"),
                "state_code": data.get("state_code") or "",
                "country": data.get("country") or "US",
                "business_purpose": data.get("business_purpose") or "",
            }
            
            # Force run the python policy check (calls run_per_diem_check internally)
            policy_res = main.run_policy_check_py(claim_details)
            pdr = claim_details.get("per_diem_review") or {}
            
            # Determine status
            status = "blocked_missing_docs" if policy_res["missing_docs"] else "pending_review"
            
            update_data = {
                "status": status,
                "policy_status": policy_res["status"],
                "required_documents": policy_res["required_docs"],
                "missing_documents": policy_res["missing_docs"],
                "company_id": pdr.get("company_id") or claim_details["company_id"],
                "employee_email": pdr.get("employee_email") or claim_details["employee_email"],
                "employee_name": pdr.get("employee_name") or claim_details["employee_name"],
                "state_code": pdr.get("state_code") or claim_details["state_code"] or "",
                "per_diem_review": pdr,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            # Write to Firestore
            db.collection("expenses").document(claim_id).update(update_data)
            print(f"    -> Updated: policy_status='{policy_res['status']}', status='{status}'")
            print(f"    -> Policy Source: '{pdr.get('policy_source')}'")
            print(f"    -> Allowed meals: ${pdr.get('allowed_meal_total')}, Claimed meals: ${pdr.get('claimed_meals')}")
            print(f"    -> Required docs: {policy_res['required_docs']}")

if __name__ == "__main__":
    recalculate()

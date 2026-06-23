import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

def diagnose():
    print("=== Diagnosing Pending Approvals and Expenses for Missing Fields ===")
    expenses_ref = db.collection("expenses")
    docs = list(expenses_ref.get())
    
    fields_to_check = [
        "amount",
        "total_claimed_amount",
        "total_reimbursable_amount",
        "reimbursable_amount",
        "non_reimbursable_amount",
        "calculated_reimbursement_amount",
        "policy_exception_count",
        "missing_document_count",
        "claim_count",
        "status",
        "category"
    ]
    
    missing_count = 0
    for doc in docs:
        d = doc.to_dict()
        missing_fields = []
        for f in fields_to_check:
            if f not in d or d[f] is None:
                missing_fields.append(f)
        
        if missing_fields:
            missing_count += 1
            print(f"Record ID: {doc.id}")
            print(f"  Employee: {d.get('employee_name')} ({d.get('employee_email')})")
            print(f"  Category: {d.get('category')} | Status: {d.get('status')}")
            print(f"  Missing or Undefined Fields: {missing_fields}")
            print("-" * 40)
            
    print(f"Diagnosis complete. Found {missing_count} out of {len(docs)} records with missing fields.")

if __name__ == "__main__":
    diagnose()

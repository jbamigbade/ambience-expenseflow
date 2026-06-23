import os
import sys
from google.cloud import firestore

# Force UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

test_emails = [
    "employee.ny.within@company.com",
    "employee.ny.over@company.com",
    "employee.sc.over@company.com",
    "employee.mn.within@company.com",
    "employee.unknown.policy@company.com"
]

def verify():
    print("=== Verification of Company-Configurable Per Diem Claims in Firestore ===")
    
    for email in test_emails:
        print(f"\n" + "="*80)
        print(f"Checking Employee Email: {email}")
        print("="*80)
        
        # Query expenses
        query = db.collection("expenses").where("employee_email", "==", email)
        docs = list(query.get())
        
        if not docs:
            print("  [ERROR] No expense document found in Firestore for this email.")
            continue
            
        # Sort by creation time to get the latest
        docs.sort(key=lambda x: x.to_dict().get("created_at", ""), reverse=True)
        doc = docs[0]
        data = doc.to_dict()
        
        print(f"  Claim ID:          {doc.id}")
        print(f"  Session ID:        {data.get('session_id')}")
        print(f"  Status:            {data.get('status')}")
        print(f"  Policy Status:     {data.get('policy_status')}")
        print(f"  Required Docs:     {data.get('required_documents')}")
        print(f"  Missing Docs:      {data.get('missing_documents')}")
        
        pdr = data.get("per_diem_review")
        if not pdr:
            print("  [ERROR] No per_diem_review dictionary stored on this claim!")
            continue
            
        print("\n  --- Per Diem Review Details ---")
        print(f"    Company Name:    {pdr.get('company_name')} ({pdr.get('company_id')})")
        print(f"    Employee Name:   {pdr.get('employee_name')}")
        print(f"    Travel Dates:    {pdr.get('travel_start_date')} to {pdr.get('travel_end_date')} ({pdr.get('travel_days')} days)")
        print(f"    Hotel Nights:    {pdr.get('hotel_nights')} nights")
        print(f"    Destination:     {pdr.get('city')}, {pdr.get('state')} ({pdr.get('state_code')})")
        print(f"    Policy Source:   {pdr.get('policy_source')}")
        
        print("\n    Rates Configuration:")
        print(f"      Meal Rate:     ${pdr.get('meal_rate_per_day')}/day")
        print(f"      Lodging Rate:  ${pdr.get('lodging_rate_per_night')}/night")
        print(f"      Incidental:    ${pdr.get('incidental_rate_per_day')}/day")
        
        print("\n    Allowed Totals vs Claimed:")
        print(f"      Allowed Meals: ${pdr.get('allowed_meal_total'):.2f} \t Claimed: ${pdr.get('claimed_meals'):.2f}")
        print(f"      Allowed Lodge: ${pdr.get('allowed_lodging_total'):.2f} \t Claimed: ${pdr.get('claimed_lodging'):.2f}")
        print(f"      Allowed Incid: ${pdr.get('allowed_incidental_total'):.2f} \t Claimed: ${pdr.get('claimed_incidentals'):.2f}")
        
        allowed_total = float(pdr.get('allowed_meal_total') or 0.0) + float(pdr.get('allowed_lodging_total') or 0.0) + float(pdr.get('allowed_incidental_total') or 0.0)
        print(f"      Allowed Total: ${allowed_total:.2f} \t Claimed Amount: ${pdr.get('claimed_amount'):.2f}")
        print(f"      Overage Total: ${pdr.get('overage_total'):.2f}")
        print(f"      Status Label:  {pdr.get('status')}")
        print(f"      Warning Msg:   {pdr.get('warning')}")
        
        # Let's verify decisions if any exist
        dec_query = db.collection("decisions").where("claim_id", "==", doc.id).limit(1).get()
        dec_docs = list(dec_query)
        if dec_docs:
            dec_data = dec_docs[0].to_dict()
            print("\n    Decision Registered:")
            print(f"      Decision:      {dec_data.get('decision')}")
            print(f"      Actor Email:   {dec_data.get('actor_email')}")
            print(f"      Actor Role:    {dec_data.get('actor_role')}")
            print(f"      Override Reason: {dec_data.get('override_reason')}")
            print(f"      Authenticated: {dec_data.get('authenticated')}")
        else:
            print("\n    No manual manager/finance_admin decisions have been taken yet.")

if __name__ == "__main__":
    verify()

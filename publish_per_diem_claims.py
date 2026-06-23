import json
import subprocess
import time
import os
from google.cloud import firestore

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

test_claims = [
    {
        "id": 1,
        "name": "Demo Company New York meals within per diem",
        "payload": {
            "company_id": "demo_company",
            "employee_email": "employee.ny.within@company.com",
            "category": "meals",
            "amount": 300.0,
            "claimed_meals": 300.0,
            "travel_start_date": "2026-04-12",
            "travel_end_date": "2026-04-14",
            "city": "New York",
            "state": "NY",
            "business_purpose": "Business meetings in New York"
        }
    },
    {
        "id": 2,
        "name": "Demo Company New York meals over per diem",
        "payload": {
            "company_id": "demo_company",
            "employee_email": "employee.ny.over@company.com",
            "category": "meals",
            "amount": 450.0,
            "claimed_meals": 450.0,
            "travel_start_date": "2026-04-12",
            "travel_end_date": "2026-04-14",
            "city": "New York",
            "state": "NY",
            "business_purpose": "Business meetings in New York"
        }
    },
    {
        "id": 3,
        "name": "Demo Company South Carolina meals over per diem",
        "payload": {
            "company_id": "demo_company",
            "employee_email": "employee.sc.over@company.com",
            "category": "meals",
            "amount": 220.0,
            "claimed_meals": 220.0,
            "travel_start_date": "2026-04-12",
            "travel_end_date": "2026-04-14",
            "city": "Columbia",
            "state": "SC",
            "business_purpose": "Business training in South Carolina"
        }
    },
    {
        "id": 4,
        "name": "Demo Company Minnesota meals within per diem",
        "payload": {
            "company_id": "demo_company",
            "employee_email": "employee.mn.within@company.com",
            "category": "meals",
            "amount": 190.0,
            "claimed_meals": 190.0,
            "travel_start_date": "2026-04-12",
            "travel_end_date": "2026-04-14",
            "city": "Minneapolis",
            "state": "MN",
            "business_purpose": "Business training in Minnesota"
        }
    },
    {
        "id": 5,
        "name": "Missing company policy",
        "payload": {
            "company_id": "unknown_company",
            "employee_email": "employee.unknown.policy@company.com",
            "category": "meals",
            "amount": 180.0,
            "claimed_meals": 180.0,
            "travel_start_date": "2026-04-12",
            "travel_end_date": "2026-04-14",
            "city": "Raleigh",
            "state": "NC",
            "business_purpose": "Business trip meals"
        }
    }
]

print("=== Publishing 5 Per Diem Test Claims via Pub/Sub ===")
for item in test_claims:
    payload = item["payload"]
    message = json.dumps({
        "input": {
            "message": json.dumps(payload),
            "user_id": f"perdiem-user-{item['id']}"
        }
    })
    
    print(f"\nPublishing Claim {item['id']}: {item['name']}")
    subprocess.run([
        gcloud,
        "pubsub",
        "topics",
        "publish",
        topic,
        f"--project={project}",
        f"--message={message}"
    ], check=True)

print("\nWaiting 20 seconds for claims to be processed by Agent Runtime and ingested into Firestore...")
time.sleep(20)

# Initialize Firestore to query them
os.environ["GOOGLE_CLOUD_PROJECT"] = project
db = firestore.Client()

print("\n=== Fetching generated Claim IDs and Session IDs ===")
for item in test_claims:
    emp_email = item["payload"]["employee_email"]
    query = db.collection("expenses").where("employee_email", "==", emp_email)
    docs = list(query.get())
    
    if docs:
        docs.sort(key=lambda x: x.to_dict().get("created_at", ""), reverse=True)
        doc = docs[0]
        d = doc.to_dict()
        print(f"\nTest Claim {item['id']} ({item['name']}):")
        print(f"  Employee Email: {emp_email}")
        print(f"  Claim ID:       {doc.id}")
        print(f"  Session ID:     {d.get('session_id')}")
        print(f"  Category:       {d.get('category')}")
        print(f"  Amount:         ${d.get('amount')}")
        print(f"  Status:         {d.get('status')}")
    else:
        print(f"\nTest Claim {item['id']} ({item['name']}) was not found in Firestore.")

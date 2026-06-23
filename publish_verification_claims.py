import json
import subprocess
import time
import os
from google.cloud import firestore

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Define the 4 claims
claims_to_publish = [
    {
        "id": 1,
        "payload": {
            "employee_name": "auth.approval.test@company.com",
            "category": "travel",
            "amount": 275.0,
            "description": "Authenticated approval audit test"
        }
    },
    {
        "id": 2,
        "payload": {
            "employee_name": "auth.rejection.test@company.com",
            "category": "travel",
            "amount": 425.0,
            "description": "Authenticated rejection audit test"
        }
    },
    {
        "id": 3,
        "payload": {
            "employee_name": "auth.flight.docs.test@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 1350.0,
            "description": "Flight above approval threshold requiring ticket receipt and manager approval letter"
        }
    },
    {
        "id": 4,
        "payload": {
            "employee_name": "auth.hotel.docs.test@company.com",
            "category": "lodging",
            "amount": 1600.0,
            "description": "Four-night hotel stay requiring approval letter",
            "check_in_date": "2026-04-12",
            "check_out_date": "2026-04-16",
            "city": "New York",
            "state": "NY"
        }
    }
]

print("=== Publishing 4 Fresh Verification Claims via Pub/Sub ===")
for item in claims_to_publish:
    payload = item["payload"]
    message = json.dumps({
        "input": {
            "message": json.dumps(payload),
            "user_id": f"verification-user-{item['id']}"
        }
    })
    
    print(f"\nPublishing Claim {item['id']} ({payload['employee_name']}):")
    subprocess.run([
        gcloud,
        "pubsub",
        "topics",
        "publish",
        topic,
        f"--project={project}",
        f"--message={message}"
    ], check=True)

print("\nWaiting 15 seconds for claims to be processed by Agent Runtime and ingested into Firestore...")
time.sleep(15)

# Initialize Firestore to query them
os.environ["GOOGLE_CLOUD_PROJECT"] = project
db = firestore.Client()

print("\n=== Fetching generated Claim IDs and Session IDs ===")
for item in claims_to_publish:
    emp_name = item["payload"]["employee_name"]
    query = db.collection("expenses").where("employee_name", "==", emp_name)
    docs = list(query.get())
    
    if docs:
        docs.sort(key=lambda x: x.to_dict().get("created_at", ""), reverse=True)
        doc = docs[0]
        d = doc.to_dict()
        print(f"\nTest Claim {item['id']}:")
        print(f"  Employee Name: {emp_name}")
        print(f"  Claim ID:      {doc.id}")
        print(f"  Session ID:    {d.get('session_id')}")
        print(f"  Category:      {d.get('category')}")
        print(f"  Amount:        ${d.get('amount')}")
        print(f"  Status:        {d.get('status')}")
    else:
        print(f"\nTest Claim {item['id']} ({emp_name}) was not found yet in Firestore.")

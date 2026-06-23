import os
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

docs = list(db.collection("expenses").order_by("created_at", direction=firestore.Query.DESCENDING).limit(15).get())
print("=== 15 Most Recent Expenses in Firestore ===")
for d in docs:
    data = d.to_dict()
    print(f"ID: {d.id} | Employee: {data.get('employee_name')} | Email: {data.get('employee_email')} | Category: {data.get('category')} | Amount: {data.get('amount')} | Created: {data.get('created_at')} | Status: {data.get('status')}")

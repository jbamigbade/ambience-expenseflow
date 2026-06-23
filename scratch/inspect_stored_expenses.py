import os
import json
from google.cloud import firestore

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

docs = list(db.collection("expenses").order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).get())
print("=== Stored Expenses Details ===")
for d in docs:
    data = d.to_dict()
    print(f"\nDocument ID: {d.id}")
    for k, v in data.items():
        print(f"  {k}: {v}")

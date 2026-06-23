import json
import subprocess
import time

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

test_cases = [
    {
        "name": "1. Flight ticket above $1200 missing manager approval letter",
        "payload": {
            "employee_name": "flight.overlimit.missing@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 1500.0,
            "description": "Flight above limit missing approval letter",
            "flight_ticket_receipt_url": "https://example.com/flight-receipt.pdf"
        }
    },
    {
        "name": "2. Flight ticket missing receipt",
        "payload": {
            "employee_name": "flight.missing.receipt@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 800.0,
            "description": "Flight missing receipt"
        }
    },
    {
        "name": "3. Hotel above $350/night missing manager approval letter",
        "payload": {
            "employee_name": "hotel.overlimit.missing.v2@company.com",
            "category": "lodging",
            "amount": 1600.0,
            "description": "Hotel over nightly limit missing approval",
            "check_in_date": "2026-04-12",
            "check_out_date": "2026-04-15",
            "city": "San Francisco",
            "state": "CA",
            "hotel_receipt_url": "https://example.com/hotel-receipt.pdf"
        }
    },
    {
        "name": "4. Office supply missing receipt",
        "payload": {
            "employee_name": "office.paper.missing@company.com",
            "category": "office_supplies",
            "amount": 120.0,
            "description": "Office supplies missing receipt"
        }
    },
    {
        "name": "5. Parking citation missing manager approval letter",
        "payload": {
            "employee_name": "parking.ticket.test@company.com",
            "category": "parking_citation",
            "amount": 75.0,
            "description": "Parking citation missing approval letter"
        }
    }
]

for idx, case in enumerate(test_cases, start=1):
    print(f"\n--- Publishing {case['name']} ---")
    
    # Wrap the payload in standard Agent Runtime event structure
    message = json.dumps({
        "input": {
            "message": json.dumps(case["payload"]),
            "user_id": "default-user"
        }
    })
    
    print(f"Message payload:\n{json.dumps(case['payload'], indent=2)}")
    
    # Publish via gcloud command
    subprocess.run([
        gcloud,
        "pubsub",
        "topics",
        "publish",
        topic,
        f"--project={project}",
        f"--message={message}"
    ], check=True)
    
    print("Published successfully.")
    if idx < len(test_cases):
        print("Waiting 3 seconds before publishing next case...")
        time.sleep(3)

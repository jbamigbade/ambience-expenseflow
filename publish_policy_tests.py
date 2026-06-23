import json
import subprocess
import time

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Define the 5 test payloads
test_cases = [
    {
        "name": "Case A: Hotel over limit missing approval letter (exactly $350/night, should be within policy)",
        "payload": {
            "employee_name": "hotel.overlimit.missing@company.com",
            "category": "lodging",
            "amount": 1400.0,
            "description": "Four-night hotel stay above nightly limit",
            "check_in_date": "2026-04-12",
            "check_out_date": "2026-04-16",
            "city": "New York",
            "state": "NY",
            "hotel_receipt_url": "https://example.com/hotel-receipt.pdf"
        }
    },
    {
        "name": "Case B: Hotel above $350 per night with approval letter ($400/night, has letter, allowed)",
        "payload": {
            "employee_name": "hotel.approved.docs@company.com",
            "category": "lodging",
            "amount": 1600.0,
            "description": "Four-night hotel stay with approval letter",
            "check_in_date": "2026-04-12",
            "check_out_date": "2026-04-16",
            "city": "New York",
            "state": "NY",
            "hotel_receipt_url": "https://example.com/hotel-receipt.pdf",
            "manager_approval_letter_url": "https://example.com/manager-approval-letter.pdf"
        }
    },
    {
        "name": "Case C: Flight ticket missing receipt (requires flight ticket receipt, disabled)",
        "payload": {
            "employee_name": "flight.missing.receipt@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 900.0,
            "description": "Domestic flight ticket without receipt"
        }
    },
    {
        "name": "Case D: Flight ticket above $1200 missing manager approval letter (disabled)",
        "payload": {
            "employee_name": "flight.overlimit.missing@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 1300.0,
            "description": "International flight ticket",
            "flight_ticket_receipt_url": "https://example.com/flight-ticket-receipt.pdf"
        }
    },
    {
        "name": "Case E: Flight ticket above $1200 with all documents (allowed)",
        "payload": {
            "employee_name": "flight.overlimit.complete@company.com",
            "category": "flight",
            "travel_type": "flight",
            "amount": 1300.0,
            "description": "International flight ticket with full documentation",
            "flight_ticket_receipt_url": "https://example.com/flight-ticket-receipt.pdf",
            "manager_approval_letter_url": "https://example.com/manager-approval-letter.pdf"
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
        print("Waiting 2 seconds before publishing next case...")
        time.sleep(2)

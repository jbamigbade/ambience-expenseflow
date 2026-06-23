import json
import subprocess
import time

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Define the 5 new test payloads
test_cases = [
    {
        "name": "Case A: Printer ink with receipt (compliant office expense, allows approval)",
        "payload": {
            "employee_name": "office.ink.test@company.com",
            "category": "printer_ink",
            "amount": 85.0,
            "item_type": "Ink cartridge",
            "vendor": "Office Depot",
            "quantity": 2,
            "description": "Printer ink for office use",
            "business_purpose": "Printing tutoring and office documents",
            "office_receipt_url": "https://example.com/printer-ink-receipt.pdf"
        }
    },
    {
        "name": "Case B: Printing supplies missing receipt (non-compliant, blocks approval)",
        "payload": {
            "employee_name": "office.paper.missing@company.com",
            "category": "printing_supplies",
            "amount": 120.0,
            "item_type": "Copy paper",
            "vendor": "Staples",
            "quantity": 5,
            "description": "Printing paper for office use",
            "business_purpose": "Printing classroom worksheets"
        }
    },
    {
        "name": "Case C: Business parking with receipt (compliant parking expense, allows approval)",
        "payload": {
            "employee_name": "parking.business.test@company.com",
            "category": "business_parking",
            "amount": 35.0,
            "description": "Parking for client meeting",
            "parking_location": "Downtown Raleigh",
            "parking_date": "2026-04-12",
            "related_meeting": "Client meeting",
            "business_purpose": "Parking during approved business meeting",
            "parking_receipt_url": "https://example.com/parking-receipt.pdf"
        }
    },
    {
        "name": "Case D: Parking citation without approval letter (non-reimbursable, blocks approval)",
        "payload": {
            "employee_name": "parking.ticket.test@company.com",
            "category": "parking_citation",
            "amount": 75.0,
            "description": "Parking citation during business trip",
            "parking_location": "Downtown Raleigh",
            "parking_date": "2026-04-12",
            "business_purpose": "Business travel"
        }
    },
    {
        "name": "Case E: Parking citation with manager approval letter (compliant citation expense, allows approval)",
        "payload": {
            "employee_name": "parking.ticket.approved@company.com",
            "category": "parking_citation",
            "amount": 75.0,
            "description": "Parking citation with special approval",
            "parking_location": "Downtown Raleigh",
            "parking_date": "2026-04-12",
            "business_purpose": "Business travel",
            "manager_approval_letter_url": "https://example.com/parking-citation-approval-letter.pdf"
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

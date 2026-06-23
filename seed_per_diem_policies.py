import os
from google.cloud import firestore
from datetime import datetime

os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"
db = firestore.Client()

def seed_data():
    print("=== Seeding Per Diem Policy Database ===")
    
    # 1. Seed Companies
    print("Seeding companies...")
    db.collection("companies").document("demo_company").set({
        "company_id": "demo_company",
        "company_name": "Demo Company",
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    })
    
    # 2. Seed Company Policy Settings
    print("Seeding company_policy_settings...")
    db.collection("company_policy_settings").document("demo_company_default").set({
        "company_id": "demo_company",
        "policy_id": "demo_company_default",
        "policy_name": "Demo Default Policy",
        "description": "Standard per diem policy settings for Demo Company",
        "default_meal_rate_per_day": 50.0,
        "default_lodging_rate_per_night": 150.0,
        "default_incidental_rate_per_day": 10.0,
        "partial_day_percent": 75.0,
        "receipt_required_above": 75.0,
        "manager_approval_required_above": 500.0,
        "require_receipt_for_flights": True,
        "require_manager_letter_for_flight_above": 1000.0,
        "require_manager_letter_for_lodging_above": 350.0,
        "active": True,
        "effective_start_date": "2026-01-01T00:00:00Z",
        "effective_end_date": "2027-12-31T23:59:59Z",
        "created_by": "system",
        "updated_by": "system",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    })
    
    # 3. Seed State Per Diem Rates
    print("Seeding company_state_per_diem_rates...")
    state_rates = [
        {
            "rate_id": "demo_state_ny",
            "state": "New York",
            "state_code": "NY",
            "country": "US",
            "cost_tier": "high",
            "meal_rate_per_day": 150.0,
            "lodging_rate_per_night": 350.0,
            "incidental_rate_per_day": 15.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        },
        {
            "rate_id": "demo_state_sc",
            "state": "South Carolina",
            "state_code": "SC",
            "country": "US",
            "cost_tier": "standard",
            "meal_rate_per_day": 75.0,
            "lodging_rate_per_night": 175.0,
            "incidental_rate_per_day": 10.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        },
        {
            "rate_id": "demo_state_mn",
            "state": "Minnesota",
            "state_code": "MN",
            "country": "US",
            "cost_tier": "standard",
            "meal_rate_per_day": 95.0,
            "lodging_rate_per_night": 225.0,
            "incidental_rate_per_day": 12.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        }
    ]
    
    for r in state_rates:
        r.update({
            "company_id": "demo_company",
            "created_by": "system",
            "updated_by": "system",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        db.collection("company_state_per_diem_rates").document(r["rate_id"]).set(r)

    # 4. Seed City Per Diem Rates
    print("Seeding company_city_per_diem_rates...")
    city_rates = [
        {
            "rate_id": "demo_city_ny",
            "city": "New York",
            "state": "New York",
            "state_code": "NY",
            "country": "US",
            "meal_rate_per_day": 150.0,
            "lodging_rate_per_night": 350.0,
            "incidental_rate_per_day": 15.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        },
        {
            "rate_id": "demo_city_columbia",
            "city": "Columbia",
            "state": "South Carolina",
            "state_code": "SC",
            "country": "US",
            "meal_rate_per_day": 75.0,
            "lodging_rate_per_night": 175.0,
            "incidental_rate_per_day": 10.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        },
        {
            "rate_id": "demo_city_minneapolis",
            "city": "Minneapolis",
            "state": "Minnesota",
            "state_code": "MN",
            "country": "US",
            "meal_rate_per_day": 95.0,
            "lodging_rate_per_night": 225.0,
            "incidental_rate_per_day": 12.0,
            "effective_start_date": "2026-01-01T00:00:00Z",
            "effective_end_date": "2027-12-31T23:59:59Z",
            "active": True,
            "source_note": "Demo company-configured rate for testing only."
        }
    ]
    
    for r in city_rates:
        r.update({
            "company_id": "demo_company",
            "created_by": "system",
            "updated_by": "system",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        db.collection("company_city_per_diem_rates").document(r["rate_id"]).set(r)

    # 5. Seed Employees
    print("Seeding employees...")
    employees = [
        {
            "employee_id": "emp_ny_within",
            "employee_email": "employee.ny.within@company.com",
            "employee_name": "NY Within Claimant",
            "department": "Sales",
            "role_level": "Standard",
            "manager_email": "manager@company.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_ny_over",
            "employee_email": "employee.ny.over@company.com",
            "employee_name": "NY Over Claimant",
            "department": "Engineering",
            "role_level": "Standard",
            "manager_email": "manager@company.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_sc_over",
            "employee_email": "employee.sc.over@company.com",
            "employee_name": "SC Over Claimant",
            "department": "Marketing",
            "role_level": "Standard",
            "manager_email": "manager@company.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_mn_within",
            "employee_email": "employee.mn.within@company.com",
            "employee_name": "MN Within Claimant",
            "department": "HR",
            "role_level": "Standard",
            "manager_email": "manager@company.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_unknown_policy",
            "employee_email": "employee.unknown.policy@company.com",
            "employee_name": "Unknown Policy Claimant",
            "department": "Finance",
            "role_level": "Standard",
            "manager_email": "manager@company.com",
            "default_per_diem_policy": "nonexistent_policy",
            "active": True
        },
        {
            "employee_id": "emp_fresh_manager_test",
            "employee_email": "fresh.manager.test@company.com",
            "employee_name": "Fresh Manager Test",
            "department": "Operations",
            "role_level": "Standard",
            "manager_email": "obamigbade@gmail.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_receipt_test",
            "employee_email": "receipt.test@company.com",
            "employee_name": "Receipt Test",
            "department": "Finance",
            "role_level": "Standard",
            "manager_email": "obamigbade@gmail.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_auth_hotel_docs_test",
            "employee_email": "auth.hotel.docs.test@company.com",
            "employee_name": "Auth Hotel Docs Test",
            "department": "Sales",
            "role_level": "Standard",
            "manager_email": "obamigbade@gmail.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_auth_flight_docs_test",
            "employee_email": "auth.flight.docs.test@company.com",
            "employee_name": "Auth Flight Docs Test",
            "department": "Travel",
            "role_level": "Standard",
            "manager_email": "obamigbade@gmail.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        },
        {
            "employee_id": "emp_auth_rejection_test",
            "employee_email": "auth.rejection.test@company.com",
            "employee_name": "Auth Rejection Test",
            "department": "Compliance",
            "role_level": "Standard",
            "manager_email": "obamigbade@gmail.com",
            "default_per_diem_policy": "demo_company_default",
            "active": True
        }
    ]
    
    for emp in employees:
        emp.update({
            # Claim 5 belongs to unknown_company
            "company_id": "unknown_company" if emp["employee_id"] == "emp_unknown_policy" else "demo_company"
        })
        db.collection("employees").document(emp["employee_id"]).set(emp)
        
    print("=== Per Diem Seeding Completed ===")

if __name__ == "__main__":
    seed_data()

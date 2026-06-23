import sys
sys.path.append(".")
from unittest.mock import patch
from fastapi.testclient import TestClient
from submission_frontend.main import app


client = TestClient(app)

# Mock Firestore
from tests.unit.test_expense_reports_workflow import InMemoryFirestore
mock_db_instance = InMemoryFirestore()
mock_db_instance.collection("employees").document("employee@company.com").set({
    "employee_email": "employee@company.com",
    "employee_name": "Test Employee",
    "employee_id": "employee",
    "department": "Engineering",
    "manager_email": "manager@company.com",
    "active": True
})
mock_db_instance.collection("companies").document("demo_company").set({
    "company_id": "demo_company",
    "company_name": "Demo Company",
    "active": True
})
mock_db_instance.collection("company_policy_settings").document("default_policy").set({
    "company_id": "demo_company",
    "active": True,
    "default_meal_rate_per_day": 75.0,
    "default_lodging_rate_per_night": 250.0,
    "default_incidental_rate_per_day": 10.0
})


with patch("submission_frontend.main.db", mock_db_instance):
    # 1. Create and submit
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        report_id = client.post("/api/reports", json={"report_title": "April Site Visits"}).json()["report_id"]
        claim_resp = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "meals",
            "amount": 25.0,
            "business_purpose": "Lunch",
            "city": "San Francisco",
            "state": "CA",
            "travel_start_date": "2026-04-01",
            "travel_end_date": "2026-04-05"
        })
        print("CLAIM RESP:", claim_resp.json())
        client.post(f"/api/reports/{report_id}/submit", json={})

    # 2. Manager return
    manager_info = {
        "email": "manager@company.com",
        "role": "manager",
        "name": "Test Manager",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=manager_info):
        client.post(f"/api/reports/{report_id}/return", json={"reason": "Missing details"})

    # 3. Resubmit
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        client.post(f"/api/reports/{report_id}/submit", json={})

    # 4. Approve
    with patch("submission_frontend.main.get_current_user_and_role", return_value=manager_info):
        resp = client.post(f"/api/reports/{report_id}/approve")
        print("STATUS CODE:", resp.status_code)
        print("DETAIL:", resp.json())

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# --- In-Memory Mock Firestore Implementation ---

class MockDocumentSnapshot:
    def __init__(self, doc_id, data, collection=None):
        self.id = doc_id
        self._data = data
        self.exists = data is not None
        self.collection = collection

    @property
    def reference(self):
        return MockDocumentReference(self.id, self.collection)

    def to_dict(self):
        return self._data

class MockDocumentReference:
    def __init__(self, doc_id, collection):
        self.id = doc_id
        self.collection = collection

    def get(self):
        data = self.collection.store.get(self.id)
        return MockDocumentSnapshot(self.id, data, self.collection)

    def set(self, data, merge=False):
        if merge and self.id in self.collection.store:
            self.collection.store[self.id].update(data)
        else:
            self.collection.store[self.id] = data

    def update(self, data):
        if self.id in self.collection.store:
            self.collection.store[self.id].update(data)
        else:
            self.collection.store[self.id] = data

    def delete(self):
        if self.id in self.collection.store:
            del self.collection.store[self.id]

class MockQuery:
    def __init__(self, collection, filters=None, order=None, limit_val=None):
        self.collection = collection
        self.filters = filters or []
        self.order = order
        self.limit_val = limit_val

    def where(self, field, op, value):
        new_filters = list(self.filters)
        new_filters.append((field, op, value))
        return MockQuery(self.collection, new_filters, self.order, self.limit_val)

    def order_by(self, field, direction=None):
        return MockQuery(self.collection, self.filters, (field, direction), self.limit_val)

    def limit(self, num):
        return MockQuery(self.collection, self.filters, self.order, num)

    def get(self):
        docs = []
        for doc_id, data in self.collection.store.items():
            match = True
            for field, op, val in self.filters:
                # Firestore query filter evaluation
                doc_val = data.get(field)
                if op == "==":
                    if doc_val != val:
                        match = False
                        break
                elif op == "!=":
                    if doc_val == val:
                        match = False
                        break
                elif op == "<":
                    if doc_val is None or doc_val >= val:
                        match = False
                        break
                elif op == ">":
                    if doc_val is None or doc_val <= val:
                        match = False
                        break
            if match:
                docs.append(MockDocumentSnapshot(doc_id, data, self.collection))

        if self.order:
            field, direction = self.order
            docs.sort(key=lambda d: d.to_dict().get(field) or "", reverse=(direction == "DESCENDING"))

        if self.limit_val is not None:
            docs = docs[:self.limit_val]

        return docs

class MockCollectionReference:
    def __init__(self, name, store):
        self.name = name
        self.store = store

    def document(self, doc_id=None):
        if not doc_id:
            doc_id = str(uuid.uuid4())
        return MockDocumentReference(doc_id, self)

    def where(self, field, op, value):
        return MockQuery(self).where(field, op, value)

    def order_by(self, field, direction=None):
        return MockQuery(self).order_by(field, direction)

    def limit(self, num):
        return MockQuery(self).limit(num)

    def get(self):
        return MockQuery(self).get()

class InMemoryFirestore:
    def __init__(self):
        self.stores = {}

    def collection(self, name):
        if name not in self.stores:
            self.stores[name] = {}
        return MockCollectionReference(name, self.stores[name])


# --- Test Fixtures ---

@pytest.fixture
def mock_db():
    db_mock = InMemoryFirestore()
    # Seed mock data
    db_mock.collection("employees").document("employee@company.com").set({
        "employee_email": "employee@company.com",
        "employee_name": "Test Employee",
        "employee_id": "employee",
        "department": "Engineering",
        "manager_email": "manager@company.com",
        "active": True
    })
    db_mock.collection("employees").document("cra001.manager001@demo-company.com").set({
        "employee_email": "cra001.manager001@demo-company.com",
        "employee_name": "CRA 001 Manager 001",
        "employee_id": "cra001.manager001",
        "department": "Clinical Research",
        "manager_email": "manager001@demo-company.com",
        "active": True
    })
    db_mock.collection("companies").document("demo_company").set({
        "company_id": "demo_company",
        "company_name": "Demo Company",
        "active": True
    })
    db_mock.collection("company_policy_settings").document("default_policy").set({
        "company_id": "demo_company",
        "active": True,
        "default_meal_rate_per_day": 75.0,
        "default_lodging_rate_per_night": 250.0,
        "default_incidental_rate_per_day": 10.0
    })
    return db_mock

@pytest.fixture
def client(mock_db):
    with patch("submission_frontend.main.db", mock_db):
        from submission_frontend.main import app
        yield TestClient(app)


# --- Test Cases ---

def test_create_draft_report(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        response = client.post("/api/reports", json={
            "report_title": "April Site Visits",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-04-30",
            "company_id": "demo_company"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["report_title"] == "April Site Visits"
        assert data["status"] == "draft"
        assert data["employee_email"] == "employee@company.com"
        assert data["manager_email"] == "manager@company.com"
        assert data["total_claimed_amount"] == 0.0

        # Check document in mock DB
        report_id = data["report_id"]
        stored_report = mock_db.collection("expense_reports").document(report_id).get().to_dict()
        assert stored_report is not None
        assert stored_report["status"] == "draft"


def test_add_multiple_line_items_and_recalculate(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        # 1. Create draft report
        response = client.post("/api/reports", json={
            "report_title": "April Site Visits",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-04-30"
        })
        report = response.json()
        report_id = report["report_id"]

        # 2. Add first line item (Flight)
        response_claim1 = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "flight",
            "amount": 1350.0,
            "currency": "USD",
            "expense_date": "2026-04-05",
            "business_purpose": "Site visit flight"
        })
        assert response_claim1.status_code == 200
        claim1_data = response_claim1.json()
        assert claim1_data["amount"] == 1350.0

        # 3. Add second line item (Hotel)
        response_claim2 = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "hotel",
            "amount": 700.0,
            "currency": "USD",
            "expense_date": "2026-04-06",
            "business_purpose": "Site visit hotel stay"
        })
        assert response_claim2.status_code == 200

        # 4. Get report details and verify calculations
        response_detail = client.get(f"/api/reports/{report_id}")
        assert response_detail.status_code == 200
        detail_data = response_detail.json()
        assert len(detail_data["claims"]) == 2
        assert detail_data["report"]["total_claimed_amount"] == 2050.0


def test_patch_draft_report(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        response_create = client.post("/api/reports", json={"report_title": "April Site Visits"})
        report_id = response_create.json()["report_id"]

        # Patch title
        response_patch = client.patch(f"/api/reports/{report_id}", json={
            "report_title": "April Site Visits - Updated"
        })
        assert response_patch.status_code == 200
        assert response_patch.json()["report_title"] == "April Site Visits - Updated"


def test_delete_draft_line_item(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        response_create = client.post("/api/reports", json={"report_title": "April Site Visits"})
        report_id = response_create.json()["report_id"]

        response_add = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "meals",
            "amount": 50.0,
            "business_purpose": "Site meeting meal"
        })
        claim_id = response_add.json()["claim_id"]

        # Delete claim
        response_delete = client.delete(f"/api/reports/{report_id}/claims/{claim_id}")
        assert response_delete.status_code == 200
        
        # Verify claim count is 0
        response_detail = client.get(f"/api/reports/{report_id}")
        assert len(response_detail.json()["claims"]) == 0


def test_bulk_upload_documents_and_assign(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        # Create report and line item
        report_id = client.post("/api/reports", json={"report_title": "April Site Visits"}).json()["report_id"]
        claim_id = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "flight",
            "amount": 500.0,
            "business_purpose": "flight"
        }).json()["claim_id"]

        # Bulk upload documents (we'll mock file upload as standard form-data post)
        files = [
            ("files", ("receipt1.pdf", b"pdfcontent", "application/pdf")),
            ("files", ("receipt2.jpg", b"jpgcontent", "image/jpeg"))
        ]
        # We need to mock GCS upload inside GET /api/reports/{report_id}/documents
        # main.py POST /api/reports/{report_id}/documents handles GCS upload. Let's mock storage client if it raises exception.
        # Let's verify how documents endpoint is defined.
        with patch("submission_frontend.main.storage.Client") as mock_storage:
            mock_bucket = mock_storage.return_value.bucket.return_value
            mock_blob = mock_bucket.blob.return_value
            
            response_upload = client.post(f"/api/reports/{report_id}/documents", files=files)
            assert response_upload.status_code == 200
            uploaded_docs = response_upload.json()
            assert len(uploaded_docs) == 2
            assert uploaded_docs[0]["assigned_to_claim"] is False

            doc_id = uploaded_docs[0]["document_id"]
            
            # Assign document to claim
            response_assign = client.post(f"/api/reports/{report_id}/documents/{doc_id}/assign", json={
                "claim_id": claim_id,
                "doc_type": "receipt"
            })
            assert response_assign.status_code == 200
            assert response_assign.json()["assigned_to_claim"] is True
            assert response_assign.json()["claim_id"] == claim_id


def test_submit_report_validation_rules(client, mock_db) -> None:
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        report_id = client.post("/api/reports", json={"report_title": "April Site Visits"}).json()["report_id"]

        # Try submitting empty report -> should block (no claims)
        response_submit = client.post(f"/api/reports/{report_id}/submit", json={})
        assert response_submit.status_code == 400
        assert "at least one line item" in response_submit.json()["detail"].lower()

        # Add claim that requires document (e.g. above $50)
        claim_id = client.post(f"/api/reports/{report_id}/claims", json={
            "category": "flight",
            "amount": 1000.0,
            "business_purpose": "Flight"
        }).json()["claim_id"]

        # Submit report with missing required document -> should block
        response_submit2 = client.post(f"/api/reports/{report_id}/submit", json={})
        assert response_submit2.status_code == 400
        assert "required document(s) are missing" in response_submit2.json()["detail"].lower()

        # Satisfy required documents by adding document and assigning it
        with patch("submission_frontend.main.storage.Client") as mock_storage:
            files = [("files", ("flight_receipt.pdf", b"pdf", "application/pdf"))]
            doc_id = client.post(f"/api/reports/{report_id}/documents", files=files).json()[0]["document_id"]
            client.post(f"/api/reports/{report_id}/documents/{doc_id}/assign", json={
                "claim_id": claim_id,
                "doc_type": "flight_ticket_receipt"
            })

            # Submit report again -> should succeed
            response_submit3 = client.post(f"/api/reports/{report_id}/submit", json={})
            assert response_submit3.status_code == 200
            assert response_submit3.json()["status"] == "success"


def test_manager_queue_and_actions(client, mock_db) -> None:
    # 1. Create and submit a report
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Test Employee",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        report_id = client.post("/api/reports", json={"report_title": "April Site Visits"}).json()["report_id"]
        client.post(f"/api/reports/{report_id}/claims", json={
            "category": "meals",
            "amount": 25.0,
            "business_purpose": "Lunch",
            "travel_start_date": "2026-04-01",
            "travel_end_date": "2026-04-05",
            "city": "San Francisco",
            "state": "CA",
            "country": "US"
        })
        client.post(f"/api/reports/{report_id}/submit", json={})

    # 2. Manager views their review queue
    manager_info = {
        "email": "manager@company.com",
        "role": "manager",
        "name": "Test Manager",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=manager_info):
        response_queue = client.get("/api/reports")
        assert response_queue.status_code == 200
        reports_in_queue = response_queue.json()
        assert len(reports_in_queue) == 1
        assert reports_in_queue[0]["report_id"] == report_id

        # Return report to employee
        response_return = client.post(f"/api/reports/{report_id}/return", json={
            "reason": "Missing extra business details"
        })
        assert response_return.status_code == 200
        assert response_return.json()["status"] == "success"
        
        # Verify status in database
        stored_report = mock_db.collection("expense_reports").document(report_id).get().to_dict()
        assert stored_report["status"] == "returned_to_employee"
        assert stored_report["return_reason"] == "Missing extra business details"

    # 3. Employee resubmits
    with patch("submission_frontend.main.get_current_user_and_role", return_value=user_info):
        client.post(f"/api/reports/{report_id}/submit", json={})

    # 4. Manager approves report
    with patch("submission_frontend.main.get_current_user_and_role", return_value=manager_info):
        response_approve = client.post(f"/api/reports/{report_id}/approve")
        assert response_approve.status_code == 200
        assert response_approve.json()["status"] == "success"
        
        # Verify status in database
        stored_report = mock_db.collection("expense_reports").document(report_id).get().to_dict()
        assert stored_report["status"] == "approved_by_manager"


def test_finance_admin_global_access(client, mock_db) -> None:
    # Create two reports for different employees
    emp1 = {"email": "emp1@company.com", "role": "employee", "authenticated": True}
    emp2 = {"email": "emp2@company.com", "role": "employee", "authenticated": True}

    with patch("submission_frontend.main.get_current_user_and_role", return_value=emp1):
        client.post("/api/reports", json={"report_title": "Emp1 April Visits"})
    with patch("submission_frontend.main.get_current_user_and_role", return_value=emp2):
        client.post("/api/reports", json={"report_title": "Emp2 May Visits"})

    # Finance Admin views all reports
    admin_info = {
        "email": "finance-admin@company.com",
        "role": "finance_admin",
        "name": "Finance Admin",
        "authenticated": True
    }
    with patch("submission_frontend.main.get_current_user_and_role", return_value=admin_info):
        response = client.get("/api/reports")
        assert response.status_code == 200
        all_reports = response.json()
        # Should see both reports
        assert len(all_reports) >= 2

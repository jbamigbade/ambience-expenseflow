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
import time
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
    # Let's seed employee info
    db_mock.collection("employees").document("employee@company.com").set({
        "employee_email": "employee@company.com",
        "employee_name": "Test Employee",
        "employee_id": "employee",
        "department": "Engineering",
        "manager_email": "manager@company.com",
        "active": True
    })
    return db_mock

@pytest.fixture
def client(mock_db):
    with patch("submission_frontend.main.db", mock_db):
        from submission_frontend.main import app
        yield TestClient(app)


# --- Test Cases ---

def test_get_card_transactions_seeding(client, mock_db) -> None:
    user_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        response = client.get("/api/cards/transactions")
        assert response.status_code == 200
        data = response.json()
        
        # Verify default seeded transactions
        assert len(data) >= 7
        providers = [tx["provider"] for tx in data]
        assert "Ramp" in providers
        assert "Brex" in providers
        assert "Amex" in providers
        assert "Visa" in providers
        assert "Stripe Issuing" in providers
        assert "Mastercard" in providers
        assert "Plaid-style bank feed" in providers


def test_connect_card_feed_access_control(client, mock_db) -> None:
    # 1. Deny employee
    user_info = {
        "email": "employee@company.com",
        "role": "employee",
        "name": "Alice Employee",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        response = client.post("/api/cards/connect", json={
            "provider": "Ramp",
            "cardholder_name": "Alice Employee",
            "cardholder_email": "employee@company.com",
            "card_last4": "1234"
        })
        assert response.status_code == 403
        assert "Access denied" in response.text

    # 2. Allow finance_admin
    admin_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=admin_info):
        response = client.post("/api/cards/connect", json={
            "provider": "Visa",
            "cardholder_name": "Jane Admin",
            "cardholder_email": "finance-admin@company.com",
            "card_last4": "9999"
        })
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "success"
        assert "Successfully connected" in res_data["message"]
        assert len(res_data["transactions"]) == 3
        
        # Check audit log was created
        audit_logs = mock_db.collection("audit_logs").get()
        assert len(audit_logs) > 0
        audit_types = [log.to_dict()["event_type"] for log in audit_logs]
        assert "card_feed_connected" in audit_types


def test_match_receipt_flow(client, mock_db) -> None:
    # Setup card transaction in DB
    tx_id = "tx_test_match"
    mock_db.collection("card_transactions").document(tx_id).set({
        "transaction_id": tx_id,
        "provider": "Amex",
        "card_last4": "3001",
        "cardholder_name": "Alice Employee",
        "cardholder_email": "employee@company.com",
        "transaction_date": "2026-06-22",
        "amount": 350.00,
        "merchant": "Delta Air Lines",
        "currency": "USD",
        "reconciliation_status": "unreconciled",
        "matched_claim_id": None,
        "matched_receipt_url": None,
        "matched_receipt_name": None,
        "notes": "Flight to conference",
        "company_id": "demo_company"
    })

    user_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        # Match receipt
        response = client.post("/api/cards/match-receipt", json={
            "transaction_id": tx_id,
            "receipt_url": "https://example.com/delta-receipt.pdf",
            "receipt_name": "delta-receipt.pdf"
        })
        assert response.status_code == 200
        assert response.json()["reconciliation_status"] == "unreconciled"  # because matched_claim_id is not set yet
        
        # Verify update in DB
        tx_data = mock_db.collection("card_transactions").document(tx_id).get().to_dict()
        assert tx_data["matched_receipt_url"] == "https://example.com/delta-receipt.pdf"
        assert tx_data["matched_receipt_name"] == "delta-receipt.pdf"

        # Check audit log
        audit_logs = mock_db.collection("audit_logs").get()
        audit_types = [log.to_dict()["event_type"] for log in audit_logs]
        assert "card_receipt_matched" in audit_types


def test_attach_claim_flow(client, mock_db) -> None:
    tx_id = "tx_test_attach"
    claim_id = "claim_test_123"
    
    # Setup card transaction and expense claim in DB
    mock_db.collection("card_transactions").document(tx_id).set({
        "transaction_id": tx_id,
        "provider": "Brex",
        "card_last4": "4092",
        "amount": 42.00,
        "merchant": "Uber Trips",
        "reconciliation_status": "unreconciled",
        "matched_claim_id": None,
        "company_id": "demo_company"
    })
    mock_db.collection("expenses").document(claim_id).set({
        "claim_id": claim_id,
        "employee_email": "employee@company.com",
        "amount": 42.00,
        "category": "transportation",
        "status": "approved"
    })

    user_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        response = client.post("/api/cards/attach-claim", json={
            "transaction_id": tx_id,
            "claim_id": claim_id
        })
        assert response.status_code == 200
        
        # Verify transaction is updated
        tx_data = mock_db.collection("card_transactions").document(tx_id).get().to_dict()
        assert tx_data["matched_claim_id"] == claim_id
        assert tx_data["reconciliation_status"] == "matched"
        
        # Verify expense claim is updated
        claim_data = mock_db.collection("expenses").document(claim_id).get().to_dict()
        assert claim_data["payment_method"] == "Business Card"
        assert claim_data["card_transaction_id"] == tx_id
        assert claim_data["reconciliation_status"] == "matched"

        # Check audit log
        audit_logs = mock_db.collection("audit_logs").get()
        audit_types = [log.to_dict()["event_type"] for log in audit_logs]
        assert "card_transaction_matched" in audit_types


def test_reconcile_flow(client, mock_db) -> None:
    tx_id = "tx_test_reconcile"
    claim_id = "claim_test_456"
    
    mock_db.collection("card_transactions").document(tx_id).set({
        "transaction_id": tx_id,
        "provider": "Visa",
        "card_last4": "9876",
        "amount": 18.50,
        "merchant": "Starbucks",
        "reconciliation_status": "matched",
        "matched_claim_id": claim_id,
        "company_id": "demo_company"
    })
    mock_db.collection("expenses").document(claim_id).set({
        "claim_id": claim_id,
        "payment_method": "Business Card",
        "card_transaction_id": tx_id,
        "reconciliation_status": "matched"
    })

    user_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        response = client.post("/api/cards/reconcile", json={
            "transaction_id": tx_id
        })
        assert response.status_code == 200
        
        # Verify transaction status is updated
        tx_data = mock_db.collection("card_transactions").document(tx_id).get().to_dict()
        assert tx_data["reconciliation_status"] == "reconciled"
        
        # Verify claim status is updated
        claim_data = mock_db.collection("expenses").document(claim_id).get().to_dict()
        assert claim_data["reconciliation_status"] == "reconciled"

        # Check audit log
        audit_logs = mock_db.collection("audit_logs").get()
        audit_types = [log.to_dict()["event_type"] for log in audit_logs]
        assert "card_transaction_reconciled" in audit_types


def test_update_notes_flow(client, mock_db) -> None:
    tx_id = "tx_test_update"
    
    mock_db.collection("card_transactions").document(tx_id).set({
        "transaction_id": tx_id,
        "provider": "Stripe Issuing",
        "card_last4": "5544",
        "amount": 29.00,
        "merchant": "GitHub",
        "reconciliation_status": "unreconciled",
        "notes": "",
        "company_id": "demo_company"
    })

    user_info = {
        "email": "admin@company.com",
        "role": "finance_admin",
        "name": "Jane Admin",
        "authenticated": True
    }
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value=user_info):
        response = client.post("/api/cards/update", json={
            "transaction_id": tx_id,
            "notes": "GitHub Copilot team subscription update",
            "reconciliation_status": "unreconciled"
        })
        assert response.status_code == 200
        
        # Verify update in DB
        tx_data = mock_db.collection("card_transactions").document(tx_id).get().to_dict()
        assert tx_data["notes"] == "GitHub Copilot team subscription update"

        # Check audit log
        audit_logs = mock_db.collection("audit_logs").get()
        audit_types = [log.to_dict()["event_type"] for log in audit_logs]
        assert "card_transaction_edited" in audit_types

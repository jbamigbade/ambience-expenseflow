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
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from submission_frontend.main import app

client = TestClient(app)

def test_export_endpoints_access_control() -> None:
    # Test that employee (unauthorized) role gets 403 Forbidden
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value={
        "email": "employee@company.com",
        "role": "employee",
        "authenticated": True
    }):
        # Test POST
        response = client.post("/api/export/expenses/csv", json={"claim_ids": ["test-claim-1"]})
        assert response.status_code == 403
        assert "Only managers and finance admins can export data" in response.text

        response = client.post("/api/export/expenses/excel", json={"claim_ids": ["test-claim-1"]})
        assert response.status_code == 403

        response = client.post("/api/export/audit/csv", json={"claim_ids": ["test-claim-1"]})
        assert response.status_code == 403

        response = client.post("/api/export/audit/excel", json={"claim_ids": ["test-claim-1"]})
        assert response.status_code == 403

        # Test GET
        response = client.get("/api/export/expenses/csv")
        assert response.status_code == 403

def test_export_expenses_csv_authorized() -> None:
    # Test that finance_admin can export expenses CSV successfully
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value={
        "email": "admin@company.com",
        "role": "finance_admin",
        "authenticated": True
    }):
        mock_claims = [
            {
                "claim_id": "test-claim-1",
                "category": "office_supplies",
                "created_at": "2026-07-02T12:00:00Z",
                "employee_name": "Test Employee",
                "employee_email": "emp@company.com",
                "department": "Engineering",
                "manager_email": "mgr@company.com",
                "submitted_by_email": "emp@company.com",
                "amount": 120.50,
                "status": "approved",
                "reviewer_email": "mgr@company.com",
                "policy_status": "Within policy",
                "company_id": "demo_company"
            }
        ]
        with patch("submission_frontend.routes.api_routes.get_claims_for_export", return_value=mock_claims):
            response = client.post("/api/export/expenses/csv", json={"claim_ids": ["test-claim-1"]})
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "expenses_export.csv" in response.headers["content-disposition"]
            assert "test-claim-1" in response.text
            assert "office_supplies" in response.text
            assert "120.5" in response.text

def test_export_expenses_excel_authorized() -> None:
    # Test that finance_admin can export expenses Excel successfully
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value={
        "email": "admin@company.com",
        "role": "finance_admin",
        "authenticated": True
    }):
        mock_claims = [
            {
                "claim_id": "test-claim-1",
                "category": "office_supplies",
                "created_at": "2026-07-02T12:00:00Z",
                "employee_name": "Test Employee",
                "employee_email": "emp@company.com",
                "department": "Engineering",
                "manager_email": "mgr@company.com",
                "submitted_by_email": "emp@company.com",
                "amount": 120.50,
                "status": "approved",
                "reviewer_email": "mgr@company.com",
                "policy_status": "Within policy",
                "company_id": "demo_company"
            }
        ]
        with patch("submission_frontend.routes.api_routes.get_claims_for_export", return_value=mock_claims):
            response = client.post("/api/export/expenses/excel", json={"claim_ids": ["test-claim-1"]})
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "expenses_export.xlsx" in response.headers["content-disposition"]
            assert len(response.content) > 1000  # valid zip/xlsx payload bytes

def test_export_audit_csv_authorized() -> None:
    # Test that manager can export audit CSV successfully
    with patch("submission_frontend.routes.api_routes.get_current_user_and_role", return_value={
        "email": "manager@company.com",
        "role": "manager",
        "authenticated": True
    }):
        mock_claims = [
            {
                "claim_id": "test-claim-1",
                "employee_name": "Test Employee",
                "employee_email": "emp@company.com",
                "department": "Engineering",
                "manager_email": "mgr@company.com",
                "amount": 120.50,
                "status": "approved"
            }
        ]
        mock_audits = [
            (
                {
                    "claim_id": "test-claim-1",
                    "event_type": "employee_submitted_claim",
                    "event_message": "Claim submitted with total 120.50",
                    "actor_email": "emp@company.com",
                    "timestamp": "2026-07-02T12:00:00Z",
                    "metadata": {}
                },
                mock_claims[0]
            )
        ]
        with patch("submission_frontend.routes.api_routes.get_claims_for_export", return_value=mock_claims):
            with patch("submission_frontend.routes.api_routes.get_audits_for_export", return_value=mock_audits):
                response = client.post("/api/export/audit/csv", json={"claim_ids": ["test-claim-1"]})
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/csv; charset=utf-8"
                assert "audit_export.csv" in response.headers["content-disposition"]
                assert "test-claim-1" in response.text
                assert "employee_submitted_claim" in response.text
                assert "Claim submitted with total 120.50" in response.text

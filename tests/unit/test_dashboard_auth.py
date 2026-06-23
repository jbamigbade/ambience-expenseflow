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
import os
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient

# Import the helper functions from main
# We import from submission_frontend.main
from submission_frontend.main import (
    resolve_role,
    is_auth_enabled,
    get_current_user_and_role,
    app,
)

def test_resolve_role() -> None:
    # Test admin allowlist matching
    assert resolve_role("admin@company.com") == "finance_admin"
    assert resolve_role("finance-admin@company.com") == "finance_admin"
    assert resolve_role("default-user@company.com") == "finance_admin"
    
    # Test manager allowlist matching
    assert resolve_role("manager@company.com") == "manager"
    
    # Test employee domain matching
    assert resolve_role("any-employee@company.com") == "employee"
    assert resolve_role("another@company.com") == "employee"
    
    # Test external or unmatched emails
    assert resolve_role("unknown@gmail.com") == "employee"
    assert resolve_role(None) == "employee"

def test_is_auth_enabled_default() -> None:
    # Default is false
    assert is_auth_enabled() is False

def test_get_current_user_and_role_disabled_fallback() -> None:
    # When auth is disabled, it should return the fallback user details
    mock_request = MagicMock(spec=Request)
    user_info = get_current_user_and_role(mock_request)
    
    assert user_info["email"] == "default-user@company.com"
    assert user_info["role"] == "finance_admin"
    assert user_info["authenticated"] is False

def test_login_renders_successfully() -> None:
    client = TestClient(app)
    
    # Test with AUTH_ENABLED=true
    with patch("submission_frontend.main.is_auth_enabled", return_value=True):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Sign in with Google" in response.text
        
    # Test with AUTH_ENABLED=false
    with patch("submission_frontend.main.is_auth_enabled", return_value=False):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Local Test Mode Active" in response.text

def test_branding_regression() -> None:
    client = TestClient(app)
    
    # Verify login page contains the new branding and subtitle
    with patch("submission_frontend.main.is_auth_enabled", return_value=True):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Ambience ExpenseFlow" in response.text
        assert "Enterprise Travel & Expense Management" in response.text
        assert "<title>Sign In - Ambience ExpenseFlow</title>" in response.text

    # Verify dashboard page contains the new branding and subtitle
    with patch("submission_frontend.main.get_current_user_and_role", return_value={
        "email": "default-user@company.com",
        "role": "finance_admin",
        "authenticated": True
    }):
        response = client.get("/")
        assert response.status_code == 200
        assert "<title>Ambience ExpenseFlow Approval Dashboard</title>" in response.text
        assert "Ambience ExpenseFlow" in response.text
        assert "Enterprise Travel & Expense Management" in response.text

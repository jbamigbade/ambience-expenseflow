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
from submission_frontend.main import sanitize_claim_dict

def test_sanitize_empty_claim() -> None:
    claim = {}
    sanitized = sanitize_claim_dict(claim)
    
    assert sanitized["amount"] == 0.0
    assert sanitized["total_claimed_amount"] == 0.0
    assert sanitized["total_reimbursable_amount"] == 0.0
    assert sanitized["total_non_reimbursable_amount"] == 0.0
    assert sanitized["reimbursable_amount"] == 0.0
    assert sanitized["non_reimbursable_amount"] == 0.0
    assert sanitized["calculated_reimbursement_amount"] == 0.0
    assert sanitized["policy_exception_count"] == 0
    assert sanitized["missing_document_count"] == 0
    assert sanitized["claim_count"] == 0
    assert sanitized["status"] == "unknown"
    assert sanitized["category"] == "N/A"

def test_sanitize_string_numeric_values() -> None:
    claim = {
        "amount": "$1,250.50",
        "total_claimed_amount": " 500.00 ",
        "policy_exception_count": "3",
        "status": "pending",
        "category": "meals"
    }
    sanitized = sanitize_claim_dict(claim)
    
    assert sanitized["amount"] == 1250.50
    assert sanitized["total_claimed_amount"] == 500.00
    assert sanitized["policy_exception_count"] == 3
    assert sanitized["status"] == "pending"
    assert sanitized["category"] == "meals"

def test_sanitize_malformed_numeric_values() -> None:
    claim = {
        "amount": "not-a-number",
        "total_claimed_amount": None,
        "policy_exception_count": "invalid-int"
    }
    sanitized = sanitize_claim_dict(claim)
    
    assert sanitized["amount"] == 0.0
    assert sanitized["total_claimed_amount"] == 0.0
    assert sanitized["policy_exception_count"] == 0

def test_sanitize_per_diem_review() -> None:
    claim = {
        "per_diem_review": {
            "meal_rate_per_day": "$75.00",
            "allowed_meal_total": "300",
            "claimed_meals": None,
            "lodging_rate_per_night": "invalid",
        }
    }
    sanitized = sanitize_claim_dict(claim)
    pdr = sanitized["per_diem_review"]
    
    assert pdr["meal_rate_per_day"] == 75.0
    assert pdr["allowed_meal_total"] == 300.0
    assert pdr["claimed_meals"] == 0.0
    assert pdr["lodging_rate_per_night"] == 0.0

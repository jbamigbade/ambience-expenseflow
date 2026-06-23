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
from google.adk.agents.context import Context
from app.agent import route_expense, ExpenseClaim, Event

class MockContext(Context):
    def __init__(self, state=None):
        self._state = state or {}

    @property
    def state(self):
        return self._state

def test_office_supplies_under_50_with_purpose() -> None:
    # Under $50 with business purpose -> auto-approve
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="office_supplies",
        amount=45.0,
        description="USB Cable",
        business_purpose="Workplace connectivity"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "auto"

def test_office_supplies_above_50_missing_receipt() -> None:
    # Above $50, missing receipt -> force review (even if under $100)
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="office_supplies",
        amount=75.0,
        description="Office chair",
        business_purpose="Workplace comfort"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

def test_office_supplies_above_50_with_receipt() -> None:
    # Above $50, has receipt and purpose -> auto-approve
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="office_supplies",
        amount=75.0,
        description="Office chair",
        business_purpose="Workplace comfort",
        receipt_url="https://example.com/receipt.pdf"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "auto"

def test_office_supplies_missing_purpose() -> None:
    # Missing business purpose -> force review
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="office_supplies",
        amount=30.0,
        description="USB Cable"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

def test_office_supplies_above_250() -> None:
    # Above $250 -> force review
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="office_supplies",
        amount=275.0,
        description="Whiteboard",
        business_purpose="Brainstorming room",
        receipt_url="https://example.com/receipt.pdf"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

def test_business_parking_compliant() -> None:
    # Compliant parking under $100 -> auto-approve
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="business_parking",
        amount=35.0,
        description="Parking for client meeting",
        parking_date="2026-04-12",
        parking_location="Downtown Raleigh",
        business_purpose="Client engagement",
        parking_receipt_url="https://example.com/parking-receipt.pdf"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "auto"

def test_business_parking_missing_receipt() -> None:
    # Missing receipt -> force review
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="business_parking",
        amount=35.0,
        description="Parking for client meeting",
        parking_date="2026-04-12",
        parking_location="Downtown Raleigh",
        business_purpose="Client engagement"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

def test_business_parking_missing_meta() -> None:
    # Missing parking_date -> force review
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="business_parking",
        amount=35.0,
        description="Parking for client meeting",
        parking_location="Downtown Raleigh",
        business_purpose="Client engagement",
        parking_receipt_url="https://example.com/parking-receipt.pdf"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

def test_parking_citation_always_review() -> None:
    # Citations always force review
    ctx = MockContext()
    claim = ExpenseClaim(
        employee_name="test@company.com",
        category="parking_citation",
        amount=75.0,
        description="Overtime meter",
        parking_location="Downtown Raleigh",
        parking_date="2026-04-12",
        business_purpose="Client meeting",
        manager_approval_letter_url="https://example.com/letter.pdf"
    )
    event = route_expense._func(ctx, claim)
    assert event.actions.route == "review"

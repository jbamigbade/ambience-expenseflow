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
from app.agent import review_agent, ExpenseClaim, ExpenseResult, Event

class MockContext(Context):
    def __init__(self, resume_inputs=None, state=None):
        self._resume_inputs = resume_inputs or {}
        self._state = state or {}

    @property
    def resume_inputs(self):
        return self._resume_inputs

    @property
    def state(self):
        return self._state

@pytest.mark.asyncio
async def test_review_agent_approved_dict() -> None:
    # Test dictionary input: {"approved": True}
    ctx = MockContext(resume_inputs={"review_decision": {"approved": True}})
    claim = ExpenseClaim(employee_name="Alice", amount=250.0, description="Conference")
    
    events = []
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseResult)
    assert result.approved is True
    assert "approved" in result.comments.lower()

@pytest.mark.asyncio
async def test_review_agent_rejected_dict() -> None:
    # Test dictionary input: {"approved": False}
    ctx = MockContext(resume_inputs={"review_decision": {"approved": False}})
    claim = ExpenseClaim(employee_name="Alice", amount=250.0, description="Conference")
    
    events = []
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseResult)
    assert result.approved is False
    assert "rejected" in result.comments.lower()

@pytest.mark.asyncio
async def test_review_agent_stringified_dict() -> None:
    # Test stringified dictionary input: '{"approved": true}'
    ctx = MockContext(resume_inputs={"review_decision": '{"approved": true}'})
    claim = ExpenseClaim(employee_name="Alice", amount=250.0, description="Conference")
    
    events = []
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseResult)
    assert result.approved is True

@pytest.mark.asyncio
async def test_review_agent_python_literal_string() -> None:
    # Test Python literal representation string: "{'approved': False}"
    ctx = MockContext(resume_inputs={"review_decision": "{'approved': False}"})
    claim = ExpenseClaim(employee_name="Alice", amount=250.0, description="Conference")
    
    events = []
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseResult)
    assert result.approved is False

@pytest.mark.asyncio
async def test_review_agent_backward_compatibility() -> None:
    # Test older string response: "approve"
    ctx = MockContext(resume_inputs={"review_decision": "approve"})
    claim = ExpenseClaim(employee_name="Alice", amount=250.0, description="Conference")
    
    events = []
    async for event in review_agent._func(ctx, claim):
        events.append(event)
        
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    result = event.output
    assert isinstance(result, ExpenseResult)
    assert result.approved is True

    # Test older string response: "reject"
    ctx2 = MockContext(resume_inputs={"review_decision": "reject"})
    events2 = []
    async for event in review_agent._func(ctx2, claim):
        events2.append(event)
        
    assert len(events2) == 1
    event2 = events2[0]
    assert isinstance(event2, Event)
    result2 = event2.output
    assert isinstance(result2, ExpenseResult)
    assert result2.approved is False

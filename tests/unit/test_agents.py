"""
Unit tests for the lightweight multi-agent layer.
Verifies the behavior of individual agents (intake, compliance, routing, audit) and
the orchestrator coordinating the workflow.
"""

import pytest
from app.agents import (
    ExpenseIntakeAgent,
    PolicyComplianceAgent,
    ApprovalRoutingAgent,
    AuditIntelligenceAgent,
    ExpenseOrchestrator
)

@pytest.fixture
def valid_report_data():
    return {
        "report_id": "rep-999",
        "employee_name": "Alice Smith",
        "employee_email": "alice.smith@company.com",
        "purpose": "Annual Sales Conference",
        "total_amount": 250.0,
        "line_items": [
            {
                "category": "Meals",
                "amount": 50.0,
                "description": "Team Dinner",
                "receipt_url": "https://storage.googleapis.com/receipts/meals-1.jpg"
            },
            {
                "category": "Lodging",
                "amount": 200.0,
                "description": "Hotel Stay",
                "receipt_url": "https://storage.googleapis.com/receipts/hotel-1.jpg"
            }
        ]
    }

@pytest.fixture
def high_value_report_data():
    return {
        "report_id": "rep-1000",
        "employee_name": "Bob Jones",
        "employee_email": "bob.jones@company.com",
        "purpose": "Hardware Procurement",
        "total_amount": 1250.0,
        "line_items": [
            {
                "category": "Equipment",
                "amount": 1250.0,
                "description": "Developer Laptop",
                "receipt_url": "https://storage.googleapis.com/receipts/laptop.jpg"
            }
        ]
    }


def test_expense_intake_agent_valid(valid_report_data):
    """Verifies that a valid expense report passes intake validation."""
    agent = ExpenseIntakeAgent()
    result = agent.validate(valid_report_data)
    
    assert result["success"] is True
    assert len(result["errors"]) == 0


def test_expense_intake_agent_missing_fields():
    """Verifies that missing required fields fail intake validation."""
    agent = ExpenseIntakeAgent()
    bad_report = {
        "report_id": "rep-123",
        "total_amount": 100.0,
        "line_items": [{"amount": 100.0}]
    }
    result = agent.validate(bad_report)
    
    assert result["success"] is False
    assert any("Missing required field" in err for err in result["errors"])


def test_expense_intake_agent_missing_line_items(valid_report_data):
    """Verifies that missing line items fails intake validation."""
    agent = ExpenseIntakeAgent()
    
    # Empty list of line items
    report_no_items = valid_report_data.copy()
    report_no_items["line_items"] = []
    
    result = agent.validate(report_no_items)
    assert result["success"] is False
    assert "At least one line item is required" in result["errors"]
    
    # Missing line_items field entirely
    report_missing_field = valid_report_data.copy()
    del report_missing_field["line_items"]
    
    result2 = agent.validate(report_missing_field)
    assert result2["success"] is False
    assert "Missing 'line_items' field" in result2["errors"]


def test_policy_compliance_agent_missing_receipt(valid_report_data):
    """Verifies that missing receipts on items >= threshold creates warnings."""
    agent = PolicyComplianceAgent(receipt_threshold=25.0)
    
    # Modify second line item to remove receipt_url (amount is $200.0)
    no_receipt_report = {
        "report_id": "rep-999",
        "employee_name": "Alice Smith",
        "total_amount": 250.0,
        "line_items": [
            {
                "category": "Meals",
                "amount": 15.0, # Below threshold, no receipt required
                "description": "Quick lunch",
                "receipt_url": None
            },
            {
                "category": "Lodging",
                "amount": 235.0, # Above threshold, receipt required!
                "description": "Hotel stay",
                "receipt_url": "" # Empty receipt
            }
        ]
    }
    
    result = agent.evaluate(no_receipt_report)
    
    assert result["compliant"] is False
    assert len(result["warnings"]) == 1
    assert "requires a receipt but none was provided" in result["warnings"][0]


def test_policy_compliance_agent_compliant(valid_report_data):
    """Verifies fully compliant reports return no warnings."""
    agent = PolicyComplianceAgent()
    result = agent.evaluate(valid_report_data)
    
    assert result["compliant"] is True
    assert len(result["warnings"]) == 0


def test_approval_routing_agent_normal(valid_report_data):
    """Verifies that compliant, low-value reports are routed to standard manager approval."""
    agent = ApprovalRoutingAgent(finance_routing_threshold=500.0)
    
    compliance_result = {"compliant": True, "warnings": []}
    result = agent.determine_route(valid_report_data, compliance_result)
    
    assert result["route_to"] == "manager"
    assert "Routed to Manager Approval" in result["reason"]


def test_approval_routing_agent_high_value(high_value_report_data):
    """Verifies that high-value reports are routed to finance review."""
    agent = ApprovalRoutingAgent(finance_routing_threshold=500.0)
    
    compliance_result = {"compliant": True, "warnings": []}
    result = agent.determine_route(high_value_report_data, compliance_result)
    
    assert result["route_to"] == "finance_review"
    assert "escalation threshold" in result["reason"]


def test_approval_routing_agent_policy_violation(valid_report_data):
    """Verifies that non-compliant reports are routed to finance review regardless of amount."""
    agent = ApprovalRoutingAgent(finance_routing_threshold=500.0)
    
    compliance_result = {
        "compliant": False,
        "warnings": ["Line item requires a receipt but none was provided"]
    }
    result = agent.determine_route(valid_report_data, compliance_result)
    
    assert result["route_to"] == "finance_review"
    assert "Non-compliant flags detected" in result["reason"]


def test_audit_intelligence_agent():
    """Verifies the structured format of generated audit logs."""
    agent = AuditIntelligenceAgent()
    event = agent.create_event(
        event_type="test_event",
        message="Running agent unit test",
        actor="TestAgent",
        metadata={"key": "val"}
    )
    
    assert event["event_id"].startswith("evt-")
    assert "timestamp" in event
    assert event["event_type"] == "test_event"
    assert event["message"] == "Running agent unit test"
    assert event["actor"] == "TestAgent"
    assert event["metadata"] == {"key": "val"}


def test_orchestrator_expected_sections(valid_report_data):
    """Verifies that the orchestrator returns all required sections in its output."""
    orchestrator = ExpenseOrchestrator()
    result = orchestrator.process_report(valid_report_data)
    
    # Assert expected sections exist
    assert "validation_result" in result
    assert "policy_result" in result
    assert "routing_result" in result
    assert "audit_events" in result
    assert "final_recommendation" in result
    
    # Assert valid report details
    assert result["validation_result"]["success"] is True
    assert result["policy_result"]["compliant"] is True
    assert result["routing_result"]["route_to"] == "manager"
    assert result["final_recommendation"] == "ROUTE_TO_MANAGER"
    assert len(result["audit_events"]) > 0


def test_orchestrator_failure_handling():
    """Verifies orchestrator correctly halts and recommends rejection on invalid intake."""
    orchestrator = ExpenseOrchestrator()
    bad_report = {
        "report_id": "rep-bad",
        "employee_name": "", # empty name
        "total_amount": -10.0, # invalid negative amount
        "line_items": [] # empty line items
    }
    
    result = orchestrator.process_report(bad_report)
    
    assert result["validation_result"]["success"] is False
    assert result["final_recommendation"] == "REJECT_INTAKE"
    assert result["routing_result"]["route_to"] == "none"
    assert len(result["audit_events"]) == 1
    assert result["audit_events"][0]["event_type"] == "intake_validation_failed"

"""
Expense Orchestrator.
Coordinates the multi-agent execution pipeline. It receives an expense report,
runs it through validation, policy check, and routing agents, logs the audit trail,
and issues the final recommendation.
"""

from app.agents.expense_intake_agent import ExpenseIntakeAgent
from app.agents.policy_compliance_agent import PolicyComplianceAgent
from app.agents.approval_routing_agent import ApprovalRoutingAgent
from app.agents.audit_intelligence_agent import AuditIntelligenceAgent

class ExpenseOrchestrator:
    """
    Coordinates sub-agents to process an expense report from intake to final routing recommendation.
    """

    def __init__(self):
        self.intake_agent = ExpenseIntakeAgent()
        self.compliance_agent = PolicyComplianceAgent()
        self.routing_agent = ApprovalRoutingAgent()
        self.audit_agent = AuditIntelligenceAgent()

    def process_report(self, report: dict) -> dict:
        """
        Orchestrates the entire multi-agent review pipeline for the given expense report.
        
        Args:
            report (dict): The input expense report data.
            
        Returns:
            dict: The orchestration response containing:
                - "validation_result": dict
                - "policy_result": dict
                - "routing_result": dict
                - "audit_events": list of dict
                - "final_recommendation": str
        """
        audit_events = []
        report_id = report.get("report_id", "unknown-report-id")
        
        # 1. Intake Validation
        validation_result = self.intake_agent.validate(report)
        
        if not validation_result["success"]:
            # Create intake failure audit event
            failure_evt = self.audit_agent.create_event(
                event_type="intake_validation_failed",
                message=f"Report {report_id} failed intake validation with errors: {', '.join(validation_result['errors'])}",
                actor="ExpenseIntakeAgent",
                metadata={"errors": validation_result["errors"], "report_id": report_id}
            )
            audit_events.append(failure_evt)
            
            return {
                "validation_result": validation_result,
                "policy_result": {
                    "compliant": False,
                    "warnings": ["Report failed initial validation. Compliance evaluation skipped."]
                },
                "routing_result": {
                    "route_to": "none",
                    "reason": "Intake validation failed; processing halted."
                },
                "audit_events": audit_events,
                "final_recommendation": "REJECT_INTAKE"
            }
            
        # Intake success event
        success_evt = self.audit_agent.create_event(
            event_type="intake_validation_passed",
            message=f"Report {report_id} successfully passed intake validation.",
            actor="ExpenseIntakeAgent",
            metadata={"report_id": report_id}
        )
        audit_events.append(success_evt)
        
        # 2. Policy Compliance Check
        policy_result = self.compliance_agent.evaluate(report)
        
        if policy_result["compliant"]:
            comp_evt = self.audit_agent.create_event(
                event_type="policy_evaluation_compliant",
                message=f"Report {report_id} is fully compliant with company spending policies.",
                actor="PolicyComplianceAgent",
                metadata={"report_id": report_id}
            )
            audit_events.append(comp_evt)
        else:
            # Create individual warning audit events and a summary event
            for warning in policy_result["warnings"]:
                warning_evt = self.audit_agent.create_event(
                    event_type="policy_compliance_warning",
                    message=f"Compliance warning: {warning}",
                    actor="PolicyComplianceAgent",
                    metadata={"warning": warning, "report_id": report_id}
                )
                audit_events.append(warning_evt)
                
            comp_evt = self.audit_agent.create_event(
                event_type="policy_evaluation_non_compliant",
                message=f"Report {report_id} flagged with {len(policy_result['warnings'])} policy compliance warning(s).",
                actor="PolicyComplianceAgent",
                metadata={"warnings": policy_result["warnings"], "report_id": report_id}
            )
            audit_events.append(comp_evt)
            
        # 3. Approval Routing
        routing_result = self.routing_agent.determine_route(report, policy_result)
        
        route_evt = self.audit_agent.create_event(
            event_type="approval_route_determined",
            message=f"Routing decision made: {routing_result['reason']}",
            actor="ApprovalRoutingAgent",
            metadata={
                "route_to": routing_result["route_to"],
                "reason": routing_result["reason"],
                "report_id": report_id
            }
        )
        audit_events.append(route_evt)
        
        # Determine Final Recommendation
        route_to = routing_result["route_to"]
        if route_to == "finance_review":
            final_recommendation = "ROUTE_TO_FINANCE"
        else:
            final_recommendation = "ROUTE_TO_MANAGER"
            
        # Overall orchestration completed event
        completed_evt = self.audit_agent.create_event(
            event_type="orchestration_completed",
            message=f"Expense processing pipeline completed for report {report_id}. Recommendation: {final_recommendation}.",
            actor="ExpenseOrchestrator",
            metadata={"final_recommendation": final_recommendation, "report_id": report_id}
        )
        audit_events.append(completed_evt)
        
        return {
            "validation_result": validation_result,
            "policy_result": policy_result,
            "routing_result": routing_result,
            "audit_events": audit_events,
            "final_recommendation": final_recommendation
        }

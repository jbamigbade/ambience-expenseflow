"""
Approval Routing Agent.
Routes expense reports to either standard Manager Approval or escalated Finance Admin Review
based on total value, policy violations, and risk flags.
"""

class ApprovalRoutingAgent:
    """
    Decides the correct review channel (e.g. manager, finance) based on report attributes.
    """

    def __init__(self, finance_routing_threshold: float = 500.0):
        self.finance_routing_threshold = finance_routing_threshold

    def determine_route(self, report: dict, compliance_result: dict = None) -> dict:
        """
        Determines the routing path for the expense report.
        
        Args:
            report (dict): The expense report dictionary.
            compliance_result (dict, optional): The result dictionary from PolicyComplianceAgent.
            
        Returns:
            dict: A dictionary containing:
                - "route_to": str, either "manager" or "finance_review"
                - "reason": str, the explanation for the routing decision
        """
        total_amount = report.get("total_amount", 0.0)
        try:
            total_amount = float(total_amount)
        except (ValueError, TypeError):
            total_amount = 0.0

        reasons = []
        is_high_risk = False

        # Check compliance warnings if provided
        if compliance_result and not compliance_result.get("compliant", True):
            warnings = compliance_result.get("warnings", [])
            if warnings:
                is_high_risk = True
                reasons.append(f"Non-compliant flags detected: {len(warnings)} warning(s)")

        # Check high-value threshold
        if total_amount >= self.finance_routing_threshold:
            is_high_risk = True
            reasons.append(f"Total amount ${total_amount:.2f} meets or exceeds the finance escalation threshold of ${self.finance_routing_threshold:.2f}")

        if is_high_risk:
            reason_str = "; ".join(reasons)
            return {
                "route_to": "finance_review",
                "reason": f"Escalated to Finance Review due to: {reason_str}"
            }
        
        return {
            "route_to": "manager",
            "reason": f"Routed to Manager Approval (total ${total_amount:.2f} is within limit and fully compliant)"
        }

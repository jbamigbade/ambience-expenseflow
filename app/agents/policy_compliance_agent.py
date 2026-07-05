"""
Policy Compliance Agent.
Evaluates expense reports and individual line items against corporate rules,
such as receipt requirements for high-value items and overall spending thresholds.
Returns compliance evaluations and warnings.
"""

class PolicyComplianceAgent:
    """
    Checks receipt requirements and spending thresholds, returning structured warnings if violated.
    """

    def __init__(self, receipt_threshold: float = 25.0, report_limit: float = 500.0):
        self.receipt_threshold = receipt_threshold
        self.report_limit = report_limit

    def evaluate(self, report: dict) -> dict:
        """
        Evaluates the expense report for policy compliance.
        
        Returns:
            dict: A dictionary containing:
                - "compliant": bool, True if no critical warnings exist, False otherwise
                - "warnings": list of dict/str, descriptive warnings about non-compliant items
        """
        warnings = []
        
        total_amount = report.get("total_amount", 0.0)
        try:
            total_amount = float(total_amount)
        except (ValueError, TypeError):
            total_amount = 0.0

        # 1. Check report-level total amount threshold
        if total_amount > self.report_limit:
            warnings.append(
                f"Report total ${total_amount:.2f} exceeds the corporate threshold of ${self.report_limit:.2f}"
            )

        # 2. Check each line item's receipt requirement and amount limit
        line_items = report.get("line_items", [])
        for idx, item in enumerate(line_items):
            if not isinstance(item, dict):
                continue
                
            amount = item.get("amount", 0.0)
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0.0
                
            category = item.get("category", "Other")
            description = item.get("description", "No description")
            receipt_url = item.get("receipt_url")

            # Check receipt requirement
            if amount >= self.receipt_threshold:
                if not receipt_url or not str(receipt_url).strip():
                    warnings.append(
                        f"Line item {idx} ({category}: {description}) of ${amount:.2f} requires a receipt but none was provided"
                    )

            # Category-specific limits (e.g. meals limit)
            if category.lower() == "meals" and amount > 100.0:
                warnings.append(
                    f"Line item {idx} ({category}) of ${amount:.2f} exceeds the single meal policy limit of $100.00"
                )

        # Compliant if no warnings are returned
        return {
            "compliant": len(warnings) == 0,
            "warnings": warnings
        }

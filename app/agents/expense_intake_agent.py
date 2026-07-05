"""
Expense Intake Agent.
Validates that the incoming expense report contains all required top-level fields
and verifies that at least one line item exists.
"""

class ExpenseIntakeAgent:
    """
    Validates required fields in an expense report and ensures it has line items.
    """

    def __init__(self, required_fields=None):
        if required_fields is None:
            # Default required top-level fields
            self.required_fields = ["employee_name", "purpose", "total_amount"]
        else:
            self.required_fields = required_fields

    def validate(self, report: dict) -> dict:
        """
        Validates the given expense report dict.
        
        Returns:
            dict: A dictionary containing:
                - "success": bool, whether the report passes validation
                - "errors": list of str, validation error messages
        """
        errors = []

        if not isinstance(report, dict):
            return {
                "success": False,
                "errors": ["Expense report must be a dictionary"]
            }

        # Validate required top-level fields
        for field in self.required_fields:
            val = report.get(field)
            if val is None:
                errors.append(f"Missing required field: '{field}'")
            elif isinstance(val, str) and not val.strip():
                errors.append(f"Required field '{field}' cannot be empty")
            elif field == "total_amount":
                try:
                    amount_float = float(val)
                    if amount_float <= 0:
                        errors.append("Total amount must be greater than zero")
                except (ValueError, TypeError):
                    errors.append("Total amount must be a valid numeric value")

        # Validate line items
        line_items = report.get("line_items")
        if line_items is None:
            errors.append("Missing 'line_items' field")
        elif not isinstance(line_items, list):
            errors.append("'line_items' must be a list")
        elif len(line_items) == 0:
            errors.append("At least one line item is required")
        else:
            # Validate basic structure of each line item
            for idx, item in enumerate(line_items):
                if not isinstance(item, dict):
                    errors.append(f"Line item at index {idx} is malformed (must be a dictionary)")
                    continue
                
                # Check line item amount and category
                item_amount = item.get("amount")
                if item_amount is None:
                    errors.append(f"Line item {idx} is missing field: 'amount'")
                else:
                    try:
                        if float(item_amount) < 0:
                            errors.append(f"Line item {idx} has a negative amount")
                    except (ValueError, TypeError):
                        errors.append(f"Line item {idx} has an invalid amount")

        return {
            "success": len(errors) == 0,
            "errors": errors
        }

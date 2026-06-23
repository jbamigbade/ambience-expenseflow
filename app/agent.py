# ruff: noqa
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

import os
import google.auth
from pydantic import BaseModel, Field
from google.adk.workflow import Workflow, node, Edge, START
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.genai import types

# Set up environment
try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "project-5d38f91a-29a3-45bd-8d4"

os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


from typing import Optional, Union

class ExpenseClaim(BaseModel):
    employee_name: str = Field(description="Name of the employee submitting the claim.")
    amount: float = Field(description="The total amount of the expense claim in USD.")
    description: str = Field(
        description="A description or business justification for the expense."
    )
    category: Optional[str] = Field(default=None, description="The category of the expense.")
    travel_type: Optional[str] = Field(default=None, description="Type of travel (e.g. flight).")
    receipt_url: Optional[str] = Field(default=None, description="General receipt URL.")
    office_receipt_url: Optional[str] = Field(default=None, description="Office receipt URL.")
    parking_receipt_url: Optional[str] = Field(default=None, description="Parking receipt URL.")
    flight_ticket_receipt_url: Optional[str] = Field(default=None, description="Flight ticket receipt URL.")
    manager_approval_letter_url: Optional[str] = Field(default=None, description="Manager approval letter URL.")
    business_purpose: Optional[str] = Field(default=None, description="Business purpose.")
    parking_location: Optional[str] = Field(default=None, description="Parking location.")
    parking_date: Optional[str] = Field(default=None, description="Parking date.")
    item_type: Optional[str] = Field(default=None, description="Item type.")
    vendor: Optional[str] = Field(default=None, description="Vendor.")
    quantity: Optional[int] = Field(default=None, description="Quantity.")
    related_meeting: Optional[str] = Field(default=None, description="Related meeting.")
    related_client: Optional[str] = Field(default=None, description="Related client.")
    non_reimbursable_reason: Optional[str] = Field(default=None, description="Non-reimbursable reason.")


class ExpenseResult(BaseModel):
    approved: bool = Field(description="Whether the expense claim is approved.")
    approver: str = Field(description="The entity that approved or reviewed the claim.")
    comments: str = Field(description="Comments or justification for the decision.")


from typing import Union

@node
def route_expense(ctx: Context, node_input: Union[ExpenseClaim, str]) -> Event:
    """Routes the expense claim based on the amount and policy validation checks.

    If the amount is under $100, and all required documentation is present, routes to auto_approve.
    Otherwise, routes to review_agent.
    """
    if isinstance(node_input, str):
        # On resumption, retrieve original claim from state
        claim_dict = ctx.state.get("claim")
        if claim_dict:
            claim = ExpenseClaim(**claim_dict)
            return Event(output=claim, route="review", state={"review_decision": node_input})
        else:
            # Initial turn with a plain string (e.g., "Hi!" in mock/integration tests)
            claim = ExpenseClaim(employee_name="Guest", amount=0.0, description=node_input)
            return Event(output=claim, route="auto", state={"claim": claim.model_dump()})

    # Run policy check to decide if we must force manager review
    force_review = False
    cat = (node_input.category or "").strip().lower()
    amount = node_input.amount

    # 1. Office Supplies / Printing Supplies
    office_cats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"]
    if cat in office_cats:
        # Require a receipt_url or office_receipt_url for approval when amount is above $50
        has_receipt = bool(node_input.receipt_url or node_input.office_receipt_url)
        if amount > 50.0 and not has_receipt:
            force_review = True
        # Require business_purpose for approval
        if not node_input.business_purpose:
            force_review = True
        # Require review for any office supplies above $250
        if amount > 250.0:
            force_review = True

    # 2. Business Parking
    parking_cats = ["business_parking", "parking_fee"]
    if cat in parking_cats:
        # Require parking_receipt_url or receipt_url
        has_receipt = bool(node_input.parking_receipt_url or node_input.receipt_url)
        if not has_receipt:
            force_review = True
        # Require parking_date, parking_location, and business_purpose
        if not node_input.parking_date or not node_input.parking_location or not node_input.business_purpose:
            force_review = True

    # 3. Parking Tickets / Citations
    citation_cats = ["parking_ticket", "parking_citation"]
    if cat in citation_cats:
        # Fines always require review (they are potentially non-reimbursable)
        force_review = True

    # 4. Flight Ticket under $100
    travel_type_val = (node_input.travel_type or "").strip().lower()
    if cat in ["flight", "airfare"] or (cat == "travel" and travel_type_val == "flight"):
        if not node_input.flight_ticket_receipt_url:
            force_review = True

    route = "review" if (amount >= 100.0 or force_review) else "auto"
    return Event(output=node_input, route=route, state={"claim": node_input.model_dump()})


@node
def auto_approve(node_input: ExpenseClaim) -> Event:
    """Instantly approves claims under $100."""
    comments = f"Expense of ${node_input.amount:.2f} for '{node_input.description}' has been automatically approved as it is under $100."
    result = ExpenseResult(approved=True, approver="auto_approve", comments=comments)
    return Event(
        output=result,
        content=types.Content(
            role="model", parts=[types.Part.from_text(text=comments)]
        ),
    )


@node(rerun_on_resume=True)
async def review_agent(ctx: Context, node_input: ExpenseClaim):
    """Flags larger expenses ($100 or more) for human-in-the-loop review."""
    # Check if a review decision has been received in the resume inputs or in state
    decision = None
    if ctx.resume_inputs and "review_decision" in ctx.resume_inputs:
        decision = ctx.resume_inputs["review_decision"]
    elif ctx.state.get("review_decision"):
        decision = ctx.state.get("review_decision")

    if not decision:
        message = (
            f"⚠️ ATTENTION REQUIRED: Expense of ${node_input.amount:.2f} by "
            f"{node_input.employee_name} for '{node_input.description}' requires review.\n"
            f"Please reply with 'approve' or 'reject'."
        )
        yield RequestInput(interrupt_id="review_decision", message=message)
        return

    # Process the human response
    if isinstance(decision, str):
        decision_stripped = decision.strip()
        if (decision_stripped.startswith("{") and decision_stripped.endswith("}")) or (decision_stripped.startswith("[") and decision_stripped.endswith("]")):
            import json
            try:
                decision = json.loads(decision_stripped)
            except Exception:
                import ast
                try:
                    decision = ast.literal_eval(decision_stripped)
                except Exception:
                    pass

    if isinstance(decision, bool):
        approved = decision
        decision_str = "approved" if approved else "rejected"
    elif isinstance(decision, dict):
        val = decision.get("approved")
        if val is None:
            val = decision.get("response") or decision.get("result")
        if isinstance(val, bool):
            approved = val
            decision_str = "approved" if val else "rejected"
        elif isinstance(val, str) and val.strip().lower() in ("true", "false"):
            approved = val.strip().lower() == "true"
            decision_str = "approved" if approved else "rejected"
        elif val is not None:
            decision_str = str(val).strip().lower()
            approved = decision_str in ("yes", "y", "approve", "approved")
        else:
            decision_str = str(decision).strip().lower()
            approved = decision_str in ("yes", "y", "approve", "approved")
    else:
        decision_str = str(decision).strip().lower()
        if decision_str in ("true", "1"):
            approved = True
            decision_str = "approved"
        elif decision_str in ("false", "0"):
            approved = False
            decision_str = "rejected"
        else:
            approved = decision_str in ("yes", "y", "approve", "approved")


    if approved:
        comments = f"Expense of ${node_input.amount:.2f} approved by human reviewer."
    else:
        comments = f"Expense of ${node_input.amount:.2f} rejected by human reviewer (Reason: {decision_str})."

    result = ExpenseResult(
        approved=approved, approver="human_reviewer", comments=comments
    )
    yield Event(
        output=result,
        content=types.Content(
            role="model", parts=[types.Part.from_text(text=comments)]
        ),
        state={"review_decision": None},
    )


from typing import Union

root_agent = Workflow(
    name="ambient_expense_agent",
    input_schema=Union[ExpenseClaim, str],
    output_schema=ExpenseResult,
    edges=[
        Edge(from_node=START, to_node=route_expense),
        Edge(from_node=route_expense, to_node=auto_approve, route="auto"),
        Edge(from_node=route_expense, to_node=review_agent, route="review"),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)

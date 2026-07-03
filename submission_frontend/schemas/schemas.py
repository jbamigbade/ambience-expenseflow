from pydantic import BaseModel

class ApprovalAction(BaseModel):
    approved: bool
    interrupt_id: str = "review_decision"
    override_reason: str | None = None

class StateRatePayload(BaseModel):
    company_id: str = "demo_company"
    state: str
    state_code: str
    country: str = "US"
    cost_tier: str | None = None
    meal_rate_per_day: float
    lodging_rate_per_night: float
    incidental_rate_per_day: float = 0.0
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    active: bool = True
    source_note: str | None = None

class CityRatePayload(BaseModel):
    company_id: str = "demo_company"
    city: str
    state: str
    state_code: str
    country: str = "US"
    meal_rate_per_day: float
    lodging_rate_per_night: float
    incidental_rate_per_day: float = 0.0
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    active: bool = True
    source_note: str | None = None

class DefaultsPayload(BaseModel):
    company_id: str = "demo_company"
    policy_id: str | None = None
    policy_name: str = "Default Policy"
    description: str | None = None
    default_meal_rate_per_day: float
    default_lodging_rate_per_night: float
    default_incidental_rate_per_day: float = 0.0
    partial_day_percent: float = 1.0
    receipt_required_above: float = 50.0
    manager_approval_required_above: float = 350.0
    require_receipt_for_flights: bool = True
    require_manager_letter_for_flight_above: float = 1200.0
    require_manager_letter_for_lodging_above: float = 350.0
    active: bool = True

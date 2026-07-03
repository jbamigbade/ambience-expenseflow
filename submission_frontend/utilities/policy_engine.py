"""
Policy Engine for Expense Claim Review.
Evaluates compliance of claims against company per diem limits and custom category policies.
"""

from datetime import datetime
from submission_frontend.config.settings import logger, EXPENSES_COL
from submission_frontend.services.firestore_service import db

def run_per_diem_check(claim: dict) -> dict:
    """
    Evaluates policy compliance for per diem rate settings.
    """
    res = {
        "company_id": None,
        "company_name": "Unknown Company",
        "employee_id": None,
        "employee_name": "Unknown Employee",
        "employee_email": None,
        "travel_start_date": None,
        "travel_end_date": None,
        "travel_days": 0,
        "check_in_date": None,
        "check_out_date": None,
        "hotel_nights": 0,
        "city": None,
        "state": None,
        "state_code": None,
        "country": None,
        "policy_source": "N/A",
        "meal_rate_per_day": 0.0,
        "lodging_rate_per_night": 0.0,
        "incidental_rate_per_day": 0.0,
        "allowed_meal_total": 0.0,
        "allowed_lodging_total": 0.0,
        "allowed_incidental_total": 0.0,
        "claimed_meals": 0.0,
        "claimed_lodging": 0.0,
        "claimed_incidentals": 0.0,
        "claimed_amount": 0.0,
        "overage_meals": 0.0,
        "overage_lodging": 0.0,
        "overage_incidentals": 0.0,
        "overage_total": 0.0,
        "status": "Within company per diem",
        "warning": "",
        "is_incomplete": False,
        "require_manager_approval": False,
        "require_manager_letter": False,
        "manager_letter_uploaded": False
    }

    if not db:
        res["status"] = "Missing company policy"
        res["warning"] = "Database connection not available."
        res["is_incomplete"] = True
        return res

    company_id = claim.get("company_id") or ""
    if not company_id:
        company_id = "demo_company"
    res["company_id"] = company_id

    try:
        comp_doc = db.collection("companies").document(company_id).get()
        if comp_doc.exists:
            res["company_name"] = comp_doc.to_dict().get("company_name", "Unknown Company")
        else:
            if company_id == "demo_company":
                res["company_name"] = "Demo Company"
            else:
                res["company_name"] = company_id
    except Exception as e:
        logger.warning(f"Error fetching company doc: {e}")

    employee_email = claim.get("employee_email") or ""
    employee_name = claim.get("employee_name") or ""
    employee_id = claim.get("employee_id") or ""

    res["employee_email"] = employee_email
    res["employee_name"] = employee_name
    res["employee_id"] = employee_id

    emp_data = None
    try:
        if employee_email:
            emp_docs = list(db.collection("employees").where("employee_email", "==", employee_email).where("active", "==", True).limit(1).get())
            if emp_docs:
                emp_data = emp_docs[0].to_dict()
        if not emp_data and employee_name:
            emp_docs = list(db.collection("employees").where("employee_name", "==", employee_name).where("active", "==", True).limit(1).get())
            if emp_docs:
                emp_data = emp_docs[0].to_dict()
    except Exception as e:
        logger.warning(f"Error searching employees: {e}")

    if emp_data:
        res["employee_id"] = emp_data.get("employee_id")
        res["employee_name"] = emp_data.get("employee_name")
        res["employee_email"] = emp_data.get("employee_email")
        if emp_data.get("company_id"):
            company_id = emp_data.get("company_id")
            res["company_id"] = company_id
            try:
                comp_doc = db.collection("companies").document(company_id).get()
                if comp_doc.exists:
                    res["company_name"] = comp_doc.to_dict().get("company_name", "Unknown Company")
            except Exception:
                pass

    city = claim.get("city") or ""
    state = claim.get("state") or ""
    state_code = claim.get("state_code") or ""
    country = claim.get("country") or "US"

    if not state_code and len(state) == 2:
        state_code = state

    res["city"] = city
    res["state"] = state
    res["state_code"] = state_code
    res["country"] = country

    travel_start_str = claim.get("travel_start_date")
    travel_end_str = claim.get("travel_end_date")
    check_in_str = claim.get("check_in_date")
    check_out_str = claim.get("check_out_date")

    res["travel_start_date"] = travel_start_str
    res["travel_end_date"] = travel_end_str
    res["check_in_date"] = check_in_str
    res["check_out_date"] = check_out_str

    category = (claim.get("category") or "").lower()
    amount = float(claim.get("amount") or 0.0)
    res["claimed_amount"] = amount

    claimed_meals = float(claim.get("claimed_meals") or 0.0)
    claimed_lodging = float(claim.get("claimed_lodging") or 0.0)
    claimed_incidentals = float(claim.get("claimed_incidentals") or 0.0)

    if category == "meals":
        if claimed_meals == 0.0:
            claimed_meals = amount
    elif category in ["lodging", "hotel"]:
        if claimed_lodging == 0.0:
            claimed_lodging = amount
    elif category == "incidentals":
        if claimed_incidentals == 0.0:
            claimed_incidentals = amount

    res["claimed_meals"] = claimed_meals
    res["claimed_lodging"] = claimed_lodging
    res["claimed_incidentals"] = claimed_incidentals

    travel_days = 0
    if travel_start_str and travel_end_str:
        try:
            t_start = datetime.fromisoformat(travel_start_str.replace("Z", ""))
            t_end = datetime.fromisoformat(travel_end_str.replace("Z", ""))
            travel_days = (t_end - t_start).days
            if travel_days < 0:
                travel_days = 0
        except Exception as e:
            logger.warning(f"Error parsing travel dates: {e}")

    hotel_nights = 0
    if check_in_str and check_out_str:
        try:
            c_in = datetime.fromisoformat(check_in_str.replace("Z", ""))
            c_out = datetime.fromisoformat(check_out_str.replace("Z", ""))
            hotel_nights = (c_out - c_in).days
            if hotel_nights < 0:
                hotel_nights = 0
        except Exception as e:
            logger.warning(f"Error parsing hotel dates: {e}")

    res["travel_days"] = travel_days
    res["hotel_nights"] = hotel_nights

    rate_found = False
    meal_rate = 0.0
    lodging_rate = 0.0
    incidental_rate = 0.0
    policy_source = "N/A"

    if city and (state or state_code):
        try:
            city_query = db.collection("company_city_per_diem_rates")\
                .where("company_id", "==", company_id)\
                .where("city", "==", city)\
                .where("active", "==", True)
            city_docs = list(city_query.get())
            for doc in city_docs:
                doc_data = doc.to_dict()
                if doc_data.get("state_code") == state_code or doc_data.get("state") == state:
                    meal_rate = float(doc_data.get("meal_rate_per_day", 0.0))
                    lodging_rate = float(doc_data.get("lodging_rate_per_night", 0.0))
                    incidental_rate = float(doc_data.get("incidental_rate_per_day", 0.0))
                    policy_source = "company city rate"
                    rate_found = True
                    break
        except Exception as e:
            logger.warning(f"Error looking up city rate: {e}")

    if not rate_found and (state or state_code):
        try:
            state_query = db.collection("company_state_per_diem_rates")\
                .where("company_id", "==", company_id)\
                .where("active", "==", True)
            state_docs = list(state_query.get())
            for doc in state_docs:
                doc_data = doc.to_dict()
                if doc_data.get("state_code") == state_code or doc_data.get("state") == state:
                    meal_rate = float(doc_data.get("meal_rate_per_day", 0.0))
                    lodging_rate = float(doc_data.get("lodging_rate_per_night", 0.0))
                    incidental_rate = float(doc_data.get("incidental_rate_per_day", 0.0))
                    policy_source = "company state rate"
                    rate_found = True
                    break
        except Exception as e:
            logger.warning(f"Error looking up state rate: {e}")

    policy_settings = None
    if not rate_found and emp_data and emp_data.get("default_per_diem_policy"):
        policy_id = emp_data["default_per_diem_policy"]
        try:
            pol_doc = db.collection("company_policy_settings").document(policy_id).get()
            if pol_doc.exists and pol_doc.to_dict().get("active"):
                policy_settings = pol_doc.to_dict()
                meal_rate = float(policy_settings.get("default_meal_rate_per_day", 0.0))
                lodging_rate = float(policy_settings.get("default_lodging_rate_per_night", 0.0))
                incidental_rate = float(policy_settings.get("default_incidental_rate_per_day", 0.0))
                policy_source = "employee policy"
                rate_found = True
        except Exception as e:
            logger.warning(f"Error looking up employee policy settings: {e}")

    if not rate_found:
        try:
            default_query = db.collection("company_policy_settings")\
                .where("company_id", "==", company_id)\
                .where("active", "==", True)\
                .limit(1)
            default_docs = list(default_query.get())
            if default_docs:
                policy_settings = default_docs[0].to_dict()
                meal_rate = float(policy_settings.get("default_meal_rate_per_day", 0.0))
                lodging_rate = float(policy_settings.get("default_lodging_rate_per_night", 0.0))
                incidental_rate = float(policy_settings.get("default_incidental_rate_per_day", 0.0))
                policy_source = "company default"
                rate_found = True
        except Exception as e:
            logger.warning(f"Error looking up company default policy settings: {e}")

    if not rate_found:
        res["status"] = "Missing company policy"
        res["warning"] = "Per diem review incomplete — missing active company policy."
        res["is_incomplete"] = True
        return res

    res["policy_source"] = policy_source
    res["meal_rate_per_day"] = meal_rate
    res["lodging_rate_per_night"] = lodging_rate
    res["incidental_rate_per_day"] = incidental_rate

    res["allowed_meal_total"] = travel_days * meal_rate
    res["allowed_lodging_total"] = hotel_nights * lodging_rate
    res["allowed_incidental_total"] = travel_days * incidental_rate

    overage_meals = max(0.0, claimed_meals - res["allowed_meal_total"])
    overage_lodging = max(0.0, claimed_lodging - res["allowed_lodging_total"])
    overage_incidentals = max(0.0, claimed_incidentals - res["allowed_incidental_total"])

    res["overage_meals"] = overage_meals
    res["overage_lodging"] = overage_lodging
    res["overage_incidentals"] = overage_incidentals
    res["overage_total"] = overage_meals + overage_lodging + overage_incidentals

    is_missing_data = False
    if not travel_start_str or not travel_end_str:
        if category in ["meals", "incidentals", "travel"]:
            is_missing_data = True
    if not check_in_str or not check_out_str:
        if category in ["lodging", "hotel", "travel"]:
            is_missing_data = True
    if not city or not (state or state_code):
        is_missing_data = True
    if not emp_data:
        is_missing_data = True

    if is_missing_data:
        res["status"] = "Missing per diem data"
        res["warning"] = "Per diem review incomplete — missing travel dates, location, employee record, or active company policy."
        res["is_incomplete"] = True
        return res

    if res["overage_total"] > 0.0:
        res["status"] = "Exceeds company per diem"
        res["warning"] = f"Claim exceeds allowed company per diem by ${res['overage_total']:.2f}."
        res["require_manager_approval"] = True
        res["require_manager_letter"] = True
    else:
        res["status"] = "Within company per diem"

    manager_letter_uploaded = bool(claim.get("manager_approval_letter_url"))
    res["manager_letter_uploaded"] = manager_letter_uploaded

    if res["overage_total"] > 0.0:
        if manager_letter_uploaded:
            res["status"] = "Requires manager approval"

    return res

def run_policy_check_py(claim: dict) -> dict:
    """
    Python equivalent of runPolicyCheck JS logic to evaluate policy compliance.
    """
    result = {
        "is_valid": True,
        "category": claim.get("category") or "N/A",
        "nights": None,
        "cost_per_night": None,
        "required_docs": [],
        "missing_docs": [],
        "warnings": [],
        "status": "Within policy"
    }

    cat = (claim.get("category") or "").lower()
    amount = claim.get("amount") or 0.0

    # 0. Integrated Per Diem Check for travel/meals/lodging
    if cat in ["meals", "lodging", "hotel", "travel"]:
        pdr = run_per_diem_check(claim)
        claim["per_diem_review"] = pdr
        
        if pdr.get("status") == "Missing company policy":
            result["is_valid"] = False
            result["status"] = "Missing company policy"
            result["warnings"].append(pdr.get("warning"))
        elif pdr.get("status") == "Missing per diem data":
            result["is_valid"] = False
            result["status"] = "Missing per diem data"
            result["warnings"].append(pdr.get("warning"))
        elif pdr.get("status") == "Exceeds company per diem":
            result["is_valid"] = False
            result["status"] = "Exceeds company per diem"
            result["warnings"].append(pdr.get("warning"))
            result["required_docs"].append("Manager Approval Letter")
            if not pdr.get("manager_letter_uploaded"):
                result["missing_docs"].append("Manager Approval Letter")
        elif pdr.get("status") == "Requires manager approval":
            result["is_valid"] = True
            result["status"] = "Requires manager approval"
            result["warnings"].append(pdr.get("warning"))
    amount = claim.get("amount") or 0.0

    # 1. Lodging / Hotel Review
    if cat in ["lodging", "hotel"]:
        check_in_date = claim.get("check_in_date")
        check_out_date = claim.get("check_out_date")
        if check_in_date and check_out_date:
            try:
                check_in = datetime.fromisoformat(check_in_date.replace("Z", ""))
                check_out = datetime.fromisoformat(check_out_date.replace("Z", ""))
                diff = check_out - check_in
                diff_days = diff.days
                if diff_days > 0:
                    result["nights"] = diff_days
                    result["cost_per_night"] = amount / diff_days
                    
                    if result["cost_per_night"] > 350.0:
                        result["required_docs"].append("Manager Approval Letter")
                        if not claim.get("manager_approval_letter_url"):
                            result["missing_docs"].append("Manager Approval Letter")
                            result["warnings"].append("Manager approval letter required because lodging exceeds $350 per night.")
                            result["is_valid"] = False
                            result["status"] = "Requires manager approval letter"
            except Exception as e:
                logger.warning(f"Error parsing hotel dates in python check: {e}")

    # 2. Flight Ticket Review
    is_flight = cat in ["flight", "airfare"] or (cat == "travel" and (claim.get("travel_type") or "").lower() == "flight")
    if is_flight:
        result["required_docs"].append("Flight Ticket Receipt")
        if not claim.get("flight_ticket_receipt_url") and not claim.get("receipt_url"):
            result["missing_docs"].append("Flight Ticket Receipt")
            result["warnings"].append("Flight ticket receipt required.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"

        if amount > 1200.0:
            result["required_docs"].append("Manager Approval Letter")
            if not claim.get("manager_approval_letter_url"):
                result["missing_docs"].append("Manager Approval Letter")
                result["warnings"].append("Manager approval letter required because flight ticket exceeds $1200.")
                result["is_valid"] = False
                if result["status"] != "Needs documentation":
                    result["status"] = "Requires manager approval letter"

    if not result["is_valid"] and result["status"] == "Within policy":
        result["status"] = "Needs documentation"

    # 3. Office Supplies / Printing Supplies
    office_cats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"]
    if cat in office_cats:
        has_receipt = bool(claim.get("office_receipt_url") or claim.get("receipt_url"))
        if amount > 50.0:
            result["required_docs"].append("Receipt")
            if not has_receipt:
                result["missing_docs"].append("Receipt")
                result["warnings"].append("Receipt is required for office supplies above $50.")
                result["is_valid"] = False
                result["status"] = "Needs documentation"
        if not claim.get("business_purpose"):
            result["warnings"].append("Business purpose is required for office supplies.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"
        if amount > 250.0 and result["is_valid"]:
            result["status"] = "Requires manager approval"

    # 4. Business Parking
    parking_cats = ["business_parking", "parking_fee", "parking"]
    if cat in parking_cats:
        result["required_docs"].append("Parking Receipt")
        has_receipt = bool(claim.get("parking_receipt_url") or claim.get("receipt_url"))
        if not has_receipt:
            result["missing_docs"].append("Parking Receipt")
            result["warnings"].append("Parking receipt is required.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"
        if not claim.get("parking_date") and not claim.get("expense_date") and not claim.get("trip_date"):
            result["warnings"].append("Parking date is required.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"
        if not claim.get("parking_location") and not claim.get("destination_address"):
            result["warnings"].append("Parking location is required.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"
        if not claim.get("business_purpose"):
            result["warnings"].append("Business purpose is required.")
            result["is_valid"] = False
            result["status"] = "Needs documentation"
        if result["is_valid"]:
            result["status"] = "Within policy"

    # 5. Parking Tickets / Citations
    citation_cats = ["parking_ticket", "parking_citation"]
    if cat in citation_cats:
        result["required_docs"].append("Manager Approval Letter")
        if not claim.get("manager_approval_letter_url"):
            result["missing_docs"].append("Manager Approval Letter")
            result["is_valid"] = False
            result["status"] = "Potentially non-reimbursable"
            result["warnings"].append("Parking citation requires manager approval letter.")
        else:
            result["status"] = "Requires manager approval"

    # 6. Transportation / Rental Car / Gas / Tolls
    if cat in ["transportation", "tolls", "rental_car", "rental_car_gas"]:
        trans_type = (claim.get("transportation_type") or "").lower()
        if cat == "rental_car" and not trans_type:
            trans_type = "rental_car"
        if cat == "rental_car_gas" and not trans_type:
            trans_type = "rental_car_gas"

        if trans_type == "personal_vehicle" or cat == "transportation" and trans_type == "personal_vehicle":
            gas_cost = float(claim.get("gas_cost") or 0.0)
            if gas_cost > 0:
                result["warnings"].append("Personal vehicle gas is not separately reimbursable.")
                result["is_valid"] = False
                result["status"] = "Personal vehicle gas is not separately reimbursable"

        if trans_type == "rental_car" or cat == "rental_car":
            result["required_docs"].append("Rental Receipt")
            if not claim.get("rental_receipt_url"):
                result["missing_docs"].append("Rental Receipt")
                result["warnings"].append("Rental car requires rental receipt.")
                result["is_valid"] = False
                result["status"] = "Needs documentation"

        if trans_type == "rental_car_gas" or cat == "rental_car_gas":
            result["required_docs"].append("Gas Receipt")
            has_rental_context = bool(claim.get("rental_receipt_url") or claim.get("linked_rental_claim_id"))
            if not claim.get("gas_receipt_url") or not has_rental_context:
                if not claim.get("gas_receipt_url"):
                    result["missing_docs"].append("Gas Receipt")
                result["warnings"].append("Rental gas requires gas receipt and rental car context.")
                result["is_valid"] = False
                result["status"] = "Needs documentation"

    return result

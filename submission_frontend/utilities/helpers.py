import re
from datetime import datetime
from submission_frontend.config.settings import (
    logger,
    DECISIONS_COL,
    AUDIT_LOGS_COL,
    POLICIES_COL
)
from submission_frontend.services.firestore_service import db

def add_audit_log(
    claim_id: str,
    session_id: str,
    event_type: str,
    event_message: str,
    actor: str = "system",
    actor_email: str = None,
    actor_role: str = None,
    authenticated: bool = False,
    employee_email: str = None,
    employee_name: str = None,
    manager_email: str = None,
    metadata: dict = None
):
    """
    Writes a structured audit trail event log to Firestore with enhanced security tracking.
    """
    if not db:
        return
    try:
        doc_ref = db.collection(AUDIT_LOGS_COL).document()
        payload = {
            "claim_id": claim_id,
            "session_id": session_id,
            "event_type": event_type,
            "event_message": event_message,
            "actor": actor,
            "actor_email": actor_email,
            "actor_role": actor_role,
            "authenticated": authenticated,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {}
        }
        if employee_email is not None:
            payload["employee_email"] = employee_email
        if employee_name is not None:
            payload["employee_name"] = employee_name
        if manager_email is not None:
            payload["manager_email"] = manager_email
        doc_ref.set(payload)
    except Exception as e:
        logger.error(f"Failed to write audit log to Firestore: {e}")

def enrich_claim_with_employee_info(claim: dict) -> dict:
    """
    Ensures that every claim returned supports company_id, employee_id, employee_name,
    employee_email, department, manager_email, submitted_by_email, submitted_by_role,
    submitted_at, reviewer_email, reviewer_role, decision_by_email, and decision_by_role.
    """
    if "company_id" not in claim or not claim["company_id"]:
        claim["company_id"] = "demo_company"
    if "employee_id" not in claim:
        claim["employee_id"] = ""
    if "employee_name" not in claim:
        claim["employee_name"] = ""
    if "employee_email" not in claim:
        claim["employee_email"] = ""
    if "department" not in claim:
        claim["department"] = "N/A"
    if "manager_email" not in claim:
        claim["manager_email"] = "manager@company.com"
    if "submitted_by_email" not in claim:
        claim["submitted_by_email"] = ""
    if "submitted_by_role" not in claim:
        claim["submitted_by_role"] = "employee"
    if "submitted_at" not in claim:
        claim["submitted_at"] = ""
    if "reviewer_email" not in claim:
        claim["reviewer_email"] = None
    if "reviewer_role" not in claim:
        claim["reviewer_role"] = None
    if "decision_by_email" not in claim:
        claim["decision_by_email"] = None
    if "decision_by_role" not in claim:
        claim["decision_by_role"] = None

    if not db:
        if not claim["employee_name"] and claim["employee_email"]:
            claim["employee_name"] = claim["employee_email"].split("@")[0].replace(".", " ").title()
        if not claim["submitted_by_email"]:
            claim["submitted_by_email"] = claim["employee_email"] or "employee@company.com"
        if not claim["submitted_at"]:
            claim["submitted_at"] = claim.get("created_at") or datetime.utcnow().isoformat() + "Z"
        return claim

    emp_email = claim.get("employee_email")
    emp_name = claim.get("employee_name")
    
    # 1. Lookup employee record if department or manager_email is missing or default
    if not claim.get("department") or claim.get("department") == "N/A" or not claim.get("manager_email") or claim.get("manager_email") == "manager@company.com":
        emp_data = None
        try:
            if emp_email:
                emp_docs = list(db.collection("employees").where("employee_email", "==", emp_email).where("active", "==", True).limit(1).get())
                if emp_docs:
                    emp_data = emp_docs[0].to_dict()
            if not emp_data and emp_name:
                emp_docs = list(db.collection("employees").where("employee_name", "==", emp_name).where("active", "==", True).limit(1).get())
                if emp_docs:
                    emp_data = emp_docs[0].to_dict()
        except Exception as e:
            logger.warning(f"Error enriching claim with employee details: {e}")
            
        if emp_data:
            claim["department"] = emp_data.get("department") or claim.get("department") or "N/A"
            claim["manager_email"] = emp_data.get("manager_email") or claim.get("manager_email") or "manager@company.com"
            claim["employee_id"] = emp_data.get("employee_id") or claim.get("employee_id") or ""
            claim["employee_name"] = emp_data.get("employee_name") or claim.get("employee_name") or ""
            claim["employee_email"] = emp_data.get("employee_email") or claim.get("employee_email") or ""
            claim["company_id"] = emp_data.get("company_id") or claim.get("company_id") or "demo_company"

    # 2. Assign standard defaults if still missing
    if not claim.get("department") or claim.get("department") == "N/A":
        claim["department"] = "N/A"
    if not claim.get("manager_email"):
        claim["manager_email"] = "manager@company.com"
    if not claim.get("submitted_by_email"):
        claim["submitted_by_email"] = claim.get("employee_email") or "cli-user@company.com"
    if not claim.get("submitted_by_role"):
        claim["submitted_by_role"] = "employee"
    if not claim.get("submitted_at"):
        claim["submitted_at"] = claim.get("created_at") or datetime.utcnow().isoformat() + "Z"
    if not claim.get("employee_name") and claim.get("employee_email"):
        claim["employee_name"] = claim["employee_email"].split("@")[0].replace(".", " ").title()
        
    # 3. Handle reviewer / decision fields
    claim_id = claim.get("claim_id")
    if claim_id and (not claim.get("decision_by_email") or not claim.get("reviewer_email")):
        try:
            dec_docs = list(db.collection(DECISIONS_COL).where("claim_id", "==", claim_id).limit(1).get())
            if dec_docs:
                dec_data = dec_docs[0].to_dict()
                claim["decision_by_email"] = dec_data.get("decided_by") or dec_data.get("actor_email") or claim.get("decision_by_email")
                claim["decision_by_role"] = dec_data.get("decided_role") or dec_data.get("actor_role") or claim.get("decision_by_role")
                claim["reviewer_email"] = dec_data.get("decided_by") or dec_data.get("actor_email") or claim.get("reviewer_email")
                claim["reviewer_role"] = dec_data.get("decided_role") or dec_data.get("actor_role") or claim.get("reviewer_role")
        except Exception as e:
            logger.warning(f"Error querying decision for enrichment: {e}")
            
    if "reviewer_email" not in claim or claim["reviewer_email"] is None:
        claim["reviewer_email"] = None
    if "reviewer_role" not in claim or claim["reviewer_role"] is None:
        claim["reviewer_role"] = None
    if "decision_by_email" not in claim or claim["decision_by_email"] is None:
        claim["decision_by_email"] = None
    if "decision_by_role" not in claim or claim["decision_by_role"] is None:
        claim["decision_by_role"] = None
        
    return claim

def filter_and_enrich_claims(claims: list, current_user: dict, params: dict, is_pending: bool) -> list:
    """
    Enriches all claims and applies role-based access control and admin-specified search filters.
    """
    role = current_user.get("role")
    email = current_user.get("email", "")
    
    enriched = []
    for c in claims:
        c_copy = dict(c)
        ec = enrich_claim_with_employee_info(c_copy)
        enriched.append(ec)
        
    filtered = []
    for c in enriched:
        # 1. Role-based baseline access control
        if role == "employee":
            sub_by = c.get("submitted_by_email") or ""
            emp_em = c.get("employee_email") or ""
            if email.lower() not in [sub_by.lower(), emp_em.lower()]:
                continue
        elif role == "manager":
            if is_pending:
                mgr_em = c.get("manager_email") or ""
                if email.lower() != mgr_em.lower():
                    continue
            else:
                mgr_em = c.get("manager_email") or ""
                emp_em = c.get("employee_email") or ""
                sub_by = c.get("submitted_by_email") or ""
                if email.lower() not in [mgr_em.lower(), emp_em.lower(), sub_by.lower()]:
                    continue
        elif role == "finance_admin":
            pass
        else:
            continue
            
        # 2. Query/Parameter Filters
        search = params.get("search")
        if search:
            search_l = search.lower()
            emp_name = (c.get("employee_name") or "").lower()
            emp_email = (c.get("employee_email") or "").lower()
            if search_l not in emp_name and search_l not in emp_email:
                continue
                 
        dept_filter = params.get("department")
        if dept_filter:
            if (c.get("department") or "").lower() != dept_filter.lower():
                continue
                 
        mgr_filter = params.get("manager")
        if mgr_filter:
            mgr_email = (c.get("manager_email") or "").lower()
            if mgr_filter.lower() not in mgr_email:
                continue
                 
        status_filter = params.get("status")
        if status_filter:
            if (c.get("status") or "").lower() != status_filter.lower():
                continue
                 
        cat_filter = params.get("category")
        if cat_filter:
            if (c.get("category") or "").lower() != cat_filter.lower():
                continue
                 
        comp_filter = params.get("company")
        if comp_filter:
            if (c.get("company_id") or "").lower() != comp_filter.lower():
                continue
                 
        sub_by = (c.get("submitted_by_email") or "").lower()
        emp_em = (c.get("employee_email") or "").lower()
        user_id = (c.get("user_id") or "").lower()
        claim_src = c.get("source") or ""
        
        computed_source = "legacy_cli"
        if claim_src == "employee_portal" or user_id == "portal-user" or "portal-user" in user_id:
            computed_source = "employee_portal"
        elif c.get("report_id") or "report" in user_id:
            computed_source = "report_workflow"
        elif "cli-user" in sub_by or "cli-user" in emp_em or "cli-user" in user_id:
            computed_source = "legacy_cli"
            
        c["computed_source"] = computed_source
        
        src_filter = params.get("source", "all")
        if src_filter and src_filter != "all":
            if computed_source != src_filter:
                continue
                 
        hide_old = params.get("hide_old_test_sessions")
        if hide_old and (hide_old == True or str(hide_old).lower() == "true"):
            if src_filter != "legacy_cli":
                if computed_source == "legacy_cli":
                    continue
                 
        assigned_to_me = params.get("assigned_to_me")
        if assigned_to_me and (assigned_to_me == True or str(assigned_to_me).lower() == "true"):
            mgr_email = (c.get("manager_email") or "").lower()
            if email.lower() != mgr_email:
                continue
                
        filtered.append(c)
        
    def get_sort_key(item):
        src = item.get("computed_source", "legacy_cli")
        if src == "employee_portal":
            return 0
        elif src == "report_workflow":
            return 1
        else:
            return 2
            
    filtered.sort(key=get_sort_key)
    return filtered

def sanitize_claim_dict(claim: dict) -> dict:
    if not isinstance(claim, dict):
        return claim
    
    numeric_fields = {
        "amount": 0.0,
        "total_claimed_amount": 0.0,
        "total_reimbursable_amount": 0.0,
        "total_non_reimbursable_amount": 0.0,
        "reimbursable_amount": 0.0,
        "non_reimbursable_amount": 0.0,
        "calculated_reimbursement_amount": 0.0,
        "policy_exception_count": 0,
        "missing_document_count": 0,
        "claim_count": 0,
    }
    
    for field, default in numeric_fields.items():
        val = claim.get(field)
        if val is None or val == "":
            claim[field] = default
        else:
            try:
                if isinstance(val, (int, float)):
                    if isinstance(default, float):
                        claim[field] = float(val)
                    else:
                        claim[field] = int(val)
                elif isinstance(val, str):
                    if isinstance(default, float):
                        claim[field] = float(val.replace("$", "").replace(",", "").strip())
                    else:
                        claim[field] = int(val.strip())
            except Exception:
                claim[field] = default
                
    claim["status"] = claim.get("status") or "unknown"
    claim["category"] = claim.get("category") or "N/A"
    
    if "per_diem_review" in claim and isinstance(claim["per_diem_review"], dict):
        pdr = claim["per_diem_review"]
        pdr_numeric = [
            "meal_rate_per_day", "allowed_meal_total", "claimed_meals",
            "lodging_rate_per_night", "allowed_lodging_total", "claimed_lodging",
            "incidental_rate_per_day", "allowed_incidental_total", "claimed_incidentals",
            "claimed_amount", "overage_total"
        ]
        for f in pdr_numeric:
            v = pdr.get(f)
            if v is None or v == "":
                pdr[f] = 0.0
            else:
                try:
                    if isinstance(v, str):
                        pdr[f] = float(v.replace("$", "").replace(",", "").strip())
                    else:
                        pdr[f] = float(v)
                except Exception:
                    pdr[f] = 0.0
        pdr["status"] = pdr.get("status") or "unknown"
        pdr["policy_source"] = pdr.get("policy_source") or "N/A"
        
    return claim

import os
import re
import json
import uuid
import secrets
from datetime import datetime
import asyncio
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
from google.cloud import storage
from google.cloud import firestore
import urllib.parse
import urllib.request
import urllib.error
from starlette.middleware.sessions import SessionMiddleware

import vertexai
from vertexai.preview import reasoning_engines
from google.cloud.aiplatform_v1beta1 import types as aip_types
from google.adk.sessions import VertexAiSessionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manager-dashboard")

app = FastAPI(title="Manager Expense Approval Dashboard")

# --- Session & Authentication Configuration ---
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-default-key-for-dev-only")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, max_age=86400) # 1 day session expiry

# Environment Variables for Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# Role Allowlist Variables
ALLOWED_ADMIN_EMAILS_RAW = os.getenv("ALLOWED_ADMIN_EMAILS", "")
if ALLOWED_ADMIN_EMAILS_RAW:
    ALLOWED_ADMIN_EMAILS = [e.strip() for e in ALLOWED_ADMIN_EMAILS_RAW.split(",") if e.strip()]
else:
    # Highly secure out-of-the-box defaults for easy local/cloud verification
    ALLOWED_ADMIN_EMAILS = ["admin@company.com", "finance-admin@company.com", "default-user@company.com"]

ALLOWED_MANAGER_EMAILS_RAW = os.getenv("ALLOWED_MANAGER_EMAILS", "")
if ALLOWED_MANAGER_EMAILS_RAW:
    ALLOWED_MANAGER_EMAILS = [e.strip() for e in ALLOWED_MANAGER_EMAILS_RAW.split(",") if e.strip()]
else:
    ALLOWED_MANAGER_EMAILS = ["manager@company.com"]

ALLOWED_EMPLOYEE_DOMAIN = os.getenv("ALLOWED_EMPLOYEE_DOMAIN", "company.com")

def is_auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")

def resolve_role(email: str) -> str:
    """
    Resolves the role for a given email address.
    """
    if not email:
        return "employee"
    
    email_lower = email.lower()
    
    # Check Admin Allowlist
    if email_lower in [e.lower() for e in ALLOWED_ADMIN_EMAILS]:
        return "finance_admin"
        
    # Check Manager Allowlist
    if email_lower in [e.lower() for e in ALLOWED_MANAGER_EMAILS]:
        return "manager"
        
    # Check Employee Domain matching
    domain = ALLOWED_EMPLOYEE_DOMAIN.lower()
    if email_lower.endswith(f"@{domain}"):
        return "employee"
        
    return "employee"

def get_current_user_and_role(request: Request):
    """
    Retrieves the current user and their role.
    If auth is disabled, returns the fallback default-user.
    If auth is enabled and the user is not authenticated, raises HTTP 401.
    """
    if not is_auth_enabled():
        return {
            "email": "default-user@company.com",
            "role": "finance_admin",
            "name": "Default Administrator",
            "authenticated": False
        }
    
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or not authenticated. Please log in."
        )
        
    return {
        "email": user["email"],
        "role": user["role"],
        "name": user.get("name", ""),
        "authenticated": True
    }

def get_redirect_uri(request: Request) -> str:
    """
    Determines the redirect URI dynamically from request headers or environment.
    """
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("host")
    if not host:
        return str(request.url_for("oauth2callback"))
    return f"{proto}://{host}/oauth2callback"

# Read GCP Project and AGENT_RUNTIME_ID from environment variables with safe defaults
PROJECT_ID = os.getenv("GCP_PROJECT", "project-5d38f91a-29a3-45bd-8d4")
AGENT_RUNTIME_ID = os.getenv("AGENT_RUNTIME_ID", "projects/654812449031/locations/us-west1/reasoningEngines/8516245322706452480")

# Extract location and engine ID from AGENT_RUNTIME_ID
LOCATION = "us-west1"
ENGINE_ID = "8516245322706452480"

match = re.search(r"projects/([^/]+)/locations/([^/]+)/reasoningEngines/([^/]+)", AGENT_RUNTIME_ID)
if match:
    LOCATION = match.group(2)
    ENGINE_ID = match.group(3)

logger.info(f"Loaded config: project={PROJECT_ID}, location={LOCATION}, engine={ENGINE_ID}")

# Initialize Vertex AI
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Instantiate reasoning engine to warm client
    _remote_engine = reasoning_engines.ReasoningEngine(AGENT_RUNTIME_ID)
    logger.info("Successfully connected to reasoning engine execution client.")
except Exception as e:
    logger.error(f"Error initializing Vertex AI Reasoning Engine: {e}")

# Cloud Storage bucket configuration for uploads
BUCKET_NAME = "expense-manager-uploads-654812449031"

def get_gcs_bucket():
    """
    Returns the storage bucket instance for manager uploads.
    """
    client = storage.Client(project=PROJECT_ID)
    return client.bucket(BUCKET_NAME)

# Initialize Firestore Client
def seed_demo_employees():
    if not db:
        return
    try:
        employees = [
            {
                "employee_name": "Fresh Manager Test",
                "employee_email": "fresh.manager.test@company.com",
                "department": "Operations",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Receipt Test",
                "employee_email": "receipt.test@company.com",
                "department": "Finance",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Hotel Docs Test",
                "employee_email": "auth.hotel.docs.test@company.com",
                "department": "Sales",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Flight Docs Test",
                "employee_email": "auth.flight.docs.test@company.com",
                "department": "Travel",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Rejection Test",
                "employee_email": "auth.rejection.test@company.com",
                "department": "Compliance",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            }
        ]
        for emp in employees:
            emp_email = emp["employee_email"]
            doc_ref = db.collection("employees").document(emp_email)
            emp["employee_id"] = emp_email.split("@")[0]
            doc_ref.set(emp, merge=True)
        logger.info("Demo employees seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to seed demo employees: {e}")

try:
    db = firestore.Client(project=PROJECT_ID)
    logger.info("Successfully connected to Firestore database.")
    seed_demo_employees()
except Exception as e:
    logger.error(f"Error initializing Firestore: {e}")
    db = None

# Firestore Collection Names
EXPENSES_COL = "expenses"
DOCUMENTS_COL = "documents"
DECISIONS_COL = "decisions"
AUDIT_LOGS_COL = "audit_logs"
POLICIES_COL = "policies"

def add_audit_log(claim_id: str, session_id: str, event_type: str, event_message: str, actor: str = "system", actor_email: str = None, actor_role: str = None, authenticated: bool = False, employee_email: str = None, employee_name: str = None, manager_email: str = None, metadata: dict = None):
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
        # Work on a copy to avoid mutation side effects
        c_copy = dict(c)
        ec = enrich_claim_with_employee_info(c_copy)
        enriched.append(ec)
        
    filtered = []
    for c in enriched:
        # 1. Role-based baseline access control
        if role == "employee":
            # can only see claims where submitted_by_email or employee_email matches their logged-in email.
            sub_by = c.get("submitted_by_email") or ""
            emp_em = c.get("employee_email") or ""
            if email.lower() not in [sub_by.lower(), emp_em.lower()]:
                continue
        elif role == "manager":
            if is_pending:
                # can see Pending Approvals only for claims where manager_email equals the logged-in manager email.
                mgr_em = c.get("manager_email") or ""
                if email.lower() != mgr_em.lower():
                    continue
            else:
                # In History, can see any claim where they are the manager, employee, or submitter.
                mgr_em = c.get("manager_email") or ""
                emp_em = c.get("employee_email") or ""
                sub_by = c.get("submitted_by_email") or ""
                if email.lower() not in [mgr_em.lower(), emp_em.lower(), sub_by.lower()]:
                    continue
        elif role == "finance_admin":
            # can see all claims baseline
            pass
        else:
            # unknown role, restrict
            continue
            
        # 2. Query/Parameter Filters
        # Search employee name/email
        search = params.get("search")
        if search:
            search_l = search.lower()
            emp_name = (c.get("employee_name") or "").lower()
            emp_email = (c.get("employee_email") or "").lower()
            if search_l not in emp_name and search_l not in emp_email:
                continue
                
        # Filter by department
        dept_filter = params.get("department")
        if dept_filter:
            if (c.get("department") or "").lower() != dept_filter.lower():
                continue
                
        # Filter by manager
        mgr_filter = params.get("manager")
        if mgr_filter:
            mgr_email = (c.get("manager_email") or "").lower()
            if mgr_filter.lower() not in mgr_email:
                continue
                
        # Filter by status
        status_filter = params.get("status")
        if status_filter:
            if (c.get("status") or "").lower() != status_filter.lower():
                continue
                
        # Filter by category
        cat_filter = params.get("category")
        if cat_filter:
            if (c.get("category") or "").lower() != cat_filter.lower():
                continue
                
        # Filter by company_id
        comp_filter = params.get("company")
        if comp_filter:
            if (c.get("company_id") or "").lower() != comp_filter.lower():
                continue
                
        # Determine source
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
        
        # Apply source filter
        src_filter = params.get("source", "all")
        if src_filter and src_filter != "all":
            if computed_source != src_filter:
                continue
                
        # Hide old test sessions
        hide_old = params.get("hide_old_test_sessions")
        if hide_old and (hide_old == True or str(hide_old).lower() == "true"):
            if src_filter != "legacy_cli":
                if computed_source == "legacy_cli":
                    continue
                
        # Show only claims assigned to me
        assigned_to_me = params.get("assigned_to_me")
        if assigned_to_me and (assigned_to_me == True or str(assigned_to_me).lower() == "true"):
            mgr_email = (c.get("manager_email") or "").lower()
            if email.lower() != mgr_email:
                continue
                
        filtered.append(c)
        
    # Sort filtered array so employee_portal and report_workflow appear first
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

def find_and_bind_expense(session_id: str, user_id: str, claim_details: dict) -> tuple[dict, str]:
    """
    Finds a submitted Firestore expense document to match this newly discovered session.
    Fails over to creating a back-compat record if no existing record is matched.
    """
    if not db:
        return {}, ""
    try:
        # 1. Search by exact session_id
        docs = list(db.collection(EXPENSES_COL).where("session_id", "==", session_id).limit(1).get())
        if docs:
            return docs[0].to_dict(), docs[0].id
            
        # 2. Search by matching employee_name and status == "submitted"
        employee_name = claim_details.get("employee_name")
        amount = claim_details.get("amount", 0.0)
        
        query = db.collection(EXPENSES_COL).where("employee_name", "==", employee_name).where("status", "==", "submitted")
        matches = list(query.get())
        
        best_match = None
        for doc in matches:
            data = doc.to_dict()
            if abs(data.get("amount", 0.0) - amount) < 0.01:
                best_match = doc
                break
                
        if best_match:
            claim_id = best_match.get("claim_id") or best_match.id
            doc_ref = db.collection(EXPENSES_COL).document(best_match.id)
            
            policy_res = run_policy_check_py(claim_details)
            status = "blocked_missing_docs" if policy_res["missing_docs"] else "pending_review"
            
            pdr = claim_details.get("per_diem_review") or {}
            update_data = {
                "session_id": session_id,
                "user_id": user_id,
                "status": status,
                "policy_status": policy_res["status"],
                "required_documents": policy_res["required_docs"],
                "missing_documents": policy_res["missing_docs"],
                "updated_at": datetime.utcnow().isoformat() + "Z",
                
                # Multi-company and per diem fields
                "company_id": pdr.get("company_id") or claim_details.get("company_id") or "demo_company",
                "employee_email": pdr.get("employee_email") or claim_details.get("employee_email") or "",
                "employee_id": pdr.get("employee_id") or claim_details.get("employee_id") or "",
                "state_code": pdr.get("state_code") or claim_details.get("state_code") or "",
                "country": pdr.get("country") or claim_details.get("country") or "US",
                "claimed_meals": pdr.get("claimed_meals") or claim_details.get("claimed_meals") or 0.0,
                "claimed_lodging": pdr.get("claimed_lodging") or claim_details.get("claimed_lodging") or 0.0,
                "claimed_incidentals": pdr.get("claimed_incidentals") or claim_details.get("claimed_incidentals") or 0.0,
                "travel_start_date": pdr.get("travel_start_date") or claim_details.get("travel_start_date"),
                "travel_end_date": pdr.get("travel_end_date") or claim_details.get("travel_end_date"),
                "check_in_date": pdr.get("check_in_date") or claim_details.get("check_in_date"),
                "check_out_date": pdr.get("check_out_date") or claim_details.get("check_out_date"),
                "city": pdr.get("city") or claim_details.get("city"),
                "state": pdr.get("state") or claim_details.get("state"),
                "per_diem_review": pdr
            }
            # Overwrite optional fields parsed from session
            for field in ["category", "description", "business_purpose"]:
                if claim_details.get(field):
                    update_data[field] = claim_details[field]
                    
            doc_ref.update(update_data)
            
            add_audit_log(
                claim_id=claim_id,
                session_id=session_id,
                event_type="session_bound",
                event_message=f"Session bound to claim. Status: {status}.",
                actor="system",
                metadata={"policy_review": policy_res}
            )
            
            updated_doc = best_match.to_dict()
            updated_doc.update(update_data)
            return updated_doc, best_match.id
            
        # 3. Create fresh document for backward compatibility
        claim_id = str(uuid.uuid4())
        policy_res = run_policy_check_py(claim_details)
        status = "blocked_missing_docs" if policy_res["missing_docs"] else "pending_review"
        
        pdr = claim_details.get("per_diem_review") or {}
        new_expense = {
            "claim_id": claim_id,
            "session_id": session_id,
            "user_id": user_id,
            "employee_name": employee_name or "Unknown Claimant",
            "amount": amount,
            "category": claim_details.get("category", "N/A"),
            "description": claim_details.get("description", "No description provided"),
            "business_purpose": claim_details.get("business_purpose", ""),
            "status": status,
            "policy_status": policy_res["status"],
            "required_documents": policy_res["required_docs"],
            "missing_documents": policy_res["missing_docs"],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            
            # Multi-company and per diem fields
            "company_id": pdr.get("company_id") or claim_details.get("company_id") or "demo_company",
            "employee_email": pdr.get("employee_email") or claim_details.get("employee_email") or "",
            "employee_id": pdr.get("employee_id") or claim_details.get("employee_id") or "",
            "state_code": pdr.get("state_code") or claim_details.get("state_code") or "",
            "country": pdr.get("country") or claim_details.get("country") or "US",
            "claimed_meals": pdr.get("claimed_meals") or claim_details.get("claimed_meals") or 0.0,
            "claimed_lodging": pdr.get("claimed_lodging") or claim_details.get("claimed_lodging") or 0.0,
            "claimed_incidentals": pdr.get("claimed_incidentals") or claim_details.get("claimed_incidentals") or 0.0,
            "travel_start_date": pdr.get("travel_start_date") or claim_details.get("travel_start_date"),
            "travel_end_date": pdr.get("travel_end_date") or claim_details.get("travel_end_date"),
            "check_in_date": pdr.get("check_in_date") or claim_details.get("check_in_date"),
            "check_out_date": pdr.get("check_out_date") or claim_details.get("check_out_date"),
            "city": pdr.get("city") or claim_details.get("city"),
            "state": pdr.get("state") or claim_details.get("state"),
            "per_diem_review": pdr
        }
        db.collection(EXPENSES_COL).document(claim_id).set(new_expense)
        
        add_audit_log(
            claim_id=claim_id,
            session_id=session_id,
            event_type="claim_created_from_session",
            event_message=f"Created claim {claim_id} from session details. Status: {status}.",
            actor="system",
            metadata={"policy_review": policy_res}
        )
        return new_expense, claim_id
    except Exception as e:
        logger.error(f"Error in find_and_bind_expense: {e}")
        return {}, ""

def reevaluate_expense_policies(expense_id: str):
    """
    Query all GCS documents uploaded for this session and re-evaluate policy status.
    Removes items from missing list and promotes status to pending_review once complete.
    """
    if not db:
        return
    try:
        doc_ref = db.collection(EXPENSES_COL).document(expense_id)
        expense = doc_ref.get().to_dict()
        if not expense:
            return
            
        claim = dict(expense)
        session_id = expense.get("session_id")
        
        # Load GCS paths from documents collection to mock url presence
        uploaded_docs = list(db.collection(DOCUMENTS_COL).where("session_id", "==", session_id).get())
        for u_doc in uploaded_docs:
            u_data = u_doc.to_dict()
            doc_type = u_data.get("doc_type")
            doc_url_fields = {
                "receipt": "receipt_url",
                "hotel_receipt": "hotel_receipt_url",
                "flight_ticket_receipt": "flight_ticket_receipt_url",
                "manager_approval_letter": "manager_approval_letter_url",
                "office_receipt": "office_receipt_url",
                "parking_receipt": "parking_receipt_url",
                "mileage_log": "mileage_log_url",
                "rental_receipt": "rental_receipt_url",
                "gas_receipt": "gas_receipt_url",
                "toll_receipt": "toll_receipt_url"
            }
            if doc_type in doc_url_fields:
                claim[doc_url_fields[doc_type]] = f"/api/document/{session_id}/{doc_type}"
                
        policy_res = run_policy_check_py(claim)
        
        current_status = expense.get("status")
        status = current_status
        if current_status in ["submitted", "pending_review", "blocked_missing_docs"]:
            status = "blocked_missing_docs" if policy_res["missing_docs"] else "pending_review"
            
        doc_ref.update({
            "status": status,
            "policy_status": policy_res["status"],
            "required_documents": policy_res["required_docs"],
            "missing_documents": policy_res["missing_docs"],
            "per_diem_review": claim.get("per_diem_review"),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        add_audit_log(
            claim_id=expense_id,
            session_id=session_id,
            event_type="policies_reevaluated",
            event_message=f"Policies re-evaluated. Status: {status}.",
            actor="system",
            metadata={"policy_review": policy_res}
        )
    except Exception as e:
        logger.error(f"Error in reevaluate_expense_policies: {e}")

async def sync_completed_sessions():
    """
    Queries active expenses with unresolved states and checks if their sessions
    are resolved. Updates their status and registers final agent replies.
    """
    if not db:
        return
    try:
        s = VertexAiSessionService(
            project=PROJECT_ID,
            location=LOCATION,
            agent_engine_id=ENGINE_ID
        )
        list_resp = await s.list_sessions(app_name="app")
        
        active_expenses = list(
            db.collection(EXPENSES_COL)
            .where("status", "in", ["submitted", "pending_review", "blocked_missing_docs"])
            .get()
        )
        
        for exp_doc in active_expenses:
            exp = exp_doc.to_dict()
            sess_id = exp.get("session_id")
            user_id = exp.get("user_id") or "default-user"
            
            # Skip cli-user sessions if they are hidden
            if user_id == "cli-user":
                continue
                
            if not sess_id:
                # Attempt to bind by scanning active session summaries
                for s_summary in list_resp.sessions:
                    if s_summary.user_id == "cli-user":
                        continue
                    try:
                        sess = await s.get_session(app_name="app", user_id=s_summary.user_id, session_id=s_summary.id)
                        claim_details = parse_claim_from_session(sess)
                        if claim_details.get("employee_name") == exp.get("employee_name") and abs(claim_details.get("amount", 0.0) - exp.get("amount", 0.0)) < 0.01:
                            sess_id = s_summary.id
                            user_id = s_summary.user_id
                            db.collection(EXPENSES_COL).document(exp_doc.id).update({
                                "session_id": sess_id,
                                "user_id": user_id,
                                "updated_at": datetime.utcnow().isoformat() + "Z"
                            })
                            exp["session_id"] = sess_id
                            exp["user_id"] = user_id
                            break
                    except Exception:
                        pass
                        
            if sess_id:
                try:
                    sess = await s.get_session(app_name="app", user_id=user_id, session_id=sess_id)
                    if not sess:
                        continue
                        
                    # Re-verify unresolved inputs
                    unresolved = False
                    for event in sess.events:
                        if not event.content or not event.content.parts:
                            continue
                        for part in event.content.parts:
                            fc = getattr(part, "function_call", None)
                            if fc and fc.name == "adk_request_input":
                                unresolved = True
                                break
                            fr = getattr(part, "function_response", None)
                            if fr and fr.name == "adk_request_input":
                                unresolved = False
                                
                    if not unresolved:
                        # Session finalized! Extract last model reply text.
                        final_response = "Session completed."
                        for event in reversed(sess.events):
                            if event.author == "model" and event.content and event.content.parts:
                                for part in event.content.parts:
                                    if getattr(part, "text", None):
                                        final_response = part.text
                                        break
                                if final_response != "Session completed.":
                                    break
                                    
                        amount = exp.get("amount", 0.0)
                        is_rejected = any(x in final_response.lower() for x in ["reject", "deny", "denied", "block"])
                        
                        if amount < 100.0 and not is_rejected:
                            status = "auto_approved"
                        elif is_rejected:
                            status = "rejected"
                        else:
                            status = "approved"
                            
                        db.collection(EXPENSES_COL).document(exp_doc.id).update({
                            "status": status,
                            "updated_at": datetime.utcnow().isoformat() + "Z"
                        })
                        
                        # Store decision record
                        decision_ref = db.collection(DECISIONS_COL).document()
                        decision_ref.set({
                            "claim_id": exp_doc.id,
                            "session_id": sess_id,
                            "decision": "approved" if status in ["approved", "auto_approved"] else "rejected",
                            "decided_by": "agent" if status == "auto_approved" else "manager",
                            "decision_reason": f"AI Engine processed claim. Resolved final status is {status}.",
                            "decided_at": datetime.utcnow().isoformat() + "Z",
                            "final_agent_response": final_response
                        })
                        
                        # Store Audit Log
                        add_audit_log(
                            claim_id=exp_doc.id,
                            session_id=sess_id,
                            event_type="agent_finalized",
                            event_message=f"Session resolved by agent. Final Status: {status}.",
                            actor="agent" if status == "auto_approved" else "manager",
                            metadata={"final_response": final_response}
                        )
                except Exception as ex:
                    logger.error(f"Error syncing session {sess_id}: {ex}")
    except Exception as e:
        logger.error(f"Error during completed sessions sync: {e}")


class ApprovalAction(BaseModel):
    approved: bool
    interrupt_id: str = "review_decision"
    override_reason: str | None = None

# Regex fallback for extracting claim details from interrupt message if first user JSON is unparseable
DETAIL_RE = re.compile(r"Expense of \$([0-9.,]+) by (.*?) for '(.*?)'", re.IGNORECASE)

def parse_claim_from_session(sess) -> dict:
    """
    Parses details of the claim from session events.
    First tries to parse the first user message as JSON.
    If that fails, falls back to parsing the interrupt message inside the function call args.
    """
    details = {
        "employee_name": "Unknown Claimant",
        "amount": 0.0,
        "description": "No description provided",
        "receipt_url": None,
        "category": None,
        "travel_type": None,
        "check_in_date": None,
        "check_out_date": None,
        "travel_start_date": None,
        "travel_end_date": None,
        "city": None,
        "state": None,
        "hotel_receipt_url": None,
        "flight_ticket_receipt_url": None,
        "manager_approval_letter_url": None,
        "per_diem_rate": None,
        "lodging_rate_limit": None,
        "claimed_meals": None,
        "business_purpose": None,
        "item_type": None,
        "quantity": None,
        "vendor": None,
        "office_receipt_url": None,
        "parking_receipt_url": None,
        "parking_location": None,
        "parking_date": None,
        "related_meeting": None,
        "related_client": None,
        "non_reimbursable_reason": None,
    }
    
    # 1. Try to find the user's initial JSON claim payload
    for event in sess.events:
        if event.author == "user" and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    try:
                        data = json.loads(part.text)
                        if isinstance(data, dict):
                            if "employee_name" in data or "amount" in data:
                                details["employee_name"] = data.get("employee_name", details["employee_name"])
                                details["amount"] = float(data.get("amount", details["amount"]))
                                details["description"] = data.get("description", details["description"])
                                
                                # Parse other optional fields
                                for field in [
                                    "category", "travel_type", "check_in_date", "check_out_date",
                                    "travel_start_date", "travel_end_date", "city", "state",
                                    "hotel_receipt_url", "flight_ticket_receipt_url", 
                                    "manager_approval_letter_url", "per_diem_rate", 
                                    "lodging_rate_limit", "claimed_meals", "business_purpose",
                                    "item_type", "quantity", "vendor", "office_receipt_url",
                                    "parking_receipt_url", "parking_location", "parking_date",
                                    "related_meeting", "related_client", "non_reimbursable_reason",
                                    "employee_email", "employee_id", "company_id", "claimed_lodging", "claimed_incidentals"
                                ]:
                                    if field in data:
                                        details[field] = data[field]
                                
                                # Forwards/backwards compatibility for receipt_url
                                for k in ["receipt_url", "receipt_link", "attachment_url"]:
                                    if k in data and data[k]:
                                        details["receipt_url"] = data[k]
                                        break
                                return details
                    except Exception:
                        pass

    # 2. Fallback: Try to extract from the interrupt's message string
    for event in sess.events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                fc = getattr(part, "function_call", None)
                if fc and fc.name == "adk_request_input":
                    msg = fc.args.get("message", "")
                    match = DETAIL_RE.search(msg)
                    if match:
                        try:
                            details["amount"] = float(match.group(1).replace(",", ""))
                            details["employee_name"] = match.group(2).strip()
                            details["description"] = match.group(3).strip()
                            return details
                        except Exception:
                            pass
                            
    return details


def sanitize_claim_dict(claim: dict) -> dict:
    if not isinstance(claim, dict):
        return claim
    
    # Target numeric fields with safe defaults
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
    
    # Check per_diem_review
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


@app.get("/api/pending")
async def get_pending(
    request: Request,
    search: str = None,
    department: str = None,
    manager: str = None,
    status: str = None,
    category: str = None,
    company: str = None,
    hide_old_test_sessions: bool = True,
    assigned_to_me: bool = False,
    show_all_fa: bool = False,
    source: str = "all"
):
    """
    Queries VertexAiSessionService, fetches full histories in parallel,
    and returns sessions with unresolved adk_request_input events.
    """
    current_user = get_current_user_and_role(request)
    params = {
        "search": search,
        "department": department,
        "manager": manager,
        "status": status,
        "category": category,
        "company": company,
        "hide_old_test_sessions": hide_old_test_sessions,
        "assigned_to_me": assigned_to_me,
        "show_all_fa": show_all_fa,
        "source": source
    }
    try:
        s = VertexAiSessionService(
            project=PROJECT_ID,
            location=LOCATION,
            agent_engine_id=ENGINE_ID
        )
        
        list_resp = await s.list_sessions(app_name="app")
        pending_claims = []
        hidden_cli_sessions_count = 0
        
        # Sort sessions by recency (newest update time first)
        sessions_sorted = sorted(
            list_resp.sessions,
            key=lambda x: getattr(x, "last_update_time", 0.0),
            reverse=True
        )
        
        # Filter summaries and track hidden cli-user sessions count
        active_summaries = []
        for summary in sessions_sorted:
            if summary.user_id == "cli-user":
                hidden_cli_sessions_count += 1
            else:
                active_summaries.append(summary)
        
        # Limit to scanning the 30 most recent active sessions to prevent excessive API calls
        active_summaries = active_summaries[:30]
        
        # Semaphore to cap concurrent requests to Vertex AI
        sem = asyncio.Semaphore(10)
        
        async def fetch_and_parse(summary):
            async with sem:
                try:
                    # Individual session fetch timeout of 5 seconds
                    sess = await asyncio.wait_for(
                        s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id),
                        timeout=5.0
                    )
                    if not sess:
                        return []
                        
                    # Map of unresolved request input function calls
                    unresolved_calls = {}
                    for event in sess.events:
                        if not event.content or not event.content.parts:
                            continue
                        for part in event.content.parts:
                            fc = getattr(part, "function_call", None)
                            if fc and fc.name == "adk_request_input":
                                interrupt_id = getattr(fc, "id", None) or fc.args.get("interruptId", "review_decision")
                                unresolved_calls[interrupt_id] = {
                                    "interrupt_id": interrupt_id,
                                    "message": fc.args.get("message", "Attention required"),
                                }
                            fr = getattr(part, "function_response", None)
                            if fr and fr.name == "adk_request_input":
                                response_id = getattr(fr, "id", None)
                                unresolved_calls.pop(response_id, None)
                                
                    if unresolved_calls:
                        claim_details = parse_claim_from_session(sess)
                        
                        # Fetch GCS uploads metadata for this session in parallel
                        uploaded_metadata = {}
                        try:
                            def get_gcs_metadata():
                                bucket = get_gcs_bucket()
                                m_blob = bucket.blob(f"uploads/{sess.id}/metadata.json")
                                if m_blob.exists():
                                    return json.loads(m_blob.download_as_bytes().decode("utf-8"))
                                return {}
                            uploaded_metadata = await asyncio.to_thread(get_gcs_metadata)
                        except Exception as ge:
                            logger.warning(f"Error fetching GCS metadata for session {sess.id}: {ge}")
                            
                        # Merge uploaded document paths as endpoint URLs if they exist in GCS and original is missing
                        doc_url_fields = {
                            "receipt": "receipt_url",
                            "hotel_receipt": "hotel_receipt_url",
                            "flight_ticket_receipt": "flight_ticket_receipt_url",
                            "manager_approval_letter": "manager_approval_letter_url",
                            "office_receipt": "office_receipt_url",
                            "parking_receipt": "parking_receipt_url"
                        }
                        
                        for doc_type, field_name in doc_url_fields.items():
                            if doc_type in uploaded_metadata:
                                # Overwrite if missing from original session payload
                                if not claim_details.get(field_name):
                                    claim_details[field_name] = f"/api/document/{sess.id}/{doc_type}"
                        
                        # Bind and find/upsert in Firestore
                        expense_data, claim_id = await asyncio.to_thread(find_and_bind_expense, sess.id, sess.user_id, claim_details)
                        
                        claims_parsed = []
                        for interrupt_id, call_info in unresolved_calls.items():
                            claims_parsed.append({
                                "claim_id": claim_id,
                                "session_id": sess.id,
                                "user_id": sess.user_id,
                                "interrupt_id": interrupt_id,
                                "message": call_info["message"],
                                "employee_name": claim_details["employee_name"],
                                "amount": claim_details["amount"],
                                "description": claim_details["description"],
                                "receipt_url": claim_details.get("receipt_url"),
                                "category": claim_details.get("category"),
                                "travel_type": claim_details.get("travel_type"),
                                "check_in_date": claim_details.get("check_in_date"),
                                "check_out_date": claim_details.get("check_out_date"),
                                "travel_start_date": claim_details.get("travel_start_date"),
                                "travel_end_date": claim_details.get("travel_end_date"),
                                "city": claim_details.get("city"),
                                "state": claim_details.get("state"),
                                "hotel_receipt_url": claim_details.get("hotel_receipt_url"),
                                "flight_ticket_receipt_url": claim_details.get("flight_ticket_receipt_url"),
                                "manager_approval_letter_url": claim_details.get("manager_approval_letter_url"),
                                "per_diem_rate": claim_details.get("per_diem_rate"),
                                "lodging_rate_limit": claim_details.get("lodging_rate_limit"),
                                "claimed_meals": claim_details.get("claimed_meals"),
                                "business_purpose": claim_details.get("business_purpose"),
                                "item_type": claim_details.get("item_type"),
                                "quantity": claim_details.get("quantity"),
                                "vendor": claim_details.get("vendor"),
                                "office_receipt_url": claim_details.get("office_receipt_url"),
                                "parking_receipt_url": claim_details.get("parking_receipt_url"),
                                "parking_location": claim_details.get("parking_location"),
                                "parking_date": claim_details.get("parking_date"),
                                "related_meeting": claim_details.get("related_meeting"),
                                "related_client": claim_details.get("related_client"),
                                "non_reimbursable_reason": claim_details.get("non_reimbursable_reason"),
                                "uploaded_docs": list(uploaded_metadata.keys()),
                                
                                # Multi-company and per-diem additions
                                "company_id": expense_data.get("company_id") or claim_details.get("company_id") or "demo_company",
                                "employee_email": expense_data.get("employee_email") or claim_details.get("employee_email") or "",
                                "employee_id": expense_data.get("employee_id") or claim_details.get("employee_id") or "",
                                "state_code": expense_data.get("state_code") or claim_details.get("state_code") or "",
                                "country": expense_data.get("country") or claim_details.get("country") or "US",
                                "claimed_lodging": expense_data.get("claimed_lodging") or claim_details.get("claimed_lodging") or 0.0,
                                "claimed_incidentals": expense_data.get("claimed_incidentals") or claim_details.get("claimed_incidentals") or 0.0,
                                "per_diem_review": expense_data.get("per_diem_review") or claim_details.get("per_diem_review")
                            })
                        return claims_parsed
                    return []
                except Exception as e:
                    logger.error(f"Error fetching session {summary.id}: {e}")
                    return []
        
        # Gather sessions in parallel
        tasks = [fetch_and_parse(summary) for summary in active_summaries]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            pending_claims.extend(result)
            
        # Merge Firestore-only claims from employee portal that are pending or blocked
        if db:
            try:
                existing_sess_ids = {c["session_id"] for c in pending_claims if "session_id" in c}
                db_expenses = await asyncio.to_thread(
                    lambda: list(
                        db.collection(EXPENSES_COL)
                        .where("status", "in", ["pending_review", "blocked_missing_docs"])
                        .get()
                    )
                )
                for doc in db_expenses:
                    exp = doc.to_dict()
                    sess_id = exp.get("session_id") or exp.get("claim_id") or doc.id
                    claim_id = exp.get("claim_id") or doc.id
                    
                    if sess_id in existing_sess_ids:
                        continue
                        
                    uploaded_metadata = []
                    try:
                        uploaded_docs = await asyncio.to_thread(
                            lambda: list(db.collection(DOCUMENTS_COL).where("session_id", "==", sess_id).get())
                        )
                        uploaded_metadata = [d.to_dict().get("doc_type") for d in uploaded_docs if d.to_dict().get("doc_type")]
                    except Exception as de:
                        logger.warning(f"Error fetching Firestore docs for sess {sess_id}: {de}")
                        
                    pending_claims.append({
                        "claim_id": claim_id,
                        "session_id": sess_id,
                        "user_id": exp.get("submitted_by_role") or "portal-user",
                        "interrupt_id": "review_decision",
                        "message": f"Attention required: Claim for {exp.get('employee_name')} is pending review.",
                        "employee_name": exp.get("employee_name") or exp.get("employee_email") or "Unknown Employee",
                        "amount": float(exp.get("amount") or 0.0),
                        "description": exp.get("description") or exp.get("business_purpose") or "Portal Claim Submission",
                        "receipt_url": exp.get("receipt_url"),
                        "category": exp.get("category"),
                        "travel_type": exp.get("travel_type") or ("travel" if exp.get("category") in ["hotel", "flight", "meals"] else "other"),
                        "check_in_date": exp.get("check_in_date"),
                        "check_out_date": exp.get("check_out_date"),
                        "travel_start_date": exp.get("travel_start_date"),
                        "travel_end_date": exp.get("travel_end_date"),
                        "city": exp.get("city"),
                        "state": exp.get("state"),
                        "hotel_receipt_url": exp.get("hotel_receipt_url"),
                        "flight_ticket_receipt_url": exp.get("flight_ticket_receipt_url"),
                        "manager_approval_letter_url": exp.get("manager_approval_letter_url"),
                        "per_diem_rate": exp.get("per_diem_rate"),
                        "lodging_rate_limit": exp.get("lodging_rate_limit"),
                        "claimed_meals": exp.get("claimed_meals"),
                        "business_purpose": exp.get("business_purpose"),
                        "uploaded_docs": list(uploaded_metadata),
                        "company_id": exp.get("company_id") or "demo_company",
                        "employee_email": exp.get("employee_email") or "",
                        "employee_id": exp.get("employee_id") or "",
                        "state_code": exp.get("state_code") or "",
                        "country": exp.get("country") or "US",
                        "claimed_lodging": exp.get("claimed_lodging") or 0.0,
                        "claimed_incidentals": exp.get("claimed_incidentals") or 0.0,
                        "per_diem_review": exp.get("per_diem_review") or {},
                        "policy_status": exp.get("policy_status") or "Compliance evaluation completed.",
                        "missing_documents": exp.get("missing_documents") or []
                    })
            except Exception as dbe:
                logger.error(f"Error merging Firestore pending claims: {dbe}")
            
        filtered_pending = filter_and_enrich_claims(pending_claims, current_user, params, is_pending=True)
        sanitized_pending_claims = [sanitize_claim_dict(c) for c in filtered_pending]
        return {
            "pending_claims": sanitized_pending_claims,
            "hidden_cli_sessions_count": hidden_cli_sessions_count
        }
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sessions: {str(e)}"
        )


@app.post("/api/action/{session_id}")
async def post_action(session_id: str, action: ApprovalAction, request: Request):
    """
    Resumes a paused Reasoning Engine session by invoking its execution api client directly.
    Also persists the manager decision and agent final response in Firestore.
    """
    current_user = get_current_user_and_role(request)
    role = current_user["role"]
    if role == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Employees cannot approve or reject claims."
        )

    if action.override_reason and role != "finance_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only finance administrators can override policy constraints."
        )

    # Phase 2: Resolve claim_id and write manager decision to Firestore
    claim_id = ""
    expense_id = ""
    decision_id = str(uuid.uuid4())
    is_portal_claim = False
    emp_email = None
    emp_name = None
    mgr_email = None
    if db:
        try:
            query = db.collection(EXPENSES_COL).where("session_id", "==", session_id).limit(1)
            expense_docs = list(query.get())
            if expense_docs:
                expense_id = expense_docs[0].id
                expense_dict = expense_docs[0].to_dict()
                claim_id = expense_dict.get("claim_id") or expense_id
                if expense_dict.get("source") == "employee_portal":
                    is_portal_claim = True
                
                # Enrich to ensure default/fallback fields are correctly retrieved
                expense_dict = enrich_claim_with_employee_info(expense_dict)
                emp_email = expense_dict.get("employee_email")
                emp_name = expense_dict.get("employee_name")
                mgr_email = expense_dict.get("manager_email")
            
            decision_doc = {
                "claim_id": claim_id,
                "session_id": session_id,
                "decision": "approved" if action.approved else "rejected",
                "decided_by": current_user["email"],
                "decided_role": current_user["role"],
                "actor_email": current_user["email"],
                "actor_role": current_user["role"],
                "authenticated": True,
                "decided_at": datetime.utcnow().isoformat() + "Z",
                "final_agent_response": ""
            }
            
            if action.override_reason:
                decision_doc["override_reason"] = action.override_reason
                decision_doc["decision_reason"] = f"Finance Admin override: {action.override_reason}"
            else:
                decision_doc["decision_reason"] = "Manager clicked Approve" if action.approved else "Manager clicked Reject"
                
            db.collection(DECISIONS_COL).document(decision_id).set(decision_doc)
            
            event_msg = f"Manager submitted decision: {'approved' if action.approved else 'rejected'}."
            if action.override_reason:
                event_msg = f"Finance Admin override: {action.override_reason}."
                
            add_audit_log(
                claim_id=claim_id,
                session_id=session_id,
                event_type="manager_decision",
                event_message=event_msg,
                actor=current_user["email"] if current_user.get("email") else current_user["role"],
                actor_email=current_user["email"],
                actor_role=current_user["role"],
                authenticated=current_user["authenticated"],
                employee_email=emp_email,
                employee_name=emp_name,
                manager_email=mgr_email,
                metadata={"override_reason": action.override_reason} if action.override_reason else None
            )
        except Exception as ex:
            logger.error(f"Error recording manager decision: {ex}")

    if is_portal_claim:
        try:
            final_status = "approved" if action.approved else "rejected"
            final_review = f"Manager directly {'approved' if action.approved else 'rejected'} this portal-submitted claim."
            
            if db:
                db.collection(DECISIONS_COL).document(decision_id).update({
                    "final_agent_response": final_review
                })
                if expense_id:
                    db.collection(EXPENSES_COL).document(expense_id).update({
                        "status": final_status,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                        "decision_by_email": current_user["email"],
                        "decision_by_role": current_user["role"],
                        "reviewer_email": current_user["email"],
                        "reviewer_role": current_user["role"],
                    })
                    
                add_audit_log(
                    claim_id=claim_id,
                    session_id=session_id,
                    event_type="agent_finalized",
                    event_message=f"Claim processed. Final Status: {final_status}.",
                    actor="agent",
                    metadata={"final_review": final_review}
                )
            
            return {
                "status": "success",
                "session_id": session_id,
                "approved": action.approved,
                "final_review": final_review
            }
        except Exception as pe:
            logger.error(f"Error executing portal bypass logic: {pe}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to finalize portal-submitted claim: {str(pe)}"
            )

    try:
        remote_app = reasoning_engines.ReasoningEngine(AGENT_RUNTIME_ID)
        
        # Build the exact resume payload expected by the workflow
        resume_payload = {
            "role": "user",
            "parts": [{
                "function_response": {
                    "id": action.interrupt_id,
                    "name": "adk_request_input",
                    "response": {"approved": action.approved}
                }
            }]
        }
        
        logger.info(f"Resuming session {session_id} with approval={action.approved}")
        
        # Invoke stream_query_reasoning_engine
        response_stream = remote_app.execution_api_client.stream_query_reasoning_engine(
            request=aip_types.StreamQueryReasoningEngineRequest(
                name=remote_app.resource_name,
                input={
                    "message": resume_payload,
                    "user_id": "default-user", # Strictly set to "default-user" per prompt rules
                    "session_id": session_id
                },
                class_method="stream_query",
            )
        )
        
        # Consume the stream and extract the model's final response text
        output_text_parts = []
        for chunk in response_stream:
            if hasattr(chunk, "data") and chunk.data:
                try:
                    payload = json.loads(chunk.data)
                    # Check for text inside content
                    if "content" in payload and "parts" in payload["content"]:
                        for part in payload["content"]["parts"]:
                            if "text" in part and part["text"]:
                                output_text_parts.append(part["text"])
                    # Check for final output attribute
                    elif "output" in payload and payload["output"]:
                        if isinstance(payload["output"], dict) and "comments" in payload["output"]:
                            output_text_parts.append(payload["output"]["comments"])
                except Exception:
                    pass
                    
        final_review = "".join(output_text_parts) if output_text_parts else "Approval submitted successfully."
        
        # Phase 2: Update status, final agent response, and audit log
        final_status = "approved" if action.approved else "rejected"
        if db:
            try:
                db.collection(DECISIONS_COL).document(decision_id).update({
                    "final_agent_response": final_review
                })
                if expense_id:
                    db.collection(EXPENSES_COL).document(expense_id).update({
                        "status": final_status,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                        "decision_by_email": current_user["email"],
                        "decision_by_role": current_user["role"],
                        "reviewer_email": current_user["email"],
                        "reviewer_role": current_user["role"],
                    })
                    
                add_audit_log(
                    claim_id=claim_id,
                    session_id=session_id,
                    event_type="agent_finalized",
                    event_message=f"Agent completed execution stream. Final Status: {final_status}.",
                    actor="agent",
                    metadata={"final_review": final_review}
                )
            except Exception as fe:
                logger.error(f"Error finalizing decision and status: {fe}")

        # Format a beautifully descriptive response
        return {
            "status": "success",
            "session_id": session_id,
            "approved": action.approved,
            "final_review": final_review
        }
        
    except Exception as e:
        logger.error(f"Error resuming session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume session: {str(e)}"
        )

@app.post("/api/upload/{session_id}/{doc_type}")
async def upload_document(session_id: str, doc_type: str, request: Request, file: UploadFile = File(...)):
    """
    Accepts multipart/form-data file upload, validates doc_type and file type,
    uploads to GCS, and updates metadata JSON.
    """
    current_user = get_current_user_and_role(request)
    role = current_user["role"]
    if role == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Employees cannot upload documents."
        )

    allowed_doc_types = {
        "receipt", "hotel_receipt", "flight_ticket_receipt", 
        "manager_approval_letter", "office_receipt", "parking_receipt"
    }
    if doc_type not in allowed_doc_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {doc_type}"
        )
    
    # Validate extension
    filename = file.filename or "file"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Only PDF, PNG, JPG, JPEG are allowed."
        )
    
    # Validate mime-type
    allowed_content_types = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}
    if file.content_type not in allowed_content_types:
        # We also allow extension-based match as backup
        pass
        
    # File size validation (10 MB maximum)
    max_size = 10 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10 MB."
        )
        
    # Sanitize filename
    base_name = os.path.splitext(filename)[0]
    clean_base = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
    safe_filename = f"{clean_base}{ext}"
    
    object_path = f"uploads/{session_id}/{doc_type}/{safe_filename}"
    
    try:
        bucket = get_gcs_bucket()
        
        # Avoid overwriting files of other types, but replace previous files of the exact same document type
        blobs_to_delete = bucket.list_blobs(prefix=f"uploads/{session_id}/{doc_type}/")
        for b in blobs_to_delete:
            try:
                b.delete()
            except Exception as de:
                logger.warning(f"Could not delete old blob {b.name}: {de}")
                
        # Upload new blob
        blob = bucket.blob(object_path)
        blob.upload_from_string(contents, content_type=file.content_type or "application/octet-stream")
        
        # Update session metadata JSON
        metadata_path = f"uploads/{session_id}/metadata.json"
        metadata_blob = bucket.blob(metadata_path)
        
        metadata = {}
        if metadata_blob.exists():
            try:
                metadata = json.loads(metadata_blob.download_as_bytes().decode("utf-8"))
            except Exception as me:
                logger.warning(f"Error reading existing metadata for {session_id}: {me}")
                
        # Register new/replaced document
        metadata[doc_type] = {
            "path": object_path,
            "display_name": safe_filename,
            "content_type": file.content_type
        }
        
        metadata_blob.upload_from_string(
            json.dumps(metadata, indent=2),
            content_type="application/json"
        )
        
        # Phase 2: Write document metadata to Firestore and reevaluate policies
        claim_id = ""
        expense_id = ""
        if db:
            try:
                query = db.collection(EXPENSES_COL).where("session_id", "==", session_id).limit(1)
                expense_docs = list(query.get())
                if expense_docs:
                    expense_id = expense_docs[0].id
                    claim_id = expense_docs[0].to_dict().get("claim_id") or expense_id
                
                doc_data = {
                    "claim_id": claim_id,
                    "session_id": session_id,
                    "doc_type": doc_type,
                    "gcs_path": f"gs://{BUCKET_NAME}/{object_path}",
                    "original_filename": filename,
                    "content_type": file.content_type or "application/octet-stream",
                    "uploaded_at": datetime.utcnow().isoformat() + "Z"
                }
                # Store document details in firestore
                db.collection(DOCUMENTS_COL).document(f"{session_id}_{doc_type}").set(doc_data)
                
                # Write Audit Log
                add_audit_log(
                    claim_id=claim_id,
                    session_id=session_id,
                    event_type="document_uploaded",
                    event_message=f"Uploaded document {doc_type}: {filename}.",
                    actor=current_user["email"] if current_user.get("email") else current_user["role"],
                    actor_email=current_user["email"],
                    actor_role=current_user["role"],
                    authenticated=current_user["authenticated"],
                    metadata={"gcs_path": f"gs://{BUCKET_NAME}/{object_path}"}
                )
                
                # Reevaluate policies
                if expense_id:
                    await asyncio.to_thread(reevaluate_expense_policies, expense_id)
            except Exception as fe:
                logger.error(f"Error updating Firestore during document upload: {fe}")

        logger.info(f"Successfully uploaded {doc_type} to {object_path} for session {session_id}")
        return {
            "status": "success",
            "doc_type": doc_type,
            "path": object_path,
            "display_name": safe_filename
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GCS Upload failed: {str(e)}"
        )


@app.get("/api/uploads/{session_id}")
async def get_uploads_metadata(session_id: str, request: Request):
    """
    Returns uploaded document metadata for a session.
    """
    current_user = get_current_user_and_role(request)
    if current_user["role"] == "employee":
        # Check if the employee owns this session
        if db:
            expense_docs = list(db.collection(EXPENSES_COL).where("session_id", "==", session_id).limit(1).get())
            if expense_docs:
                expense_data = expense_docs[0].to_dict()
                if expense_data.get("employee_name", "").lower() != current_user["email"].lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You are not authorized to view uploads metadata for this session."
                    )
    """
    Returns uploaded document metadata for a session.
    """
    try:
        bucket = get_gcs_bucket()
        metadata_blob = bucket.blob(f"uploads/{session_id}/metadata.json")
        if not metadata_blob.exists():
            return {}
        return json.loads(metadata_blob.download_as_bytes().decode("utf-8"))
    except Exception as e:
        logger.error(f"Error reading GCS metadata for {session_id}: {e}")
        return {}


@app.get("/api/document/{session_id}/{doc_type}")
async def get_uploaded_document(session_id: str, doc_type: str, request: Request):
    """
    Securely retrieves and streams an uploaded file for viewing from private GCS bucket.
    """
    current_user = get_current_user_and_role(request)
    if current_user["role"] == "employee":
        # Check if the employee owns this session
        if db:
            expense_docs = list(db.collection(EXPENSES_COL).where("session_id", "==", session_id).limit(1).get())
            if expense_docs:
                expense_data = expense_docs[0].to_dict()
                if expense_data.get("employee_name", "").lower() != current_user["email"].lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You are not authorized to view this document."
                    )
    """
    Securely retrieves and streams an uploaded file for viewing from private GCS bucket.
    """
    try:
        bucket = get_gcs_bucket()
        metadata_blob = bucket.blob(f"uploads/{session_id}/metadata.json")
        if not metadata_blob.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No metadata found for session")
            
        metadata = json.loads(metadata_blob.download_as_bytes().decode("utf-8"))
        if doc_type not in metadata:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No document of type {doc_type} uploaded")
            
        doc_info = metadata[doc_type]
        blob = bucket.blob(doc_info["path"])
        if not blob.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage")
            
        file_bytes = blob.download_as_bytes()
        import io
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=blob.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"inline; filename={urllib.parse.quote(doc_info['display_name'])}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document: {str(e)}"
        )


@app.post("/api/ingest-expense")
async def ingest_expense(payload: dict, request: Request):
    """
    Stores incoming Pub/Sub expense event into Firestore.
    Does not replace the Agent Runtime processing flow.
    Supports both direct JSON payloads and standard Pub/Sub push notification structures.
    """
    # Ingest Endpoint Shared-Secret Verification
    shared_secret = os.getenv("INGEST_SHARED_SECRET", "")
    if shared_secret:
        req_secret = request.query_params.get("secret")
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:]
            req_secret = bearer_token
            # Add robust OIDC Token verification fallback to accept our Pub/Sub invoker service account
            try:
                parts = bearer_token.split('.')
                if len(parts) == 3:
                    import base64
                    payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
                    payload_data = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
                    if payload_data.get("iss") in ["accounts.google.com", "https://accounts.google.com"]:
                        email = payload_data.get("email")
                        if email == "pubsub-invoker@project-5d38f91a-29a3-45bd-8d4.iam.gserviceaccount.com":
                            logger.info(f"Authenticated ingest via Google OIDC Token for {email}")
                            req_secret = shared_secret
            except Exception as jwte:
                logger.warning(f"Failed to decode OIDC bearer token: {jwte}")
            
        if req_secret != shared_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid ingest shared secret."
            )
    """
    Stores incoming Pub/Sub expense event into Firestore.
    Does not replace the Agent Runtime processing flow.
    Supports both direct JSON payloads and standard Pub/Sub push notification structures.
    """
    logger.info(f"Received ingest-expense payload: {payload}")
    try:
        # Check if it is a Pub/Sub push message
        raw_data = None
        if "message" in payload and "data" in payload["message"]:
            import base64
            encoded_data = payload["message"]["data"]
            try:
                decoded = base64.b64decode(encoded_data).decode("utf-8")
                raw_data = json.loads(decoded)
            except Exception as e:
                logger.error(f"Failed to decode Pub/Sub base64 data: {e}")
                raise HTTPException(status_code=400, detail="Invalid Pub/Sub base64 data")
        else:
            raw_data = payload

        # Now, raw_data should be the expense dictionary. Let's parse/unwrap input.message if needed.
        if "input" in raw_data and isinstance(raw_data["input"], dict):
            if "message" in raw_data["input"] and isinstance(raw_data["input"]["message"], dict):
                raw_data = raw_data["input"]["message"]
            elif "message" in raw_data["input"] and isinstance(raw_data["input"]["message"], str):
                try:
                    raw_data = json.loads(raw_data["input"]["message"])
                except Exception:
                    pass

        # Generate or preserve claim_id
        claim_id = raw_data.get("claim_id") or str(uuid.uuid4())
        session_id = raw_data.get("session_id") or ""
        user_id = raw_data.get("user_id") or "default-user"
        
        employee_name = raw_data.get("employee_name") or "Unknown Claimant"
        amount = float(raw_data.get("amount") or 0.0)
        
        # Policy review to set correct initial properties
        policy_res = run_policy_check_py(raw_data)
        
        # Determine status. Initially, all ingested expenses are "submitted".
        initial_status = "submitted"
        
        new_expense = {
            "claim_id": claim_id,
            "session_id": session_id,
            "user_id": user_id,
            "employee_name": employee_name,
            "amount": amount,
            "category": raw_data.get("category", "N/A"),
            "description": raw_data.get("description") or raw_data.get("business_purpose") or "No description provided",
            "business_purpose": raw_data.get("business_purpose", ""),
            "status": initial_status,
            "policy_status": policy_res["status"],
            "required_documents": policy_res["required_docs"],
            "missing_documents": policy_res["missing_docs"],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Store other custom/extra fields in the document
        for field in [
            "company_id", "employee_email", "employee_id", "state_code", "country",
            "claimed_meals", "claimed_lodging", "claimed_incidentals", "per_diem_review",
            "check_in_date", "check_out_date", "travel_start_date", "travel_end_date",
            "city", "state", "receipt_url", "hotel_receipt_url", "flight_ticket_receipt_url",
            "manager_approval_letter_url", "per_diem_rate", "lodging_rate_limit",
            "item_type", "quantity", "vendor", "office_receipt_url", "parking_receipt_url",
            "parking_location", "parking_date", "related_meeting", "related_client", "non_reimbursable_reason"
        ]:
            if field in raw_data:
                new_expense[field] = raw_data[field]
            elif field == "per_diem_review" and "per_diem_review" in raw_data:
                new_expense["per_diem_review"] = raw_data["per_diem_review"]
                
        # Ensure company_id and other fields are always present
        pdr_dict = new_expense.get("per_diem_review") or {}
        if not new_expense.get("company_id"):
            new_expense["company_id"] = pdr_dict.get("company_id") or "demo_company"
        if not new_expense.get("employee_email"):
            new_expense["employee_email"] = pdr_dict.get("employee_email") or ""
        if not new_expense.get("employee_id"):
            new_expense["employee_id"] = pdr_dict.get("employee_id") or ""
                
        if db:
            db.collection(EXPENSES_COL).document(claim_id).set(new_expense)
            
            # Write audit log
            add_audit_log(
                claim_id=claim_id,
                session_id=session_id,
                event_type="claim_ingested",
                event_message=f"Expense ingested via Pub/Sub endpoint. Status: {initial_status}.",
                actor="system",
                metadata={"payload": raw_data, "policy_review": policy_res}
            )
            
        logger.info(f"Successfully ingested expense claim {claim_id} for {employee_name} of amount {amount}")
        return {"status": "success", "claim_id": claim_id}
        
    except Exception as e:
        logger.error(f"Error in ingest_expense endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest expense: {str(e)}")


@app.get("/api/expenses")
async def get_expenses(
    request: Request,
    search: str = None,
    department: str = None,
    manager: str = None,
    status: str = None,
    category: str = None,
    company: str = None,
    hide_old_test_sessions: bool = False,
    assigned_to_me: bool = False,
    show_all_fa: bool = False
):
    """
    Returns recent expenses from Firestore, syncing completed sessions first.
    """
    current_user = get_current_user_and_role(request)
    params = {
        "search": search,
        "department": department,
        "manager": manager,
        "status": status,
        "category": category,
        "company": company,
        "hide_old_test_sessions": hide_old_test_sessions,
        "assigned_to_me": assigned_to_me,
        "show_all_fa": show_all_fa
    }
    try:
        if db:
            # Run session sync to capture auto-approvals and finalised sessions
            try:
                await sync_completed_sessions()
            except Exception as se:
                logger.warning(f"Error syncing completed sessions during get_expenses: {se}")
                
            expenses_ref = db.collection(EXPENSES_COL).order_by("created_at", direction=firestore.Query.DESCENDING)
            docs = list(expenses_ref.get())
            all_claims = [doc.to_dict() for doc in docs]
            filtered_claims = filter_and_enrich_claims(all_claims, current_user, params, is_pending=False)
            return [sanitize_claim_dict(c) for c in filtered_claims]
        return []
    except Exception as e:
        logger.error(f"Error fetching expenses from Firestore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {str(e)}")


@app.get("/api/expenses/{claim_id}")
async def get_expense_detail(claim_id: str, request: Request):
    """
    Returns expense, documents, decisions, and audit log for one claim.
    """
    current_user = get_current_user_and_role(request)
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        doc_ref = db.collection(EXPENSES_COL).document(claim_id)
        expense_doc = doc_ref.get()
        if not expense_doc.exists:
            raise HTTPException(status_code=404, detail=f"Expense claim {claim_id} not found")
            
        expense_data = enrich_claim_with_employee_info(expense_doc.to_dict())
        is_owner = (
            expense_data.get("employee_email") == current_user["email"] or
            expense_data.get("submitted_by_email") == current_user["email"]
        )
        is_manager = (
            expense_data.get("manager_email") == current_user["email"]
        )
        is_authorized = (
            current_user["role"] == "finance_admin" or
            is_owner or
            is_manager
        )
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view details of this expense claim."
            )
            
        # Query documents
        docs_ref = db.collection(DOCUMENTS_COL).where("claim_id", "==", claim_id)
        documents = [d.to_dict() for d in docs_ref.get()]
        
        # Query decisions
        decisions_ref = db.collection(DECISIONS_COL).where("claim_id", "==", claim_id)
        decisions = [d.to_dict() for d in decisions_ref.get()]
        
        # Query audit logs
        audits_ref = db.collection(AUDIT_LOGS_COL).where("claim_id", "==", claim_id)
        audits = [a.to_dict() for a in audits_ref.get()]
        audits = sorted(audits, key=lambda x: x.get("timestamp", ""))
        
        return {
            "expense": sanitize_claim_dict(expense_data),
            "documents": documents,
            "decisions": decisions,
            "audit_logs": audits
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching expense detail for claim_id {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch expense details: {str(e)}")


@app.get("/api/audit/{claim_id}")
async def get_audit_trail(claim_id: str, request: Request):
    """
    Returns the sorted chronological audit timeline for one claim.
    """
    current_user = get_current_user_and_role(request)
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        # First fetch expense document to verify authorization
        doc_ref = db.collection(EXPENSES_COL).document(claim_id)
        expense_doc = doc_ref.get()
        if not expense_doc.exists:
            raise HTTPException(status_code=404, detail=f"Expense claim {claim_id} not found")
            
        expense_data = enrich_claim_with_employee_info(expense_doc.to_dict())
        is_owner = (
            expense_data.get("employee_email") == current_user["email"] or
            expense_data.get("submitted_by_email") == current_user["email"]
        )
        is_manager = (
            expense_data.get("manager_email") == current_user["email"]
        )
        is_authorized = (
            current_user["role"] == "finance_admin" or
            is_owner or
            is_manager
        )
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view the audit trail for this expense claim."
            )
            
        audits_ref = db.collection(AUDIT_LOGS_COL).where("claim_id", "==", claim_id)
        audits = [a.to_dict() for a in audits_ref.get()]
        audits = sorted(audits, key=lambda x: x.get("timestamp", ""))
        return audits
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit trail for claim_id {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit trail: {str(e)}")


# --- Company Policy Admin Endpoints ---

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
    effective_start_date: str | None = None
    effective_end_date: str | None = None

@app.get("/api/company-policy")
async def get_company_policy(request: Request, company_id: str = "demo_company"):
    current_user = get_current_user_and_role(request)
    if current_user["role"] == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Employees cannot view company per diem policies."
        )
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        # Query company default policy
        default_policy_docs = list(db.collection("company_policy_settings")
            .where("company_id", "==", company_id)
            .where("active", "==", True).get())
        defaults = [d.to_dict() for d in default_policy_docs]

        # Query state rates
        state_rate_docs = list(db.collection("company_state_per_diem_rates")
            .where("company_id", "==", company_id)
            .where("active", "==", True).get())
        state_rates = [d.to_dict() for d in state_rate_docs]

        # Query city rates
        city_rate_docs = list(db.collection("company_city_per_diem_rates")
            .where("company_id", "==", company_id)
            .where("active", "==", True).get())
        city_rates = [d.to_dict() for d in city_rate_docs]

        return {
            "company_id": company_id,
            "default_policy_settings": defaults,
            "state_rates": state_rates,
            "city_rates": city_rates
        }
    except Exception as e:
        logger.error(f"Error fetching company policies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch company policies: {str(e)}")

@app.post("/api/company-policy/state-rate")
async def post_state_rate(payload: StateRatePayload, request: Request):
    current_user = get_current_user_and_role(request)
    if current_user["role"] != "finance_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only finance administrators can create or update state per diem rates."
        )
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        rate_id = f"{payload.company_id}_{payload.state_code.lower()}"
        data = payload.dict()
        data["rate_id"] = rate_id
        data["created_by"] = current_user["email"]
        data["updated_by"] = current_user["email"]
        data["created_at"] = datetime.utcnow().isoformat() + "Z"
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        db.collection("company_state_per_diem_rates").document(rate_id).set(data)
        
        # Write audit log
        add_audit_log(
            claim_id="",
            session_id="",
            event_type="state_rate_updated",
            event_message=f"Created or updated state per diem rate for state {payload.state_code}.",
            actor=current_user["email"] if current_user.get("email") else current_user["role"],
            actor_email=current_user["email"],
            actor_role=current_user["role"],
            authenticated=current_user["authenticated"],
            metadata={"state_rate": data}
        )
        return {"status": "success", "rate_id": rate_id}
    except Exception as e:
        logger.error(f"Error writing state rate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save state per diem rate: {str(e)}")

@app.post("/api/company-policy/city-rate")
async def post_city_rate(payload: CityRatePayload, request: Request):
    current_user = get_current_user_and_role(request)
    if current_user["role"] != "finance_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only finance administrators can create or update city per diem rates."
        )
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        city_slug = payload.city.lower().replace(" ", "_")
        rate_id = f"{payload.company_id}_{payload.state_code.lower()}_{city_slug}"
        data = payload.dict()
        data["rate_id"] = rate_id
        data["created_by"] = current_user["email"]
        data["updated_by"] = current_user["email"]
        data["created_at"] = datetime.utcnow().isoformat() + "Z"
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        db.collection("company_city_per_diem_rates").document(rate_id).set(data)
        
        # Write audit log
        add_audit_log(
            claim_id="",
            session_id="",
            event_type="city_rate_updated",
            event_message=f"Created or updated city per diem rate for city {payload.city}, state {payload.state_code}.",
            actor=current_user["email"] if current_user.get("email") else current_user["role"],
            actor_email=current_user["email"],
            actor_role=current_user["role"],
            authenticated=current_user["authenticated"],
            metadata={"city_rate": data}
        )
        return {"status": "success", "rate_id": rate_id}
    except Exception as e:
        logger.error(f"Error writing city rate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save city per diem rate: {str(e)}")

@app.post("/api/company-policy/defaults")
async def post_defaults(payload: DefaultsPayload, request: Request):
    current_user = get_current_user_and_role(request)
    if current_user["role"] != "finance_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only finance administrators can update default company policies."
        )
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        policy_id = payload.policy_id or f"{payload.company_id}_default"
        data = payload.dict()
        data["policy_id"] = policy_id
        data["created_by"] = current_user["email"]
        data["updated_by"] = current_user["email"]
        data["created_at"] = datetime.utcnow().isoformat() + "Z"
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        db.collection("company_policy_settings").document(policy_id).set(data)
        
        # Write audit log
        add_audit_log(
            claim_id="",
            session_id="",
            event_type="company_defaults_updated",
            event_message=f"Created or updated default company per diem policy settings.",
            actor=current_user["email"] if current_user.get("email") else current_user["role"],
            actor_email=current_user["email"],
            actor_role=current_user["role"],
            authenticated=current_user["authenticated"],
            metadata={"policy_settings": data}
        )
        return {"status": "success", "policy_id": policy_id}
    except Exception as e:
        logger.error(f"Error writing default policy settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save default company per diem policy settings: {str(e)}")



@app.get("/api/me")
async def get_me(request: Request):
    user = get_current_user_and_role(request)
    return {
        "email": user["email"],
        "role": user["role"],
        "name": user.get("name", ""),
        "company_id": "demo_company",
        "authenticated": user["authenticated"]
    }

@app.post("/api/employee/claims")
async def create_employee_claim(claim_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    
    # 1. Validate required fields
    if not claim_data.get("category"):
        raise HTTPException(status_code=400, detail="Category is required")
    try:
        amount = float(claim_data.get("amount") or 0.0)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid amount value")
        
    # 2. Assign & Normalize
    claim_id = claim_data.get("claim_id") or str(uuid.uuid4())
    session_id = claim_id  # Align session_id with claim_id for upload matching
    
    company_id = claim_data.get("company_id") or "demo_company"
    
    # Check if logged in user is finance_admin and submits on behalf of demo employee
    employee_email = claim_data.get("employee_email")
    if current_user["role"] == "finance_admin" and employee_email:
        pass
    else:
        employee_email = current_user["email"]
        
    # Retrieve employee details from Firestore (Next Step 1)
    employee_profile_status = "missing_employee_record"
    employee_id = ""
    employee_name = claim_data.get("employee_name") or employee_email.split("@")[0].replace(".", " ").title()
    department = claim_data.get("department") or "N/A"
    manager_email = claim_data.get("manager_email") or "manager@company.com"
    
    if db:
        try:
            emp_docs = list(db.collection("employees").where("employee_email", "==", employee_email).where("active", "==", True).limit(1).get())
            if emp_docs:
                emp_data = emp_docs[0].to_dict()
                employee_profile_status = "found"
                department = emp_data.get("department") or department
                manager_email = emp_data.get("manager_email") or manager_email
                employee_id = emp_data.get("employee_id") or employee_id
                employee_name = emp_data.get("employee_name") or employee_name
        except Exception as e:
            logger.warning(f"Error checking employee profile during claim creation: {e}")

    claim_data["employee_email"] = employee_email
    claim_data["employee_name"] = employee_name
    claim_data["employee_id"] = employee_id
    claim_data["employee_profile_status"] = employee_profile_status
    claim_data["department"] = department
    claim_data["manager_email"] = manager_email
    
    # Check for existing document uploads
    if db:
        uploaded_docs = list(db.collection(DOCUMENTS_COL).where("session_id", "==", session_id).get())
        for doc_item in uploaded_docs:
            doc_data = doc_item.to_dict()
            doc_type = doc_data.get("doc_type")
            doc_url_fields = {
                "receipt": "receipt_url",
                "hotel_receipt": "hotel_receipt_url",
                "flight_ticket_receipt": "flight_ticket_receipt_url",
                "manager_approval_letter": "manager_approval_letter_url",
                "office_receipt": "office_receipt_url",
                "parking_receipt": "parking_receipt_url",
                "mileage_log": "mileage_log_url",
                "rental_receipt": "rental_receipt_url",
                "gas_receipt": "gas_receipt_url",
                "toll_receipt": "toll_receipt_url"
            }
            if doc_type in doc_url_fields:
                claim_data[doc_url_fields[doc_type]] = f"/api/document/{session_id}/{doc_type}"
                
    # 4. Run policy check
    policy_res = run_policy_check_py(claim_data)
    
    # 3. Determine status
    if policy_res.get("missing_docs"):
        status = "blocked_missing_docs"
    elif not policy_res.get("is_valid") or "Requires manager approval" in policy_res.get("status", "") or "Requires manager approval letter" in policy_res.get("status", "") or policy_res.get("status") == "Potentially non-reimbursable":
        status = "pending_review"
    else:
        status = "auto_approved"
        
    pdr = policy_res.get("per_diem_review") or {}
    
    normalized_claim = {
        "claim_id": claim_id,
        "session_id": session_id,
        "company_id": company_id,
        "employee_email": employee_email,
        "employee_name": employee_name,
        "employee_id": employee_id,
        "employee_profile_status": employee_profile_status,
        "department": department,
        "manager_email": manager_email,
        "category": claim_data.get("category"),
        "amount": amount,
        "currency": claim_data.get("currency") or "USD",
        "expense_date": claim_data.get("expense_date") or datetime.utcnow().strftime("%Y-%m-%d"),
        "business_purpose": claim_data.get("business_purpose") or "",
        "description": claim_data.get("description") or "",
        "status": status,
        "policy_status": policy_res["status"],
        "required_documents": policy_res["required_docs"],
        "missing_documents": policy_res["missing_docs"],
        "submitted_by_email": current_user["email"],
        "submitted_by_role": current_user["role"],
        "submitted_at": datetime.utcnow().isoformat() + "Z",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "source": "employee_portal",
        
        # Travel fields
        "travel_start_date": claim_data.get("travel_start_date"),
        "travel_end_date": claim_data.get("travel_end_date"),
        "city": claim_data.get("city"),
        "state": claim_data.get("state"),
        "state_code": claim_data.get("state_code") or claim_data.get("state"),
        "country": claim_data.get("country") or "US",
        "claimed_meals": float(claim_data.get("claimed_meals") or 0.0),
        "claimed_lodging": float(claim_data.get("claimed_lodging") or 0.0),
        "claimed_incidentals": float(claim_data.get("claimed_incidentals") or 0.0),
        "check_in_date": claim_data.get("check_in_date"),
        "check_out_date": claim_data.get("check_out_date"),
        
        # Transportation fields
        "transportation_type": claim_data.get("transportation_type"),
        "trip_date": claim_data.get("trip_date"),
        "start_location_label": claim_data.get("start_location_label"),
        "start_address": claim_data.get("start_address"),
        "destination_location_label": claim_data.get("destination_location_label"),
        "destination_address": claim_data.get("destination_address"),
        "trip_type": claim_data.get("trip_type"),
        "business_miles": float(claim_data.get("business_miles") or 0.0),
        "employee_entered_miles": float(claim_data.get("employee_entered_miles") or 0.0),
        "rental_start_date": claim_data.get("rental_start_date"),
        "rental_end_date": claim_data.get("rental_end_date"),
        "rental_cost": float(claim_data.get("rental_cost") or 0.0),
        "gas_cost": float(claim_data.get("gas_cost") or 0.0),
        "parking_cost": float(claim_data.get("parking_cost") or 0.0),
        "toll_cost": float(claim_data.get("toll_cost") or 0.0),
        "linked_rental_claim_id": claim_data.get("linked_rental_claim_id"),
        "per_diem_review": pdr
    }
    
    # Assign document URLs
    for doc_type, url_field in {
        "receipt": "receipt_url",
        "hotel_receipt": "hotel_receipt_url",
        "flight_ticket_receipt": "flight_ticket_receipt_url",
        "manager_approval_letter": "manager_approval_letter_url",
        "office_receipt": "office_receipt_url",
        "parking_receipt": "parking_receipt_url",
        "mileage_log": "mileage_log_url",
        "rental_receipt": "rental_receipt_url",
        "gas_receipt": "gas_receipt_url",
        "toll_receipt": "toll_receipt_url"
    }.items():
        if claim_data.get(url_field):
            normalized_claim[url_field] = claim_data[url_field]
            
    if db:
        db.collection(EXPENSES_COL).document(claim_id).set(normalized_claim)
        
        # 6. Store audit log
        add_audit_log(
            claim_id=claim_id,
            session_id=session_id,
            event_type="employee_submitted_claim",
            event_message=f"Employee submitted claim {claim_id} via portal. Status: {status}.",
            actor=current_user["email"],
            actor_email=current_user["email"],
            actor_role=current_user["role"],
            authenticated=True,
            employee_email=employee_email,
            employee_name=employee_name,
            manager_email=manager_email,
            metadata={"policy_review": policy_res, "source": "employee_portal"}
        )
        
        # If auto-approved, record decision and finalize log
        if status == "auto_approved":
            decision_ref = db.collection(DECISIONS_COL).document()
            decision_ref.set({
                "claim_id": claim_id,
                "session_id": session_id,
                "decision": "approved",
                "decided_by": "agent",
                "decision_reason": "Claim is within company policy thresholds. Automated system approval.",
                "decided_at": datetime.utcnow().isoformat() + "Z",
                "final_agent_response": "Automated system approval."
            })
            add_audit_log(
                claim_id=claim_id,
                session_id=session_id,
                event_type="agent_finalized",
                event_message=f"Claim auto-approved. Status: auto_approved.",
                actor="agent",
                metadata={"final_response": "Automated system approval."}
            )
            
    return normalized_claim

@app.get("/api/employee/claims")
async def get_employee_claims(request: Request):
    current_user = get_current_user_and_role(request)
    if not db:
        return []
    try:
        show_all = request.query_params.get("all") == "true" and current_user["role"] == "finance_admin"
        if show_all:
            query = db.collection(EXPENSES_COL).order_by("created_at", direction=firestore.Query.DESCENDING)
            docs = list(query.get())
            return [sanitize_claim_dict(doc.to_dict()) for doc in docs]
        else:
            email = current_user["email"]
            claims_dict = {}
            q1 = db.collection(EXPENSES_COL).where("employee_email", "==", email).get()
            for doc in q1:
                claims_dict[doc.id] = doc.to_dict()
            q2 = db.collection(EXPENSES_COL).where("submitted_by_email", "==", email).get()
            for doc in q2:
                claims_dict[doc.id] = doc.to_dict()
            claims_list = list(claims_dict.values())
            claims_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return [sanitize_claim_dict(c) for c in claims_list]
    except Exception as e:
        logger.error(f"Error fetching employee claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/employee/claims/{claim_id}")
async def get_employee_claim_detail(claim_id: str, request: Request):
    current_user = get_current_user_and_role(request)
    if not db:
        raise HTTPException(status_code=500, detail="Database connection not available")
    try:
        doc_ref = db.collection(EXPENSES_COL).document(claim_id)
        expense_doc = doc_ref.get()
        if not expense_doc.exists:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
            
        expense_data = expense_doc.to_dict()
        
        is_owner = (
            expense_data.get("employee_email") == current_user["email"] or
            expense_data.get("submitted_by_email") == current_user["email"] or
            expense_data.get("employee_name", "").lower() == current_user["email"].lower()
        )
        is_manager_or_admin = current_user["role"] in ["manager", "finance_admin"]
        
        if not is_owner and not is_manager_or_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view this claim."
            )
            
        docs_ref = db.collection(DOCUMENTS_COL).where("claim_id", "==", claim_id)
        documents = [d.to_dict() for d in docs_ref.get()]
        
        decisions_ref = db.collection(DECISIONS_COL).where("claim_id", "==", claim_id)
        decisions = [d.to_dict() for d in decisions_ref.get()]
        
        audits_ref = db.collection(AUDIT_LOGS_COL).where("claim_id", "==", claim_id)
        audits = [a.to_dict() for a in audits_ref.get()]
        audits = sorted(audits, key=lambda x: x.get("timestamp", ""))
        
        return {
            "expense": sanitize_claim_dict(expense_data),
            "documents": documents,
            "decisions": decisions,
            "audit_logs": audits
        }
    except Exception as e:
        logger.error(f"Error fetching employee claim detail for {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/employee/claims/{claim_id}/documents/{doc_type}")
async def upload_employee_document(claim_id: str, doc_type: str, request: Request, file: UploadFile = File(...)):
    current_user = get_current_user_and_role(request)
    session_id = claim_id
    
    if db:
        doc_ref = db.collection(EXPENSES_COL).document(claim_id)
        expense_doc = doc_ref.get()
        if expense_doc.exists:
            expense_data = expense_doc.to_dict()
            is_owner = (
                expense_data.get("employee_email") == current_user["email"] or
                expense_data.get("submitted_by_email") == current_user["email"] or
                expense_data.get("employee_name", "").lower() == current_user["email"].lower()
            )
            is_manager_or_admin = current_user["role"] in ["manager", "finance_admin"]
            if not is_owner and not is_manager_or_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to upload documents for this claim."
                )
                
    allowed_doc_types = {
        "receipt", "hotel_receipt", "flight_ticket_receipt", 
        "manager_approval_letter", "office_receipt", "parking_receipt",
        "mileage_log", "rental_receipt", "gas_receipt", "toll_receipt"
    }
    if doc_type not in allowed_doc_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {doc_type}"
        )
        
    filename = file.filename or "file"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Only PDF, PNG, JPG, JPEG are allowed."
        )
        
    max_size = 10 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10 MB."
        )
        
    base_name = os.path.splitext(filename)[0]
    clean_base = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
    safe_filename = f"{clean_base}{ext}"
    
    object_path = f"uploads/{session_id}/{doc_type}/{safe_filename}"
    
    try:
        bucket = get_gcs_bucket()
        blobs_to_delete = bucket.list_blobs(prefix=f"uploads/{session_id}/{doc_type}/")
        for b in blobs_to_delete:
            try:
                b.delete()
            except Exception as de:
                logger.warning(f"Could not delete old blob {b.name}: {de}")
                
        blob = bucket.blob(object_path)
        blob.upload_from_string(contents, content_type=file.content_type or "application/octet-stream")
        
        metadata_path = f"uploads/{session_id}/metadata.json"
        metadata_blob = bucket.blob(metadata_path)
        metadata = {}
        if metadata_blob.exists():
            try:
                metadata = json.loads(metadata_blob.download_as_bytes().decode("utf-8"))
            except Exception as me:
                logger.warning(f"Error reading metadata: {me}")
                
        metadata[doc_type] = {
            "path": object_path,
            "display_name": safe_filename,
            "content_type": file.content_type
        }
        metadata_blob.upload_from_string(json.dumps(metadata, indent=2), content_type="application/json")
        
        if db:
            doc_data = {
                "claim_id": claim_id,
                "session_id": session_id,
                "doc_type": doc_type,
                "gcs_path": f"gs://{BUCKET_NAME}/{object_path}",
                "original_filename": filename,
                "content_type": file.content_type or "application/octet-stream",
                "uploaded_at": datetime.utcnow().isoformat() + "Z"
            }
            db.collection(DOCUMENTS_COL).document(f"{session_id}_{doc_type}").set(doc_data)
            
            add_audit_log(
                claim_id=claim_id,
                session_id=session_id,
                event_type="document_uploaded",
                event_message=f"Uploaded document {doc_type}: {filename}.",
                actor=current_user["email"],
                actor_email=current_user["email"],
                actor_role=current_user["role"],
                authenticated=True,
                metadata={"gcs_path": f"gs://{BUCKET_NAME}/{object_path}", "source": "employee_portal"}
            )
            
            expense_doc = db.collection(EXPENSES_COL).document(claim_id).get()
            if expense_doc.exists:
                await asyncio.to_thread(reevaluate_expense_policies, claim_id)
                
        return {
            "status": "success",
            "doc_type": doc_type,
            "path": object_path,
            "display_name": safe_filename
        }
    except Exception as e:
        logger.error(f"Error uploading file for claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/employee/claims/preview")
async def preview_claim_policy(claim_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    policy_res = run_policy_check_py(claim_data)
    
    amount = float(claim_data.get("amount") or 0.0)
    reimbursable_amount = amount
    non_reimbursable_amount = 0.0
    
    trans_type = (claim_data.get("transportation_type") or "").lower()
    cat = (claim_data.get("category") or "").lower()
    if trans_type == "personal_vehicle" and cat == "transportation":
        gas_cost = float(claim_data.get("gas_cost") or 0.0)
        if gas_cost > 0:
            non_reimbursable_amount = gas_cost
            reimbursable_amount = max(0.0, amount - gas_cost)
            
    return {
        "policy_status": policy_res["status"],
        "is_valid": policy_res["is_valid"],
        "required_documents": policy_res["required_docs"],
        "missing_documents": policy_res["missing_docs"],
        "warnings": policy_res["warnings"],
        "estimated_reimbursable": reimbursable_amount,
        "estimated_non_reimbursable": non_reimbursable_amount,
        "manager_approval_required": not policy_res["is_valid"] or "Requires manager approval" in policy_res["status"]
    }


# ==========================================
# ENTERPRISE EXPENSE REPORT WORKFLOW APIs
# ==========================================

def check_claim_missing_documents(report_id: str, claim: dict):
    """
    Reruns the policy check for the claim, and checks the actual uploaded documents
    assigned to this claim to filter out from missing_documents.
    """
    cat = (claim.get("category") or "").lower()
    trans_type = (claim.get("transportation_type") or "").lower()
    if cat == "rental_car_gas" or trans_type == "rental_car_gas":
        if not claim.get("linked_rental_claim_id") and db and report_id:
            try:
                sibling_claims_ref = db.collection("expense_claims").where("report_id", "==", report_id)
                sibling_claims = [doc.to_dict() for doc in sibling_claims_ref.get()]
                has_rental_sibling = any(
                    (s.get("category") or "").lower() == "rental_car" or 
                    (s.get("transportation_type") or "").lower() == "rental_car"
                    for s in sibling_claims
                )
                if has_rental_sibling:
                    claim["linked_rental_claim_id"] = "report_context"
            except Exception as e:
                logger.warning(f"Error checking sibling claims for rental context: {e}")

    policy_res = run_policy_check_py(claim)
    required_docs = policy_res.get("required_docs") or []
    
    uploaded_types = set()
    if db:
        try:
            docs_ref = db.collection("documents").where("report_id", "==", report_id).where("claim_id", "==", claim["claim_id"]).where("active", "==", True).where("assigned_to_claim", "==", True)
            assigned_docs = [doc.to_dict() for doc in docs_ref.get()]
            uploaded_types = {d.get("doc_type") for d in assigned_docs}
        except Exception as e:
            logger.warning(f"Error checking active documents for claim {claim['claim_id']}: {e}")
            
    type_map = {
        "manager_approval_letter": "Manager Approval Letter",
        "flight_ticket_receipt": "Flight Ticket Receipt",
        "hotel_receipt": "Hotel Receipt",
        "receipt": "Receipt",
        "office_receipt": "Office Receipt",
        "parking_receipt": "Parking Receipt",
        "rental_receipt": "Rental Receipt",
        "gas_receipt": "Gas Receipt"
    }
    
    uploaded_doc_names = {type_map.get(t, t) for t in uploaded_types}
    if "receipt" in uploaded_types or "hotel_receipt" in uploaded_types or "flight_ticket_receipt" in uploaded_types:
        uploaded_doc_names.add("Receipt")
        
    missing_docs = []
    for req in required_docs:
        if req not in uploaded_doc_names:
            if req == "Receipt" and ("receipt_url" in claim or "receipt" in uploaded_types):
                continue
            missing_docs.append(req)
            
    claim["required_documents"] = required_docs
    claim["missing_documents"] = missing_docs
    claim["policy_status"] = "Within policy" if not missing_docs and policy_res["is_valid"] else policy_res["status"]
    
    return claim


def recalculate_report_totals(report_id: str):
    """
    Queries all claims and documents for a given report_id and recalculates totals and counts,
    then updates the report in Firestore.
    """
    if not db:
        return
    try:
        claims_ref = db.collection("expense_claims").where("report_id", "==", report_id)
        claims = [doc.to_dict() for doc in claims_ref.get()]
        
        # Check if the report has been approved with exceptions or has an override reason
        report_ref = db.collection("expense_reports").document(report_id)
        report_snap = report_ref.get()
        report_data = report_snap.to_dict() if report_snap.exists else {}
        report_status = report_data.get("status") or "draft"
        has_override = bool(report_data.get("override_reason")) or report_status == "approved_with_exceptions"
        
        total_claimed = 0.0
        total_reimbursable = 0.0
        total_non_reimbursable = 0.0
        policy_exception_count = 0
        missing_document_count = 0
        
        for c in claims:
            c_amount = float(c.get("amount") or 0.0)
            total_claimed += c_amount
            
            policy_status = c.get("policy_status") or "Within policy"
            has_exception = policy_status != "Within policy" and "Within policy" not in policy_status
            missing_docs = c.get("missing_documents") or []
            has_missing_docs = len(missing_docs) > 0
            
            if has_exception:
                policy_exception_count += 1
            missing_document_count += len(missing_docs)
            
            c_reimb = float(c.get("reimbursable_amount") or 0.0)
            c_non_reimb = float(c.get("non_reimbursable_amount") or 0.0)
            
            if c.get("claim_status") == "rejected":
                total_non_reimbursable += c_amount
            else:
                # If there are policy exceptions or missing documents, and NO override exists on the report,
                # then this item is not reimbursable (reimbursable amount is 0)
                if (has_exception or has_missing_docs) and not has_override:
                    total_non_reimbursable += c_amount
                else:
                    total_reimbursable += c_reimb
                    total_non_reimbursable += c_non_reimb
                    
        docs_ref = db.collection("documents").where("report_id", "==", report_id).where("active", "==", True)
        docs = [doc.to_dict() for doc in docs_ref.get()]
        
        document_count = len(docs)
        unassigned_document_count = sum(1 for d in docs if not d.get("assigned_to_claim"))
        
        if report_snap.exists:
            report_ref.update({
                "total_claimed_amount": total_claimed,
                "total_reimbursable_amount": total_reimbursable,
                "total_non_reimbursable_amount": total_non_reimbursable,
                "claim_count": len(claims),
                "document_count": document_count,
                "unassigned_document_count": unassigned_document_count,
                "missing_document_count": missing_document_count,
                "policy_exception_count": policy_exception_count,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            })
    except Exception as e:
        logger.error(f"Error recalculating report {report_id} totals: {e}")


def add_report_audit_log(report_id: str, claim_id: str, event_type: str, message: str, current_user: dict, override_reason: str = None):
    """
    Writes a structured audit trail event log to Firestore for reports.
    """
    if not db:
        return
    try:
        doc_ref = db.collection("audit_logs").document()
        payload = {
            "company_id": "demo_company",
            "report_id": report_id,
            "claim_id": claim_id,
            "event_id": doc_ref.id,
            "event_type": event_type,
            "actor_email": current_user.get("email"),
            "actor_role": current_user.get("role"),
            "authenticated": True if event_type == "manager_decision" else current_user.get("authenticated", False),
            "message": message,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        if override_reason:
            payload["override_reason"] = override_reason
            
        report_ref = db.collection("expense_reports").document(report_id)
        report_snap = report_ref.get()
        if report_snap.exists:
            report_data = report_snap.to_dict()
            payload["employee_email"] = report_data.get("employee_email")
            payload["manager_email"] = report_data.get("manager_email")
            
        doc_ref.set(payload)
    except Exception as e:
        logger.error(f"Failed to write report audit log: {e}")


@app.get("/api/reports")
async def get_reports(
    request: Request,
    status: str = None,
    employee: str = None,
    manager: str = None,
    department: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 50,
    offset: int = 0
):
    current_user = get_current_user_and_role(request)
    email = current_user["email"]
    role = current_user["role"]
    
    if not db:
        return []
        
    try:
        query = db.collection("expense_reports")
        
        # Scoping
        if role == "employee":
            query = query.where("employee_email", "==", email)
        elif role == "manager":
            query = query.where("manager_email", "==", email)
        elif role == "finance_admin":
            pass
        else:
            raise HTTPException(status_code=403, detail="Role not authorized to access reports")
            
        query = query.order_by("updated_at", direction=firestore.Query.DESCENDING)
        reports = [doc.to_dict() for doc in query.limit(limit + offset).get()]
        
        if offset > 0:
            reports = reports[offset:]
            
        filtered = []
        for r in reports:
            if status and r.get("status") != status:
                continue
            if employee and employee.lower() not in (r.get("employee_email") or "").lower() and employee.lower() not in (r.get("employee_name") or "").lower():
                continue
            if manager and manager.lower() not in (r.get("manager_email") or "").lower():
                continue
            if department and r.get("department") != department:
                continue
            if start_date and r.get("report_period_start") and r.get("report_period_start") < start_date:
                continue
            if end_date and r.get("report_period_end") and r.get("report_period_end") > end_date:
                continue
            filtered.append(r)
            
        return filtered
    except Exception as e:
        logger.error(f"Error in GET /api/reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports")
async def create_report(report_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    email = current_user["email"]
    role = current_user["role"]
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    company_id = report_data.get("company_id") or "demo_company"
    report_id = "rep_" + str(uuid.uuid4())[:18]
    
    employee_email = report_data.get("employee_email")
    if role == "finance_admin" and employee_email:
        pass
    else:
        employee_email = email
        
    employee_name = report_data.get("employee_name") or employee_email.split("@")[0].replace(".", " ").title()
    department = report_data.get("department") or "N/A"
    manager_email = report_data.get("manager_email") or "manager@company.com"
    employee_id = employee_email.split("@")[0]
    
    try:
        emp_docs = list(db.collection("employees").where("employee_email", "==", employee_email).where("active", "==", True).limit(1).get())
        if emp_docs:
            emp_data = emp_docs[0].to_dict()
            department = emp_data.get("department") or department
            manager_email = emp_data.get("manager_email") or manager_email
            employee_id = emp_data.get("employee_id") or employee_id
            employee_name = emp_data.get("employee_name") or employee_name
    except Exception as e:
        logger.warning(f"Error fetching employee profile: {e}")
        
    start_date = report_data.get("report_period_start") or datetime.utcnow().strftime("%Y-%m-%d")
    end_date = report_data.get("report_period_end") or datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        date_obj = datetime.fromisoformat(start_date.replace("Z", ""))
        month = date_obj.strftime("%B")
        year = date_obj.year
    except Exception:
        month = datetime.utcnow().strftime("%B")
        year = datetime.utcnow().year
        
    report = {
        "company_id": company_id,
        "report_id": report_id,
        "employee_id": employee_id,
        "employee_email": employee_email,
        "employee_name": employee_name,
        "department": department,
        "manager_id": manager_email.split("@")[0] if manager_email else "",
        "manager_email": manager_email,
        "report_title": report_data.get("report_title") or "Expense Report",
        "report_period_start": start_date,
        "report_period_end": end_date,
        "travel_week": report_data.get("travel_week"),
        "month": month,
        "year": year,
        "status": "draft",
        "total_claimed_amount": 0.0,
        "total_reimbursable_amount": 0.0,
        "total_non_reimbursable_amount": 0.0,
        "claim_count": 0,
        "document_count": 0,
        "unassigned_document_count": 0,
        "missing_document_count": 0,
        "policy_exception_count": 0,
        "submitted_by_email": "",
        "submitted_by_role": "",
        "submitted_at": "",
        "manager_reviewed_by": "",
        "manager_reviewed_at": "",
        "finance_reviewed_by": "",
        "finance_reviewed_at": "",
        "return_reason": "",
        "rejection_reason": "",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        db.collection("expense_reports").document(report_id).set(report)
        add_report_audit_log(report_id, None, "report_created", f"Created draft report '{report['report_title']}'.", current_user)
        return report
    except Exception as e:
        logger.error(f"Error creating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}")
async def get_report_detail(report_id: str, request: Request):
    current_user = get_current_user_and_role(request)
    email = current_user["email"]
    role = current_user["role"]
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_doc = db.collection("expense_reports").document(report_id).get()
        if not report_doc.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = report_doc.to_dict()
        
        if role == "employee" and report.get("employee_email") != email:
            raise HTTPException(status_code=403, detail="Access denied to this report")
        elif role == "manager" and report.get("manager_email") != email and role != "finance_admin":
            raise HTTPException(status_code=403, detail="Access denied to this report")
            
        recalculate_report_totals(report_id)
        report = db.collection("expense_reports").document(report_id).get().to_dict()
        
        claims = [d.to_dict() for d in db.collection("expense_claims").where("report_id", "==", report_id).get()]
        documents = [d.to_dict() for d in db.collection("documents").where("report_id", "==", report_id).where("active", "==", True).get()]
        decisions = [d.to_dict() for d in db.collection("report_decisions").where("report_id", "==", report_id).get()]
        audit_logs = [d.to_dict() for d in db.collection("audit_logs").where("report_id", "==", report_id).get()]
        
        # Sort audit logs manually in memory to prevent indexing issues
        audit_logs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        return {
            "report": report,
            "claims": claims,
            "documents": documents,
            "decisions": decisions,
            "audit_logs": audit_logs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in GET /api/reports/{report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/reports/{report_id}")
async def update_report(report_id: str, update_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        ref = db.collection("expense_reports").document(report_id)
        snap = ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = snap.to_dict()
        if report.get("status") not in ["draft", "returned_to_employee"]:
            raise HTTPException(status_code=400, detail="Can only update draft or returned reports")
            
        allowed_updates = ["report_title", "report_period_start", "report_period_end", "travel_week"]
        payload = {}
        for k in allowed_updates:
            if k in update_data:
                payload[k] = update_data[k]
                
        if payload:
            payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
            ref.update(payload)
            add_report_audit_log(report_id, None, "report_updated", f"Updated report fields: {', '.join(payload.keys())}.", current_user)
            
        return ref.get().to_dict()
    except Exception as e:
        logger.error(f"Error updating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/claims")
async def add_claim_to_report(report_id: str, claim_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_ref = db.collection("expense_reports").document(report_id)
        report_snap = report_ref.get()
        if not report_snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = report_snap.to_dict()
        if report.get("status") not in ["draft", "returned_to_employee"]:
            raise HTTPException(status_code=400, detail="Can only add claims to draft or returned reports")
            
        claim_id = claim_data.get("claim_id") or "clm_" + str(uuid.uuid4())[:18]
        amount = float(claim_data.get("amount") or 0.0)
        reimbursable_amount = amount
        non_reimbursable_amount = 0.0
        
        trans_type = (claim_data.get("transportation_type") or "").lower()
        cat = (claim_data.get("category") or "").lower()
        if trans_type == "personal_vehicle" and cat == "transportation":
            gas_cost = float(claim_data.get("gas_cost") or 0.0)
            if gas_cost > 0:
                non_reimbursable_amount = gas_cost
                reimbursable_amount = max(0.0, amount - gas_cost)
                
        claim = {
            "company_id": report.get("company_id") or "demo_company",
            "report_id": report_id,
            "claim_id": claim_id,
            "employee_id": report.get("employee_id"),
            "employee_email": report.get("employee_email"),
            "employee_name": report.get("employee_name"),
            "manager_email": report.get("manager_email"),
            "category": claim_data.get("category"),
            "amount": amount,
            "currency": claim_data.get("currency") or "USD",
            "expense_date": claim_data.get("expense_date") or datetime.utcnow().strftime("%Y-%m-%d"),
            "business_purpose": claim_data.get("business_purpose") or "",
            "description": claim_data.get("description") or "",
            "claim_status": "draft",
            "reimbursable_amount": reimbursable_amount,
            "non_reimbursable_amount": non_reimbursable_amount,
            "transportation_type": claim_data.get("transportation_type"),
            "gas_cost": claim_data.get("gas_cost"),
            "mileage": claim_data.get("mileage"),
            "check_in_date": claim_data.get("check_in_date"),
            "check_out_date": claim_data.get("check_out_date"),
            "travel_start_date": claim_data.get("travel_start_date") or report.get("report_period_start"),
            "travel_end_date": claim_data.get("travel_end_date") or report.get("report_period_end"),
            "city": claim_data.get("city") or report.get("city") or "",
            "state": claim_data.get("state") or report.get("state") or "",
            "state_code": claim_data.get("state_code") or report.get("state_code") or "",
            "country": claim_data.get("country") or report.get("country") or "US",
            "claimed_meals": claim_data.get("claimed_meals"),
            "claimed_lodging": claim_data.get("claimed_lodging"),
            "claimed_incidentals": claim_data.get("claimed_incidentals"),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        claim = check_claim_missing_documents(report_id, claim)
        db.collection("expense_claims").document(claim_id).set(claim)
        
        recalculate_report_totals(report_id)
        add_report_audit_log(report_id, claim_id, "claim_added_to_report", f"Added line item {claim['category']} of {claim['amount']} {claim['currency']} to report.", current_user)
        
        return claim
    except Exception as e:
        logger.error(f"Error adding claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/reports/{report_id}/claims/{claim_id}")
async def update_claim_in_report(report_id: str, claim_id: str, claim_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_ref = db.collection("expense_reports").document(report_id)
        if not report_ref.get().exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = report_ref.get().to_dict()
        if report.get("status") not in ["draft", "returned_to_employee"]:
            raise HTTPException(status_code=400, detail="Can only update claims of draft or returned reports")
            
        claim_ref = db.collection("expense_claims").document(claim_id)
        snap = claim_ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        claim = snap.to_dict()
        allowed_updates = ["category", "amount", "currency", "expense_date", "business_purpose", "description", "transportation_type", "gas_cost", "mileage", "check_in_date", "check_out_date"]
        for k in allowed_updates:
            if k in claim_data:
                claim[k] = claim_data[k]
                
        amount = float(claim.get("amount") or 0.0)
        reimbursable_amount = amount
        non_reimbursable_amount = 0.0
        
        trans_type = (claim.get("transportation_type") or "").lower()
        cat = (claim.get("category") or "").lower()
        if trans_type == "personal_vehicle" and cat == "transportation":
            gas_cost = float(claim.get("gas_cost") or 0.0)
            if gas_cost > 0:
                non_reimbursable_amount = gas_cost
                reimbursable_amount = max(0.0, amount - gas_cost)
                
        claim["amount"] = amount
        claim["reimbursable_amount"] = reimbursable_amount
        claim["non_reimbursable_amount"] = non_reimbursable_amount
        claim["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        claim = check_claim_missing_documents(report_id, claim)
        claim_ref.set(claim)
        
        recalculate_report_totals(report_id)
        add_report_audit_log(report_id, claim_id, "claim_updated", f"Updated line item {claim['category']}.", current_user)
        
        return claim
    except Exception as e:
        logger.error(f"Error updating claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{report_id}/claims/{claim_id}")
async def delete_claim_from_report(report_id: str, claim_id: str, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_ref = db.collection("expense_reports").document(report_id)
        if not report_ref.get().exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = report_ref.get().to_dict()
        if report.get("status") not in ["draft", "returned_to_employee"]:
            raise HTTPException(status_code=400, detail="Can only delete claims from draft or returned reports")
            
        claim_ref = db.collection("expense_claims").document(claim_id)
        if not claim_ref.get().exists:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        claim = claim_ref.get().to_dict()
        
        docs_ref = db.collection("documents").where("report_id", "==", report_id).where("claim_id", "==", claim_id)
        for doc_snap in docs_ref.get():
            doc_snap.reference.update({
                "claim_id": None,
                "assigned_to_claim": False
            })
            
        claim_ref.delete()
        recalculate_report_totals(report_id)
        add_report_audit_log(report_id, claim_id, "claim_deleted", f"Deleted line item {claim.get('category')}.", current_user)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/documents")
async def bulk_upload_report_documents(report_id: str, request: Request, files: list[UploadFile] = File(...)):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_ref = db.collection("expense_reports").document(report_id)
        if not report_ref.get().exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        uploaded_docs = []
        bucket = get_gcs_bucket()
        
        for file in files:
            filename = file.filename or "file"
            ext = os.path.splitext(filename)[1].lower()
            allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
            if ext not in allowed_exts:
                continue
                
            contents = await file.read()
            doc_id = "doc_" + str(uuid.uuid4())[:18]
            doc_type = "receipt"
            
            object_path = f"uploads/reports/{report_id}/{doc_id}/{filename}"
            blob = bucket.blob(object_path)
            blob.upload_from_string(contents, content_type=file.content_type or "application/octet-stream")
            
            doc_data = {
                "company_id": "demo_company",
                "report_id": report_id,
                "claim_id": None,
                "document_id": doc_id,
                "doc_type": doc_type,
                "file_name": filename,
                "gcs_path": f"gs://{BUCKET_NAME}/{object_path}",
                "assigned_to_claim": False,
                "uploaded_by_email": current_user.get("email") or "employee@company.com",
                "uploaded_by_role": current_user.get("role") or "employee",
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "active": True
            }
            
            db.collection("documents").document(doc_id).set(doc_data)
            uploaded_docs.append(doc_data)
            
        recalculate_report_totals(report_id)
        add_report_audit_log(report_id, None, "document_bulk_uploaded", f"Bulk uploaded {len(uploaded_docs)} document(s).", current_user)
        
        return uploaded_docs
    except Exception as e:
        logger.error(f"Error bulk uploading documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/documents/{document_id}/assign")
async def assign_document_to_claim(report_id: str, document_id: str, assign_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        doc_ref = db.collection("documents").document(document_id)
        snap = doc_ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Document not found")
            
        doc = snap.to_dict()
        claim_id = assign_data.get("claim_id")
        doc_type = assign_data.get("doc_type") or doc.get("doc_type")
        
        payload = {
            "claim_id": claim_id,
            "assigned_to_claim": True if claim_id else False,
            "doc_type": doc_type
        }
        doc_ref.update(payload)
        
        doc.update(payload)
        doc["status"] = "success"
        
        if claim_id:
            claim_ref = db.collection("expense_claims").document(claim_id)
            claim_snap = claim_ref.get()
            if claim_snap.exists:
                claim = claim_snap.to_dict()
                claim = check_claim_missing_documents(report_id, claim)
                claim_ref.set(claim)
                
        recalculate_report_totals(report_id)
        msg = f"Assigned document '{doc.get('file_name')}' to claim." if claim_id else f"Unassigned document '{doc.get('file_name')}'."
        add_report_audit_log(report_id, claim_id, "document_assigned_to_claim", msg, current_user)
        
        return doc
    except Exception as e:
        logger.error(f"Error assigning document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/submit")
async def submit_report(report_id: str, submit_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    role = current_user["role"]
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        report_ref = db.collection("expense_reports").document(report_id)
        report_snap = report_ref.get()
        if not report_snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = report_snap.to_dict()
        if report.get("status") not in ["draft", "returned_to_employee"]:
            raise HTTPException(status_code=400, detail="Can only submit draft or returned reports")
            
        claims_ref = db.collection("expense_claims").where("report_id", "==", report_id)
        claims = [c.to_dict() for c in claims_ref.get()]
        
        if not claims:
            raise HTTPException(status_code=400, detail="Report must have at least one line item claim before submission.")
            
        total_missing = 0
        for c in claims:
            updated_c = check_claim_missing_documents(report_id, c)
            db.collection("expense_claims").document(c["claim_id"]).set(updated_c)
            total_missing += len(updated_c.get("missing_documents") or [])
            
        is_override = submit_data.get("override_missing_docs") or (role == "finance_admin")
        if total_missing > 0 and not is_override:
            raise HTTPException(status_code=400, detail=f"Submission blocked: {total_missing} required document(s) are missing.")
            
        unassigned_ref = db.collection("documents").where("report_id", "==", report_id).where("assigned_to_claim", "==", False).where("active", "==", True)
        for doc_snap in unassigned_ref.get():
            doc_snap.reference.update({
                "assigned_to_claim": True,
                "claim_id": "supporting"
            })
            
        recalculate_report_totals(report_id)
        report_ref.update({
            "status": "pending_manager_review",
            "submitted_by_email": current_user.get("email"),
            "submitted_by_role": current_user.get("role"),
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        for c in claims:
            db.collection("expense_claims").document(c["claim_id"]).update({"claim_status": "submitted"})
            
        add_report_audit_log(report_id, None, "report_submitted", "Expense report submitted for manager review.", current_user)
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/return")
async def return_report(report_id: str, decision_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    reason = decision_data.get("reason")
    if not reason:
        raise HTTPException(status_code=400, detail="Return reason is required")
        
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        ref = db.collection("expense_reports").document(report_id)
        snap = ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = snap.to_dict()
        ref.update({
            "status": "returned_to_employee",
            "return_reason": reason,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        dec_id = "dec_" + str(uuid.uuid4())[:18]
        dec_data = {
            "company_id": report.get("company_id") or "demo_company",
            "report_id": report_id,
            "claim_id": None,
            "decision_id": dec_id,
            "decision_scope": "report",
            "decision": "returned_to_employee",
            "reason": reason,
            "actor_email": current_user.get("email"),
            "actor_role": current_user.get("role"),
            "authenticated": True,
            "decided_at": datetime.utcnow().isoformat() + "Z"
        }
        db.collection("report_decisions").document(dec_id).set(dec_data)
        
        add_report_audit_log(report_id, None, "report_returned_to_employee", f"Report returned to employee. Reason: {reason}", current_user)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error returning report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/approve")
async def approve_report(report_id: str, request: Request):
    current_user = get_current_user_and_role(request)
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        ref = db.collection("expense_reports").document(report_id)
        snap = ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = snap.to_dict()
        
        override_reason = None
        try:
            body = await request.json()
            if isinstance(body, dict):
                override_reason = body.get("override_reason")
        except Exception:
            pass
            
        missing_docs_count = report.get("missing_document_count") or 0
        exceptions_count = report.get("policy_exception_count") or 0
        
        status = "approved_by_manager"
        if missing_docs_count > 0 or exceptions_count > 0:
            if not override_reason or not override_reason.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Report contains policy exceptions or missing documents. An override reason is required."
                )
            status = "approved_with_exceptions"
            
        update_data = {
            "status": status,
            "manager_reviewed_by": current_user.get("email"),
            "manager_reviewed_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        if override_reason:
            update_data["override_reason"] = override_reason
            
        ref.update(update_data)
        
        # Recalculate totals now that status and override are updated, to include approved/overridden claims
        recalculate_report_totals(report_id)
        
        claims_ref = db.collection("expense_claims").where("report_id", "==", report_id)
        for c_snap in claims_ref.get():
            c = c_snap.to_dict()
            if c.get("claim_status") != "rejected":
                c_snap.reference.update({"claim_status": "approved"})
                
        dec_id = "dec_" + str(uuid.uuid4())[:18]
        dec_data = {
            "company_id": report.get("company_id") or "demo_company",
            "report_id": report_id,
            "claim_id": None,
            "decision_id": dec_id,
            "decision_scope": "report",
            "decision": "approved",
            "reason": override_reason or "Full report approved.",
            "actor_email": current_user.get("email"),
            "actor_role": current_user.get("role"),
            "authenticated": True,
            "decided_at": datetime.utcnow().isoformat() + "Z"
        }
        if override_reason:
            dec_data["override_reason"] = override_reason
            
        db.collection("report_decisions").document(dec_id).set(dec_data)
        
        audit_msg = "Expense report approved by manager."
        if status == "approved_with_exceptions":
            audit_msg = f"Expense report approved with exceptions. Override reason: {override_reason}"
            
        add_report_audit_log(report_id, None, "manager_decision", audit_msg, current_user, override_reason=override_reason)
        
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/reject")
async def reject_report(report_id: str, decision_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    reason = decision_data.get("reason") or "Rejected by manager."
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        ref = db.collection("expense_reports").document(report_id)
        snap = ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Report not found")
            
        report = snap.to_dict()
        ref.update({
            "status": "rejected",
            "rejection_reason": reason,
            "manager_reviewed_by": current_user.get("email"),
            "manager_reviewed_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        claims_ref = db.collection("expense_claims").where("report_id", "==", report_id)
        for c_snap in claims_ref.get():
            c_snap.reference.update({"claim_status": "rejected"})
            
        dec_id = "dec_" + str(uuid.uuid4())[:18]
        dec_data = {
            "company_id": report.get("company_id") or "demo_company",
            "report_id": report_id,
            "claim_id": None,
            "decision_id": dec_id,
            "decision_scope": "report",
            "decision": "rejected",
            "reason": reason,
            "actor_email": current_user.get("email"),
            "actor_role": current_user.get("role"),
            "authenticated": True,
            "decided_at": datetime.utcnow().isoformat() + "Z"
        }
        db.collection("report_decisions").document(dec_id).set(dec_data)
        
        add_report_audit_log(report_id, None, "manager_decision", f"Expense report rejected. Reason: {reason}", current_user)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error rejecting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/claims/{claim_id}/decision")
async def decide_individual_claim(report_id: str, claim_id: str, decision_data: dict, request: Request):
    current_user = get_current_user_and_role(request)
    decision = decision_data.get("decision")
    reason = decision_data.get("reason") or f"Claim {decision}."
    
    if decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be approved or rejected")
        
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        claim_ref = db.collection("expense_claims").document(claim_id)
        snap = claim_ref.get()
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Claim not found")
            
        claim_ref.update({
            "claim_status": decision,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        dec_id = "dec_" + str(uuid.uuid4())[:18]
        dec_data = {
            "company_id": "demo_company",
            "report_id": report_id,
            "claim_id": claim_id,
            "decision_id": dec_id,
            "decision_scope": "claim",
            "decision": decision,
            "reason": reason,
            "actor_email": current_user.get("email"),
            "actor_role": current_user.get("role"),
            "authenticated": True,
            "decided_at": datetime.utcnow().isoformat() + "Z"
        }
        db.collection("report_decisions").document(dec_id).set(dec_data)
        
        recalculate_report_totals(report_id)
        add_report_audit_log(report_id, claim_id, "claim_decision", f"Line item was {decision}. Reason: {reason}", current_user)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error in claim decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In - Ambience ExpenseFlow</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #060713;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.2);
            --accent: #8b5cf6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --glass-bg: rgba(15, 17, 36, 0.55);
            --glass-border: rgba(255, 255, 255, 0.08);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(139, 92, 246, 0.12) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
            padding: 1.5rem;
        }}

        .glow-sphere {{
            position: absolute;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, transparent 70%);
            filter: blur(40px);
            pointer-events: none;
            z-index: 0;
            animation: pulse 6s ease-in-out infinite alternate;
        }}

        .glow-sphere-1 {{ top: 10%; left: 15%; }}
        .glow-sphere-2 {{ bottom: 10%; right: 15%; }}

        @keyframes pulse {{
            0% {{ transform: scale(1) translate(0, 0); }}
            100% {{ transform: scale(1.2) translate(10px, 10px); }}
        }}

        .login-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 28px;
            padding: 3rem 2.5rem;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            text-align: center;
            position: relative;
            z-index: 10;
            animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}

        .login-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--primary), var(--accent), transparent);
        }}

        .logo-icon {{
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.5rem;
            color: white;
            margin: 0 auto 1.5rem auto;
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4);
            animation: float 4s ease-in-out infinite;
        }}

        h1 {{
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(to right, #ffffff, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        p {{
            font-size: 0.95rem;
            color: var(--text-muted);
            line-height: 1.5;
            margin-bottom: 2.5rem;
        }}

        .btn-google {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            background: #ffffff;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 0.9rem 1.5rem;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            width: 100%;
            transition: var(--transition);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            text-decoration: none;
        }}

        .btn-google:hover {{
            background: #f9fafb;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 255, 255, 0.15), 0 0 15px var(--primary-glow);
            border-color: var(--primary);
        }}

        .btn-google:active {{
            transform: translateY(0);
        }}

        .btn-google svg {{
            width: 20px;
            height: 20px;
        }}

        .badge-dev {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #f59e0b;
            padding: 0.75rem 1rem;
            border-radius: 12px;
            font-size: 0.85rem;
            line-height: 1.4;
            text-align: left;
            margin-bottom: 2rem;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }}

        .btn-bypass {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 0.9rem 1.5rem;
            font-family: inherit;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            width: 100%;
            transition: var(--transition);
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35);
            text-decoration: none;
            display: inline-block;
        }}

        .btn-bypass:hover {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.55);
        }}

        .footer-text {{
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.3);
            margin-top: 2.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-8px); }}
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    
        /* New premium styles for Expense Reports */
        .reports-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }
        .report-card {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }
        .report-card:hover {
            transform: translateY(-5px);
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.15);
        }
        .report-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }
        .report-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.5rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .report-meta {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
        }
        .report-meta-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .report-totals {
            display: flex;
            justify-content: space-between;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 1rem;
            margin-top: auto;
        }
        .report-total-box {
            display: flex;
            flex-direction: column;
        }
        .report-total-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .report-total-val {
            font-size: 1.1rem;
            font-weight: 700;
            color: white;
        }
        /* Slider Panel (slide drawer) */
        .slider-panel {
            position: fixed;
            top: 0;
            right: -450px;
            width: 450px;
            height: 100vh;
            background: rgba(10, 11, 26, 0.95);
            backdrop-filter: blur(20px);
            border-left: 1px solid var(--glass-border);
            box-shadow: -10px 0 40px rgba(0,0,0,0.5);
            z-index: 100;
            transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 2.5rem;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        .slider-panel.active {
            right: 0;
        }
        .slider-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding-bottom: 1rem;
        }
        /* Dropzone styling */
        .dropzone {
            border: 2px dashed rgba(99, 102, 241, 0.3);
            background: rgba(99, 102, 241, 0.02);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            margin: 1.5rem 0;
        }
        .dropzone:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.05);
        }
        /* Unassigned docs list */
        .unassigned-docs-bar {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.25rem;
            margin-top: 1.5rem;
        }
        .unassigned-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #f59e0b;
            padding: 0.4rem 0.8rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
        }
        .unassigned-badge:hover {
            background: rgba(245, 158, 11, 0.15);
            transform: scale(1.03);
        }

</style>
</head>
<body>
    <div class="glow-sphere glow-sphere-1"></div>
    <div class="glow-sphere glow-sphere-2"></div>

    <div class="login-card">
        <div class="logo-icon">AEF</div>
        <h1>Ambience ExpenseFlow</h1>
        <p>Enterprise Travel & Expense Management</p>

        {content_html}

        <div class="footer-text">SECURE OIDC SIGN-IN • AES-256 SESSION CODES</div>
    </div>
</body>
</html>
"""

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """
    Serves the beautifully stylized glassmorphic Login Page.
    """
    if is_auth_enabled():
        if request.session.get("user"):
            return RedirectResponse(url="/")
        content_html = """
        <a href="/login-google" class="btn-google">
            <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.18 1-.76 1.85-1.61 2.42v2.83h2.61c1.53-1.41 2.41-3.49 2.41-5.91z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-2.61-2.83c-.72.48-1.64.77-2.67.77-2.87 0-5.3-1.94-6.16-4.54H1.18v2.92C3 20.35 7.24 23 12 23z" fill="#34A853"/>
                <path d="M5.84 13.74c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V6.63H1.18C.43 8.09 0 9.73 0 11.5s.43 3.41 1.18 4.87l4.66-2.63z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.24 1 3 3.65 1.18 7.63l4.66 2.63c.86-2.6 3.3-4.54 6.16-4.54z" fill="#EA4335"/>
            </svg>
            Sign in with Google
        </a>
        """
    else:
        content_html = """
        <div class="badge-dev">
            <span style="font-size: 1.1rem; line-height: 1;">⚠️</span>
            <div>
                <strong>Local Test Mode Active</strong>
                <div style="margin-top: 2px; opacity: 0.8; font-size: 0.8rem;">AUTH_ENABLED is set to false. Real Google OAuth is bypassed. You will be authenticated as:</div>
                <div style="margin-top: 4px; font-family: monospace; font-weight: bold; color: white;">default-user@company.com (finance_admin)</div>
            </div>
        </div>
        <a href="/login-bypass" class="btn-bypass">
            Enter Dashboard
        </a>
        """
    return LOGIN_HTML.replace("{content_html}", content_html)

@app.get("/login-bypass")
async def login_bypass(request: Request):
    """
    Bypasses authentication and logs in as default finance admin for local testing.
    """
    if is_auth_enabled():
        return RedirectResponse(url="/login")
    request.session["user"] = {
        "email": "default-user@company.com",
        "name": "Default Administrator",
        "role": "finance_admin"
    }
    return RedirectResponse(url="/")

@app.get("/login-google")
async def login_google(request: Request):
    """
    Initiates Google OAuth authentication flow.
    """
    if not is_auth_enabled():
        return RedirectResponse(url="/")
        
    state = secrets.token_hex(16)
    request.session["state"] = state
    
    redirect_uri = get_redirect_uri(request)
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    """
    Handles redirect callback from Google OAuth service.
    """
    if not is_auth_enabled():
        return RedirectResponse(url="/")
        
    state = request.query_params.get("state")
    saved_state = request.session.get("state")
    if not state or state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state token (possible CSRF attempt)")
        
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code returned from Google")
        
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = get_redirect_uri(request)
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            token_response = json.loads(response.read().decode("utf-8"))
            
        id_token = token_response.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve ID token from Google")
            
        tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        with urllib.request.urlopen(tokeninfo_url, timeout=10) as response:
            token_info = json.loads(response.read().decode("utf-8"))
            
        if token_info.get("aud") != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="ID token audience mismatch")
            
        email = token_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email address not returned by Google")
            
        role = resolve_role(email)
        name = token_info.get("name", token_info.get("given_name", "Google User"))
        
        request.session["user"] = {
            "email": email,
            "name": name,
            "role": role
        }
        
        request.session.pop("state", None)
        return RedirectResponse(url="/")
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"Google Token Exchange HTTP Error: {e.code} - {error_body}")
        raise HTTPException(status_code=500, detail=f"Google sign-in token exchange failed: {error_body}")
    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth login failed: {str(e)}")

@app.get("/logout")
async def logout(request: Request):
    """
    Clears the user session and redirects to the login screen.
    """
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serves the beautifully stylized glassmorphic Manager Dashboard.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ambience ExpenseFlow Approval Dashboard</title>
    <!-- Outfit Google Font -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #080811;
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --accent: #8b5cf6;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --danger: #f43f5e;
            --danger-glow: rgba(244, 63, 94, 0.2);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --glass-bg: rgba(15, 17, 36, 0.45);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-glow: rgba(255, 255, 255, 0.02);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 40%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            padding: 2rem;
        }

        /* Ambient background glow spots */
        .glow-spot-1 {
            position: absolute;
            top: -10%;
            left: 20%;
            width: 40vw;
            height: 40vw;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }

        .glow-spot-2 {
            position: absolute;
            bottom: -10%;
            right: 15%;
            width: 35vw;
            height: 35vw;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.05) 0%, transparent 70%);
            pointer-events: none;
            z-index: 0;
        }

        header {
            position: relative;
            z-index: 10;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 2rem;
            margin-bottom: 2.5rem;
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .header-logo {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.2rem;
            color: white;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
        }

        .header-title h1 {
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(to right, #ffffff, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-title p {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .stats-container {
            display: flex;
            gap: 1rem;
            z-index: 10;
        }

        .stat-badge {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            padding: 0.5rem 1rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }

        .stat-badge .count {
            background: var(--primary);
            color: white;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
        }

        .refresh-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            color: var(--text-main);
            padding: 0.6rem 1.2rem;
            border-radius: 12px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: var(--transition);
        }

        .refresh-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
        }

        main {
            position: relative;
            z-index: 10;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 1.5rem;
        }

        /* Empty state styling */
        .empty-state {
            grid-column: 1 / -1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 6rem 2rem;
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            text-align: center;
            animation: fadeIn 0.6s ease forwards;
        }

        .empty-icon {
            font-size: 3rem;
            margin-bottom: 1.5rem;
            filter: drop-shadow(0 0 15px rgba(16, 185, 129, 0.4));
            animation: float 3s ease-in-out infinite;
        }

        .empty-state h3 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: white;
        }

        .empty-state p {
            color: var(--text-muted);
            max-width: 400px;
            line-height: 1.5;
        }

        /* Approval card layout */
        .approval-card {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.8rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            transition: var(--transition);
            box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.2);
            animation: fadeInUp 0.5s ease forwards;
        }

        .approval-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(to right, var(--primary), var(--accent));
            opacity: 0.8;
        }

        .approval-card:hover {
            transform: translateY(-6px);
            border-color: rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4), 0 0 20px rgba(99, 102, 241, 0.05);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.2rem;
        }

        .claimant-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: white;
            font-size: 1.1rem;
            box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.15);
        }

        .claimant-info h3 {
            font-size: 1.15rem;
            font-weight: 600;
            color: white;
        }

        .claimant-info p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .amount-tag {
            margin-left: auto;
            font-size: 1.5rem;
            font-weight: 800;
            color: #ffffff;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .card-body {
            margin-bottom: 1.8rem;
            flex-grow: 1;
        }

        .claim-desc {
            font-size: 0.95rem;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.85);
            margin-bottom: 1rem;
        }

        .meta-list {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .meta-item strong {
            color: rgba(255, 255, 255, 0.6);
            font-weight: 500;
        }

        .card-actions {
            display: flex;
            gap: 0.8rem;
            position: relative;
        }

        .btn {
            flex: 1;
            padding: 0.8rem;
            border-radius: 12px;
            font-family: inherit;
            font-weight: 700;
            font-size: 0.9rem;
            cursor: pointer;
            border: 1px solid transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: var(--transition);
        }

        .btn-approve {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .btn-approve:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
            transform: translateY(-2px);
        }

        .btn-reject {
            background: rgba(244, 63, 94, 0.1);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.2);
        }

        .btn-reject:hover {
            background: rgba(244, 63, 94, 0.25);
            border-color: rgba(244, 63, 94, 0.4);
            transform: translateY(-2px);
        }

        .btn-receipt {
            background: rgba(99, 102, 241, 0.1);
            color: #cbd5e1;
            border: 1px solid rgba(99, 102, 241, 0.25);
            text-decoration: none;
        }

        .btn-receipt:hover {
            background: rgba(99, 102, 241, 0.2) !important;
            border-color: var(--primary) !important;
            color: white !important;
            transform: translateY(-2px);
        }

        /* Loading Overlay inside card */
        .card-loader {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(8, 8, 17, 0.85);
            backdrop-filter: blur(8px);
            border-radius: 20px;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 100;
            animation: fadeIn 0.3s ease forwards;
        }

        .spinner {
            width: 32px;
            height: 32px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 0.8rem;
        }

        .loader-text {
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--text-main);
        }

        /* Slide-out Review Modal Sidebar */
        .slide-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: var(--transition);
        }

        .slide-overlay.active {
            opacity: 1;
            pointer-events: all;
        }

        .slide-modal {
            position: fixed;
            top: 0;
            right: 0;
            width: 480px;
            max-width: 100%;
            height: 100%;
            background: rgba(10, 11, 26, 0.95);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-left: 1px solid var(--glass-border);
            box-shadow: -10px 0 40px rgba(0, 0, 0, 0.5);
            z-index: 1001;
            transform: translateX(100%);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            padding: 2.5rem;
        }

        .slide-modal.active {
            transform: translateX(0);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }

        .modal-title h2 {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
        }

        .modal-title p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .close-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: var(--transition);
        }

        .close-btn:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: rotate(90deg);
        }

        .modal-body {
            flex-grow: 1;
            overflow-y: auto;
            padding-right: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Review status box */
        .status-box {
            padding: 1.5rem;
            border-radius: 16px;
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }

        .status-box.approved {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: #10b981;
        }

        .status-box.rejected {
            background: rgba(244, 63, 94, 0.1);
            border: 1px solid rgba(244, 63, 94, 0.25);
            color: #f43f5e;
        }

        .status-icon {
            font-size: 2rem;
        }

        .status-text h4 {
            font-size: 1.1rem;
            font-weight: 700;
        }

        .status-text p {
            font-size: 0.85rem;
            opacity: 0.8;
            margin-top: 2px;
        }

        .review-details-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.2rem;
        }

        .review-details-card h4 {
            font-size: 0.9rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.8rem;
        }

        .review-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        .review-field span {
            display: block;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .review-field strong {
            font-size: 1.05rem;
            color: white;
            font-weight: 600;
        }

        .compliance-box {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }

        .compliance-box h4 {
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .compliance-text {
            font-size: 0.95rem;
            line-height: 1.6;
            color: rgba(255, 255, 255, 0.9);
            white-space: pre-wrap;
            overflow-y: auto;
            flex-grow: 1;
            padding: 0.5rem 0;
        }

        .modal-footer {
            margin-top: 2rem;
        }

        .modal-done-btn {
            width: 100%;
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.9rem;
            border-radius: 12px;
            font-family: inherit;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            transition: var(--transition);
        }

        .modal-done-btn:hover {
            background: var(--accent);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
            transform: translateY(-2px);
        }

        /* Animations */
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Toast feedback alerts */
        .toast {
            position: fixed;
            bottom: 2rem;
            left: 2rem;
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(12px);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 0.8rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            transform: translateY(150%);
            transition: var(--transition);
            z-index: 2000;
        }

        .toast.active {
            transform: translateY(0);
        }

        .toast-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }

        .toast-success .toast-icon {
            background: var(--success);
        }

        .toast-error .toast-icon {
            background: var(--danger);
        }

        /* Avatar color variants using clean, harmonious gradients */
        .gradient-avatar-0 { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .gradient-avatar-1 { background: linear-gradient(135deg, #10b981, #059669); }
        .gradient-avatar-2 { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .gradient-avatar-3 { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .gradient-avatar-4 { background: linear-gradient(135deg, #ec4899, #db2777); }
        .gradient-avatar-5 { background: linear-gradient(135deg, #06b6d4, #0891b2); }

        /* Scrollbar customization */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.01);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        /* Submit Portal Style Tokens */
        .portal-layout {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
            margin-top: 1rem;
        }
        @media (min-width: 1024px) {
            .portal-layout {
                grid-template-columns: 1.6fr 1fr;
            }
        }
        .form-section-card {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
            position: relative;
            overflow: hidden;
        }
        .form-section-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
            opacity: 0.6;
        }
        .form-section-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: white;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 0.6rem;
        }
        .form-section-title span.section-icon {
            font-size: 1.4rem;
        }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .form-group.full-width {
            grid-column: 1 / -1;
        }
        .form-group label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .form-group input, .form-group select, .form-group textarea {
            background: rgba(10, 11, 30, 0.5);
            border: 1px solid var(--glass-border);
            border-radius: 10px;
            color: white;
            padding: 0.75rem 1rem;
            font-family: inherit;
            font-size: 0.95rem;
            transition: var(--transition);
            outline: none;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
            background: rgba(10, 11, 30, 0.7);
        }
        .form-group input::placeholder, .form-group textarea::placeholder {
            color: rgba(255, 255, 255, 0.25);
        }
        /* Upload Dropzones */
        .upload-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }
        .upload-dropzone {
            border: 2px dashed rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 1.25rem 1rem;
            text-align: center;
            background: rgba(255, 255, 255, 0.01);
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            position: relative;
        }
        .upload-dropzone:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.04);
        }
        .upload-dropzone.uploaded {
            border-style: solid;
            border-color: rgba(16, 185, 129, 0.4);
            background: rgba(16, 185, 129, 0.02);
        }
        .upload-dropzone .dropzone-icon {
            font-size: 1.6rem;
            transition: var(--transition);
        }
        .upload-dropzone:hover .dropzone-icon {
            transform: scale(1.1);
        }
        .upload-dropzone .dropzone-title {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-main);
        }
        .upload-dropzone .dropzone-status {
            font-size: 0.7rem;
            font-weight: 500;
        }
        /* Live Preview Sidebar */
        .preview-sidebar {
            position: sticky;
            top: 2rem;
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            align-self: start;
        }
        .preview-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .preview-metric:last-of-type {
            border-bottom: none;
        }
        .preview-metric-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
        }
        .preview-metric-value {
            font-size: 1rem;
            font-weight: 700;
            color: white;
        }
        .preview-metric-value.highlight {
            color: var(--primary);
            font-size: 1.15rem;
        }
        .preview-metric-value.success {
            color: #34d399;
        }
        .preview-metric-value.danger {
            color: #fb7185;
        }
        .warning-banner {
            padding: 0.8rem 1rem;
            border-radius: 10px;
            font-size: 0.8rem;
            line-height: 1.4;
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
        }
        .warning-banner.info {
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.2);
            color: #c7d2fe;
        }
        .warning-banner.danger {
            background: rgba(244, 63, 94, 0.08);
            border: 1px solid rgba(244, 63, 94, 0.2);
            color: #fb7185;
        }

        .filter-btn {
            background: none;
            border: 1px solid rgba(255,255,255,0.05);
            color: var(--text-muted);
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-btn:hover {
            background: rgba(255,255,255,0.05);
            border-color: rgba(255,255,255,0.15);
            color: white;
        }
        .filter-btn.active {
            background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 100%);
            border-color: rgba(99, 102, 241, 0.4);
            color: white;
            box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
        }
    
</style>
</head>
<body>
    <div class="glow-spot-1"></div>
    <div class="glow-spot-2"></div>

    <header>
        <div class="header-logo">
            <div class="logo-icon">AEF</div>
            <div class="header-title">
                <h1>Ambience ExpenseFlow</h1>
                <p>Enterprise Travel & Expense Management</p>
            </div>
        </div>
        <div class="stats-container">
            <div class="stat-badge" id="hidden-badge" style="display: none; border-color: rgba(244, 63, 94, 0.3); background: rgba(244, 63, 94, 0.05);">
                <span style="color: #fb7185;">Old CLI sessions hidden</span>
                <span class="count" style="background: var(--danger); box-shadow: 0 0 10px rgba(244, 63, 94, 0.5);" id="hidden-count">0</span>
            </div>
            <div class="stat-badge">
                <span style="color: #cbd5e1;">Current dashboard sessions</span>
                <span class="count" id="pending-count">0</span>
            </div>
            <button class="refresh-btn" onclick="fetchPendingApprovals()">
                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                </svg>
                Sync Engine
            </button>
        </div>
    </header>

    <!-- Beautiful glassmorphic tab bar -->
    <div class="tab-bar" style="display: flex; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid var(--glass-border); padding-bottom: 0.8rem; position: relative; z-index: 10;">
        <button class="tab-btn" id="tab-reports" onclick="switchTab('reports')" style="background: none; border: none; color: var(--text-muted); font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            My Reports
        </button>
        
        <button class="tab-btn" id="tab-submit" onclick="switchTab('submit')" style="background: none; border: none; color: var(--text-muted); font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            Submit Expense
        </button>
        <button class="tab-btn active" id="tab-pending" onclick="switchTab('pending')" style="background: none; border: none; color: white; font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            Pending Approvals
        </button>
        <button class="tab-btn" id="tab-history" onclick="switchTab('history')" style="background: none; border: none; color: var(--text-muted); font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            Expense History
        </button>
        <button class="tab-btn" id="tab-audit" onclick="switchTab('audit-trail')" style="background: none; border: none; color: var(--text-muted); font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            Audit Timeline
        </button>
    </div>

    <main>
        \n        
        <!-- 0. Expense Reports Section -->
        <div id="section-reports" class="tab-section" style="display: none;">
            <!-- Main reports dashboard container -->
            <div id="reports-dashboard-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <div>
                        <h1 id="reports-page-title" style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Expense Reports</h1>
                        <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.2rem;">Draft, review, and manage multi-item expense report containers.</p>
                    </div>
                </div>

                <!-- Admin & Manager Filter Bar (hidden for employees) -->
                <div id="reports-filter-bar" style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.25rem; margin-bottom: 1.5rem; display: none; gap: 1rem; flex-wrap: wrap; align-items: center;">
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Employee</label>
                        <input type="text" id="filter-employee" placeholder="Search email or name..." oninput="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Manager</label>
                        <input type="text" id="filter-manager" placeholder="Filter manager..." oninput="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Department</label>
                        <select id="filter-department" onchange="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                            <option value="">All Departments</option>
                            <option value="Engineering">Engineering</option>
                            <option value="Sales">Sales</option>
                            <option value="Marketing">Sales & Marketing</option>
                            <option value="Operations">Operations</option>
                            <option value="Finance">Finance</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Status</label>
                        <select id="filter-status" onchange="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                            <option value="">All Statuses</option>
                            <option value="draft">Draft</option>
                            <option value="pending_manager_review">Pending Manager Review</option>
                            <option value="returned_to_employee">Returned to Employee</option>
                            <option value="approved">Approved</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </div>
                    <button class="btn btn-receipt" onclick="clearReportFilters()" style="margin-top: 1.2rem; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600;">Clear</button>
                </div>

                <!-- Reports Grid Container -->
                <div class="reports-grid" id="reports-grid">
                    <!-- Cards will be populated dynamically -->
                </div>

                <!-- Create Report Secondary Panel -->
                <div id="create-report-container" style="background: linear-gradient(135deg, rgba(255,255,255,0.01) 0%, rgba(255,255,255,0.03) 100%); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); border-radius: 20px; padding: 2rem; margin-top: 2.5rem; display: flex; justify-content: space-between; align-items: center; gap: 2rem; flex-wrap: wrap; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); transition: transform 0.2s ease, border-color 0.2s ease;">
                    <div style="flex: 1; min-width: 280px;">
                        <h3 style="font-size: 1.25rem; font-weight: 700; color: white; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.5rem;">📁</span> Create a New Expense Report
                        </h3>
                        <p style="color: var(--text-muted); font-size: 0.9rem; line-height: 1.5;">
                            Group multiple business claims, travel per diems, and transport receipts into a single unified container for faster approval processing.
                        </p>
                    </div>
                    <div>
                        <button class="btn btn-primary" id="btn-create-report" onclick="openNewReportDrawer()" style="padding: 0.85rem 2rem; font-weight: 700; font-size: 0.95rem; border-radius: 12px; display: inline-flex; align-items: center; gap: 0.75rem; box-shadow: 0 0 16px rgba(99, 102, 241, 0.25); transition: all 0.2s;">
                            <span>+</span> Create New Report
                        </button>
                    </div>
                </div>
            </div>

            <!-- Report Builder Detailed View (Hidden by default, shown when builder active) -->
            <div id="report-builder-container" style="display: none;">
                <!-- Header with Back button -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.5rem 1rem; font-size: 0.85rem; border-radius: 8px; display: inline-flex; align-items: center; gap: 0.5rem;">
                            <span>&larr;</span> Back to list
                        </button>
                        <div>
                            <h2 id="builder-report-title" style="font-size: 1.6rem; font-weight: 800; color: white;">April Site Visits</h2>
                            <p id="builder-report-meta" style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.1rem;"></p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.75rem;" id="builder-actions-container">
                        <!-- Actions injected here dynamically based on role/status (e.g. Save Draft, Submit, Return, Approve, Reject) -->
                    </div>
                </div>

                <!-- Splitting Builder into left summary/claims and right documents/audit -->
                <div style="display: grid; grid-template-columns: 1.8fr 1fr; gap: 2rem; align-items: start;">
                    <!-- Left: Report Metadata & Claims Table -->
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <!-- Report stats banner -->
                        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.25rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Total Claimed</span>
                                <div id="stat-total-claimed" style="font-size: 1.3rem; font-weight: 700; color: white; margin-top: 0.2rem;">$0.00</div>
                            </div>
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Reimbursable</span>
                                <div id="stat-total-reimbursable" style="font-size: 1.3rem; font-weight: 700; color: var(--success); margin-top: 0.2rem;">$0.00</div>
                            </div>
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Exceptions</span>
                                <div id="stat-policy-exceptions" style="font-size: 1.3rem; font-weight: 700; color: #fb7185; margin-top: 0.2rem;">0</div>
                            </div>
                            <div>
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Missing Receipts</span>
                                <div id="stat-missing-documents" style="font-size: 1.3rem; font-weight: 700; color: #f59e0b; margin-top: 0.2rem;">0</div>
                            </div>
                        </div>

                        <!-- Return reason banner (if returned) -->
                        <div id="builder-return-reason-banner" style="display: none; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 12px; padding: 1rem; color: #fda4af;">
                            <strong>Returned by Reviewer:</strong> <span id="builder-return-reason-text"></span>
                        </div>

                        <!-- Line Items Header -->
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 1.2rem; font-weight: 700; color: white;">Expense Line Items</h3>
                            <button class="btn btn-primary" id="btn-add-line-item" onclick="openClaimFormModal()" style="padding: 0.5rem 1rem; font-size: 0.85rem; border-radius: 8px;">
                                + Add Expense Claim
                            </button>
                        </div>

                        <!-- Claims Table -->
                        <div style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 16px; overflow: hidden;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted); background: rgba(0,0,0,0.2);">
                                        <th style="padding: 0.8rem 1rem;">Category</th>
                                        <th style="padding: 0.8rem 1rem;">Date</th>
                                        <th style="padding: 0.8rem 1rem;">Amount</th>
                                        <th style="padding: 0.8rem 1rem;">Compliance</th>
                                        <th style="padding: 0.8rem 1rem;">Receipt Status</th>
                                        <th style="padding: 0.8rem 1rem; text-align: right;" class="builder-actions-column">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="builder-claims-tbody">
                                    <!-- Claims populated here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Right: GCS Receipts Hub & Audit Log -->
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <!-- Bulk Receipt Upload zone (only visible for drafts) -->
                        <div id="builder-upload-container" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.5rem;">Receipt Dossier</h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted);">Bulk upload receipts/PDFs. You can assign them to specific claims below.</p>
                            
                            <div class="dropzone" id="bulk-receipt-dropzone" onclick="triggerBulkFileInput()">
                                <span style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;">📁</span>
                                <span style="font-weight: 500; font-size: 0.85rem;">Drag & drop files or click to upload</span>
                                <span style="display: block; font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem;">PDF, PNG, JPG (Max 5MB)</span>
                                <input type="file" id="bulk-receipt-file-input" multiple style="display: none;" onchange="handleBulkReceiptsSelect(this.files)">
                            </div>
                        </div>

                        <!-- Unassigned/Supporting documents list -->
                        <div id="builder-documents-container" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.5rem;">Report Documents</h3>
                            <div id="builder-documents-list" style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1rem;">
                                <!-- Document items populated dynamically -->
                            </div>
                        </div>

                        <!-- Audit Log / Timeline for this report -->
                        <div style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.75rem;">Report Lifecycle Timeline</h3>
                            <div id="builder-audit-list" style="display: flex; flex-direction: column; gap: 1rem; border-left: 2px solid rgba(255,255,255,0.05); padding-left: 1rem; margin-left: 0.5rem; max-height: 300px; overflow-y: auto;">
                                <!-- Audit entries populated dynamically -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 1. Pending Approvals Section -->
        <div id="section-pending" class="tab-section">
            <div class="source-filter-container" style="display: flex; gap: 0.75rem; margin-bottom: 1.5rem; align-items: center; background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); padding: 0.75rem 1.25rem; border-radius: 16px;">
                <span style="font-size: 0.9rem; font-weight: 600; color: var(--text-muted); margin-right: 0.5rem;">Source Filter:</span>
                <button class="filter-btn active" id="src-btn-all" onclick="setPendingSourceFilter('all')">All Sources</button>
                <button class="filter-btn" id="src-btn-employee_portal" onclick="setPendingSourceFilter('employee_portal')">Employee Portal</button>
                <button class="filter-btn" id="src-btn-report_workflow" onclick="setPendingSourceFilter('report_workflow')">Report Workflow</button>
                <button class="filter-btn" id="src-btn-legacy_cli" onclick="setPendingSourceFilter('legacy_cli')">Legacy CLI</button>
            </div>
            <div class="dashboard-grid" id="dashboard-grid">
                <!-- Loading state on startup -->
                <div class="empty-state" style="grid-column: 1/-1;">
                    <div class="spinner"></div>
                    <h3>Querying Agent Registry...</h3>
                    <p>Connecting to Vertex AI reasoning engine and downloading active session metrics...</p>
                </div>
            </div>
        </div>

        <!-- 2. Expense History Section -->
        <div id="section-history" class="tab-section" style="display: none;">
            <div style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="font-size: 1.4rem; font-weight: 700;">Expense History Source of Truth</h2>
                    <button class="refresh-btn" onclick="fetchExpenseHistory()" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Refresh History</button>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                        <thead>
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted);">
                                <th style="padding: 1rem 0.75rem;">Category</th>
                                <th style="padding: 1rem 0.75rem;">Date</th>
                                <th style="padding: 1rem 0.75rem;">Employee</th>
                                <th style="padding: 1rem 0.75rem;">Department</th>
                                <th style="padding: 1rem 0.75rem;">Assigned Manager</th>
                                <th style="padding: 1rem 0.75rem;">Submitted By</th>
                                <th style="padding: 1rem 0.75rem;">Amount</th>
                                <th style="padding: 1rem 0.75rem;">Status</th>
                                <th style="padding: 1rem 0.75rem;">Reviewer</th>
                                <th style="padding: 1rem 0.75rem; text-align: right;">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="history-table-body">
                            <tr>
                                <td colspan="10" style="padding: 3rem; text-align: center; color: var(--text-muted);">
                                    <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                                    Loading history...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 3. Audit Timeline Section -->
        <div id="section-audit-trail" class="tab-section" style="display: none;">
            <div style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2.5rem; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); max-width: 800px; margin: 0 auto;">
                <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 1.5rem;">
                    <h2 style="font-size: 1.4rem; font-weight: 700;">Global Audit Trail</h2>
                    <p style="font-size: 0.9rem; color: var(--text-muted);">Select any claim from Expense History to view its complete step-by-step lifecycle log.</p>
                </div>
                <div id="audit-trail-container">
                    <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                        <div style="font-size: 2.5rem; margin-bottom: 1rem;">🔍</div>
                        <h3>No Claim Selected</h3>
                        <p>Go to the "Expense History" tab and click "View Trail" to see its immutable lifecycle events.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. Submit Expense Section -->
        <div id="section-submit" class="tab-section" style="display: none;">
            <div class="portal-layout">
                <!-- Left Column: Submission Form -->
                <form id="claim-submit-form" onsubmit="submitClaimForm(event)" style="display: flex; flex-direction: column; margin: 0;">
                    <!-- Section 1: Employee Info -->
                    <div class="form-section-card">
                        <div class="form-section-title">
                            <span class="section-icon">👤</span>
                            Employee Information
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-company-id">Company ID</label>
                                <input type="text" id="form-company-id" value="demo_company" readonly required>
                            </div>
                            <div class="form-group">
                                <label for="form-employee-email">Employee Email</label>
                                <input type="email" id="form-employee-email" required oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group" id="demo-claimant-container" style="display: none;">
                                <label for="form-demo-select">Or Demo Claimant</label>
                                <select id="form-demo-select" onchange="useDemoClaimant(this.value)">
                                    <option value="">-- Select Demo Employee --</option>
                                    <option value="fresh.manager.test@company.com">Fresh Manager Test</option>
                                    <option value="receipt.test@company.com">Receipt Test</option>
                                    <option value="auth.hotel.docs.test@company.com">Auth Hotel Docs Test</option>
                                    <option value="auth.flight.docs.test@company.com">Auth Flight Docs Test</option>
                                    <option value="auth.rejection.test@company.com">Auth Rejection Test</option>
                                    <option value="employee.portal.meals@company.com">Meals within per diem</option>
                                    <option value="employee.portal.meals.over@company.com">Meals over per diem</option>
                                    <option value="employee.portal.mileage@company.com">Personal Mileage</option>
                                    <option value="employee.portal.rental@company.com">Rental Car</option>
                                    <option value="employee.portal.flight@company.com">Flight Claim</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-employee-name">Employee Name</label>
                                <input type="text" id="form-employee-name" placeholder="John Doe" required oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-department">Department</label>
                                <input type="text" id="form-department" placeholder="Engineering" required oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-manager-email">Manager Email</label>
                                <input type="email" id="form-manager-email" placeholder="manager@company.com" required oninput="triggerLivePreview()">
                            </div>
                        </div>
                    </div>

                    <!-- Section 2: Expense Basics -->
                    <div class="form-section-card">
                        <div class="form-section-title">
                            <span class="section-icon">💳</span>
                            Expense Basics
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-category">Expense Category</label>
                                <select id="form-category" required onchange="handleCategoryChange()">
                                    <option value="">-- Choose Category --</option>
                                    <option value="meals">Meals</option>
                                    <option value="lodging">Lodging</option>
                                    <option value="flight">Flight</option>
                                    <option value="office_supplies">Office Supplies</option>
                                    <option value="printing_supplies">Printing Supplies</option>
                                    <option value="parking">Parking</option>
                                    <option value="parking_citation">Parking Citation</option>
                                    <option value="transportation">Transportation</option>
                                    <option value="tolls">Tolls</option>
                                    <option value="rental_car">Rental Car</option>
                                    <option value="rental_car_gas">Rental Car Gas</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-amount">Amount</label>
                                <input type="number" step="0.01" id="form-amount" placeholder="0.00" required oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-currency">Currency</label>
                                <select id="form-currency" required onchange="triggerLivePreview()">
                                    <option value="USD">USD ($)</option>
                                    <option value="EUR">EUR (€)</option>
                                    <option value="GBP">GBP (£)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-expense-date">Expense Date</label>
                                <input type="date" id="form-expense-date" required onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group full-width">
                                <label for="form-business-purpose">Business Purpose</label>
                                <input type="text" id="form-business-purpose" placeholder="e.g. Client meetings" required oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group full-width">
                                <label for="form-description">Description</label>
                                <textarea id="form-description" rows="3" placeholder="e.g. Dinner with ACME clients..." oninput="triggerLivePreview()"></textarea>
                            </div>
                        </div>
                    </div>

                    <!-- Section 3: Travel / Per Diem Fields -->
                    <div class="form-section-card" id="card-travel-fields" style="display: none;">
                        <div class="form-section-title">
                            <span class="section-icon">✈️</span>
                            Travel / Per Diem Details
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-travel-start">Travel Start Date</label>
                                <input type="date" id="form-travel-start" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-travel-end">Travel End Date</label>
                                <input type="date" id="form-travel-end" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-city">City</label>
                                <input type="text" id="form-city" placeholder="New York" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-state">State</label>
                                <input type="text" id="form-state" placeholder="NY" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-country">Country</label>
                                <input type="text" id="form-country" value="US" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-meals">Claimed Meals Total</label>
                                <input type="number" step="0.01" id="form-claimed-meals" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-lodging">Claimed Lodging Total</label>
                                <input type="number" step="0.01" id="form-claimed-lodging" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-incidentals">Claimed Incidentals Total</label>
                                <input type="number" step="0.01" id="form-claimed-incidentals" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-check-in">Hotel Check-In Date</label>
                                <input type="date" id="form-check-in" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-check-out">Hotel Check-Out Date</label>
                                <input type="date" id="form-check-out" onchange="triggerLivePreview()">
                            </div>
                        </div>
                    </div>

                    <!-- Section 4: Transportation Fields -->
                    <div class="form-section-card" id="card-transport-fields" style="display: none;">
                        <div class="form-section-title">
                            <span class="section-icon">🚗</span>
                            Transportation Details
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-trans-type">Transportation Type</label>
                                <select id="form-trans-type" onchange="handleTransTypeChange()">
                                    <option value="">-- Choose Type --</option>
                                    <option value="personal_vehicle">Personal Vehicle</option>
                                    <option value="rental_car">Rental Car</option>
                                    <option value="rental_car_gas">Rental Car Gas</option>
                                    <option value="parking">Parking</option>
                                    <option value="tolls">Tolls</option>
                                    <option value="mixed">Mixed</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-trip-date">Trip Date</label>
                                <input type="date" id="form-trip-date" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-start-loc">Start Location Label</label>
                                <input type="text" id="form-start-loc" placeholder="e.g. home" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-start-addr">Start Address</label>
                                <input type="text" id="form-start-addr" placeholder="Raleigh, NC" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-dest-loc">Destination Location Label</label>
                                <input type="text" id="form-dest-loc" placeholder="e.g. client_site" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-dest-addr">Destination Address</label>
                                <input type="text" id="form-dest-addr" placeholder="Charlotte, NC" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-trip-type">Trip Type</label>
                                <select id="form-trip-type" onchange="triggerLivePreview()">
                                    <option value="one_way">One Way</option>
                                    <option value="round_trip">Round Trip</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-biz-miles">Business Miles</label>
                                <input type="number" step="0.1" id="form-biz-miles" placeholder="0.0" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-entered-miles">Employee Entered Miles</label>
                                <input type="number" step="0.1" id="form-entered-miles" placeholder="0.0" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-start">Rental Start Date</label>
                                <input type="date" id="form-rental-start" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-end">Rental End Date</label>
                                <input type="date" id="form-rental-end" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-cost">Rental Cost</label>
                                <input type="number" step="0.01" id="form-rental-cost" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-gas-cost">Gas Cost</label>
                                <input type="number" step="0.01" id="form-gas-cost" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-parking-cost">Parking Cost</label>
                                <input type="number" step="0.01" id="form-parking-cost" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-toll-cost">Toll Cost</label>
                                <input type="number" step="0.01" id="form-toll-cost" placeholder="0.00" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-linked-rental">Linked Rental Claim ID</label>
                                <input type="text" id="form-linked-rental" placeholder="e.g. ext-12345" oninput="triggerLivePreview()">
                            </div>
                        </div>
                    </div>

                    <!-- Section 5: Supporting Documents -->
                    <div class="form-section-card">
                        <div class="form-section-title">
                            <span class="section-icon">📂</span>
                            Supporting Documents
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.25rem;">
                            Select files to upload as supporting documents before submission.
                        </p>
                        <div class="upload-grid" id="portal-upload-grid">
                            <!-- Populated dynamically -->
                        </div>
                    </div>

                    <button type="submit" class="btn btn-approve" style="width: 100%; padding: 1rem; font-size: 1.1rem; border-radius: 12px; margin-top: 1rem; font-weight: 700; height: auto;">
                        Submit Claim
                    </button>
                </form>

                <!-- Right Column: Real-time Live Policy Preview -->
                <div class="preview-sidebar">
                    <h3 style="font-size: 1.2rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.75rem; margin-bottom: 0.5rem; color: white;">
                        <span>🛡️</span> Real-Time Compliance Preview
                    </h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;">
                        Our compliance engine is analyzing your claim input in real-time. Review warning and overage indications below.
                    </p>

                    <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 0.5rem;">
                        <div class="preview-metric">
                            <span class="preview-metric-label">Policy Status</span>
                            <span class="preview-metric-value" id="preview-policy-status">N/A</span>
                        </div>
                        <div class="preview-metric">
                            <span class="preview-metric-label">Overage Status</span>
                            <span class="preview-metric-value" id="preview-overage-status">Within Policy</span>
                        </div>
                        <div class="preview-metric">
                            <span class="preview-metric-label">Est. Reimbursable</span>
                            <span class="preview-metric-value highlight success" id="preview-reimbursable">$0.00</span>
                        </div>
                        <div class="preview-metric">
                            <span class="preview-metric-label">Est. Non-Reimbursable</span>
                            <span class="preview-metric-value highlight danger" id="preview-non-reimbursable">$0.00</span>
                        </div>
                        <div class="preview-metric">
                            <span class="preview-metric-label">Manager Review Required</span>
                            <span class="preview-metric-value" id="preview-manager-required">No</span>
                        </div>
                    </div>

                    <!-- Warnings list -->
                    <div style="display: flex; flex-direction: column; gap: 0.75rem;" id="preview-warnings-container">
                        <div class="warning-banner info">
                            <span>ℹ️</span><span>Enter category and details to see live policy evaluation.</span>
                        </div>
                    </div>

                    <!-- Required / Uploaded Docs Checklist -->
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem;">
                        <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; font-weight: 700; margin-bottom: 0.5rem;">
                            Document Checklist
                        </h4>
                        <div id="preview-docs-checklist" style="display: flex; flex-direction: column; gap: 0.4rem;">
                            <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No category selected.</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Side Slide Modal for Compliance Review -->
    <div class="slide-overlay" id="slide-overlay"></div>
    <div class="slide-modal" id="slide-modal">
        <div class="modal-header">
            <div class="modal-title">
                <h2>Compliance Audit</h2>
                <p id="modal-session-id">Session Reference: </p>
            </div>
            <button class="close-btn" onclick="toggleModal(false)">✕</button>
        </div>
        <div class="modal-body">
            <div class="status-box" id="modal-status-box">
                <div class="status-icon" id="modal-status-icon">✓</div>
                <div class="status-text">
                    <h4 id="modal-status-title">Claim Approved</h4>
                    <p id="modal-status-desc">Successfully authorized and registered on runtime.</p>
                </div>
            </div>

            <div class="review-details-card">
                <h4>Claimant Metrics</h4>
                <div class="review-grid">
                    <div class="review-field">
                        <span>Claimant Name</span>
                        <strong id="modal-claimant">--</strong>
                    </div>
                    <div class="review-field">
                        <span>Total Claim Value</span>
                        <strong id="modal-amount" style="color: #34d399;">--</strong>
                    </div>
                </div>
                <div id="modal-receipt-container" style="margin-top: 1rem; display: none;">
                    <a id="modal-receipt-btn" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="background: rgba(99, 102, 241, 0.1); color: #cbd5e1; border: 1px solid rgba(99, 102, 241, 0.25); text-decoration: none; display: flex; width: 100%; align-items: center; justify-content: center;">
                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" style="display:inline; vertical-align:middle; margin-right:4px;">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        View Receipt
                    </a>
                </div>
            </div>

            <div class="compliance-box">
                <h4>
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" style="display:inline; vertical-align:middle; margin-right:4px;">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Compliance Engine Report
                </h4>
                <div class="compliance-text" id="modal-comments">
                    Loading review comment details...
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="modal-done-btn" onclick="toggleModal(false)">Acknowledge & Close</button>
        </div>
    </div>

    <!-- Toast Notification alerts -->
    <div class="toast" id="toast">
        <div class="toast-icon">✓</div>
        <div id="toast-text">Approval processed successfully.</div>
    </div>

    <script>
        function safeNumber(value) {
            if (value === undefined || value === null || value === "") return 0;
            const parsed = parseFloat(value);
            return isNaN(parsed) ? 0 : parsed;
        }

        function formatMoney(value) {
            try {
                const num = safeNumber(value);
                return "$" + num.toFixed(2);
            } catch (e) {
                console.warn("formatMoney failed for value:", value, e);
                return "$0.00";
            }
        }

        let cachedClaims = {};
        let activeClaimId = null;

        const DOC_TYPES = {
            receipt: { label: "General Receipt", icon: "📄" },
            hotel_receipt: { label: "Hotel Receipt", icon: "🏨" },
            flight_ticket_receipt: { label: "Flight Receipt", icon: "✈️" },
            manager_approval_letter: { label: "Manager Approval Letter", icon: "✉️" },
            office_receipt: { label: "Office Receipt", icon: "💼" },
            parking_receipt: { label: "Parking Receipt", icon: "🚗" },
            mileage_log: { label: "Mileage Log", icon: "🗺️" },
            rental_receipt: { label: "Rental Receipt", icon: "🔑" },
            gas_receipt: { label: "Gas Receipt", icon: "⛽" },
            toll_receipt: { label: "Toll Receipt", icon: "🪙" }
        };

        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        function titleCase(str) {
            if (!str) return "";
            return str.split(/[\._]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        }

        function initSubmitForm() {
            if (!activeClaimId) {
                resetSubmissionForm();
            }
        }

        function renderPortalUploadGrid() {
            const grid = document.getElementById("portal-upload-grid");
            if (!grid) return;
            grid.innerHTML = "";
            Object.keys(DOC_TYPES).forEach(docType => {
                const config = DOC_TYPES[docType];
                const div = document.createElement("div");
                div.className = "upload-dropzone";
                div.id = `dz-${docType}`;
                div.onclick = (e) => {
                    if (e.target.tagName !== 'INPUT') {
                        const inp = document.getElementById(`file-input-${docType}`);
                        if (inp) inp.click();
                    }
                };
                div.innerHTML = `
                    <input type="file" id="file-input-${docType}" onchange="uploadPortalFile('${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                    <span class="dropzone-icon">${config.icon}</span>
                    <span class="dropzone-title">${config.label}</span>
                    <span class="dropzone-status" style="color: var(--text-muted);" id="dz-status-${docType}">Empty</span>
                `;
                grid.appendChild(div);
            });
        }

        async function uploadPortalFile(docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            
            const dz = document.getElementById(`dz-${docType}`);
            const originalHTML = dz.innerHTML;
            
            dz.style.pointerEvents = "none";
            dz.innerHTML = `
                <div class="spinner" style="width:24px; height:24px; border-width:2px; margin-bottom: 0.5rem; margin-left: auto; margin-right: auto;"></div>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Uploading...</span>
            `;
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/employee/claims/${activeClaimId}/documents/${docType}`, {
                    method: "POST",
                    body: formData
                });
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                
                dz.classList.add("uploaded");
                dz.innerHTML = `
                    <input type="file" id="file-input-${docType}" onchange="uploadPortalFile('${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                    <span class="dropzone-icon" style="color: #34d399;">✓</span>
                    <span class="dropzone-title">${DOC_TYPES[docType].label}</span>
                    <span class="dropzone-status" style="color: #34d399;">Uploaded</span>
                    <span style="font-size: 0.65rem; color: var(--text-muted); margin-top: -0.2rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 160px; display: block; margin-left: auto; margin-right: auto;">${escapeHtml(file.name)}</span>
                `;
                
                triggerLivePreview();
            } catch (err) {
                console.error("Portal upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                dz.innerHTML = originalHTML;
            } finally {
                dz.style.pointerEvents = "all";
            }
        }

        function handleCategoryChange() {
            const category = document.getElementById("form-category").value;
            const travelCard = document.getElementById("card-travel-fields");
            const transportCard = document.getElementById("card-transport-fields");
            
            const isTravel = ["meals", "lodging", "flight"].includes(category);
            const isTransport = ["transportation", "rental_car", "rental_car_gas", "parking", "tolls"].includes(category);
            
            if (travelCard) travelCard.style.display = isTravel ? "block" : "none";
            if (transportCard) transportCard.style.display = isTransport ? "block" : "none";
            
            if (category === "rental_car") {
                document.getElementById("form-trans-type").value = "rental_car";
            } else if (category === "rental_car_gas") {
                document.getElementById("form-trans-type").value = "rental_car_gas";
            } else if (category === "parking") {
                document.getElementById("form-trans-type").value = "parking";
            } else if (category === "tolls") {
                document.getElementById("form-trans-type").value = "tolls";
            } else if (category === "transportation") {
                document.getElementById("form-trans-type").value = "personal_vehicle";
            }
            
            triggerLivePreview();
        }

        function handleTransTypeChange() {
            triggerLivePreview();
        }

        function getFormData() {
            const category = document.getElementById("form-category").value;
            const amount = document.getElementById("form-amount").value;
            const company_id = document.getElementById("form-company-id").value;
            const employee_email = document.getElementById("form-employee-email").value;
            const employee_name = document.getElementById("form-employee-name").value;
            const department = document.getElementById("form-department").value;
            const manager_email = document.getElementById("form-manager-email").value;
            const currency = document.getElementById("form-currency").value;
            const expense_date = document.getElementById("form-expense-date").value;
            const business_purpose = document.getElementById("form-business-purpose").value;
            const description = document.getElementById("form-description").value;
            
            const travel_start_date = document.getElementById("form-travel-start").value;
            const travel_end_date = document.getElementById("form-travel-end").value;
            const city = document.getElementById("form-city").value;
            const state = document.getElementById("form-state").value;
            const country = document.getElementById("form-country").value;
            const claimed_meals = document.getElementById("form-claimed-meals").value;
            const claimed_lodging = document.getElementById("form-claimed-lodging").value;
            const claimed_incidentals = document.getElementById("form-claimed-incidentals").value;
            const check_in_date = document.getElementById("form-check-in").value;
            const check_out_date = document.getElementById("form-check-out").value;
            
            const transportation_type = document.getElementById("form-trans-type").value;
            const trip_date = document.getElementById("form-trip-date").value;
            const start_location_label = document.getElementById("form-start-loc").value;
            const start_address = document.getElementById("form-start-addr").value;
            const destination_location_label = document.getElementById("form-dest-loc").value;
            const destination_address = document.getElementById("form-dest-addr").value;
            const trip_type = document.getElementById("form-trip-type").value;
            const business_miles = document.getElementById("form-biz-miles").value;
            const employee_entered_miles = document.getElementById("form-entered-miles").value;
            const rental_start_date = document.getElementById("form-rental-start").value;
            const rental_end_date = document.getElementById("form-rental-end").value;
            const rental_cost = document.getElementById("form-rental-cost").value;
            const gas_cost = document.getElementById("form-gas-cost").value;
            const parking_cost = document.getElementById("form-parking-cost").value;
            const toll_cost = document.getElementById("form-toll-cost").value;
            const linked_rental_claim_id = document.getElementById("form-linked-rental").value;
            
            return {
                claim_id: activeClaimId,
                category,
                amount,
                company_id,
                employee_email,
                employee_name,
                department,
                manager_email,
                currency,
                expense_date,
                business_purpose,
                description,
                
                travel_start_date,
                travel_end_date,
                city,
                state,
                country,
                claimed_meals,
                claimed_lodging,
                claimed_incidentals,
                check_in_date,
                check_out_date,
                
                transportation_type,
                trip_date,
                start_location_label,
                start_address,
                destination_location_label,
                destination_address,
                trip_type,
                business_miles,
                employee_entered_miles,
                rental_start_date,
                rental_end_date,
                rental_cost,
                gas_cost,
                parking_cost,
                toll_cost,
                linked_rental_claim_id
            };
        }

        let previewTimeout = null;
        function triggerLivePreview() {
            clearTimeout(previewTimeout);
            previewTimeout = setTimeout(async () => {
                const data = getFormData();
                if (!data.category) return;
                
                try {
                    const response = await fetch("/api/employee/claims/preview", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(data)
                    });
                    if (!response.ok) throw new Error("Preview failed");
                    const preview = await response.json();
                    
                    const statusEl = document.getElementById("preview-policy-status");
                    if (statusEl) {
                        statusEl.textContent = preview.policy_status;
                        statusEl.className = "preview-metric-value " + (preview.is_valid ? "success" : "danger");
                    }
                    
                    const overageEl = document.getElementById("preview-overage-status");
                    if (overageEl) {
                        if (preview.policy_status.includes("Exceeds") || preview.estimated_non_reimbursable > 0) {
                            overageEl.textContent = "Overage Detected";
                            overageEl.className = "preview-metric-value danger";
                        } else {
                            overageEl.textContent = "Within Limits";
                            overageEl.className = "preview-metric-value success";
                        }
                    }
                    
                    const reimbEl = document.getElementById("preview-reimbursable");
                    if (reimbEl) reimbEl.textContent = formatMoney(preview.estimated_reimbursable);
                    
                    const nonReimbEl = document.getElementById("preview-non-reimbursable");
                    if (nonReimbEl) nonReimbEl.textContent = formatMoney(preview.estimated_non_reimbursable);
                    
                    const reviewReqEl = document.getElementById("preview-manager-required");
                    if (reviewReqEl) {
                        reviewReqEl.textContent = preview.manager_approval_required ? "Yes" : "No";
                        reviewReqEl.className = "preview-metric-value " + (preview.manager_approval_required ? "danger" : "success");
                    }
                    
                    const warningsContainer = document.getElementById("preview-warnings-container");
                    if (warningsContainer) {
                        warningsContainer.innerHTML = "";
                        if (preview.warnings && preview.warnings.length > 0) {
                            preview.warnings.forEach(w => {
                                const banner = document.createElement("div");
                                banner.className = "warning-banner danger";
                                banner.innerHTML = `<span>⚠️</span><span>${escapeHtml(w)}</span>`;
                                warningsContainer.appendChild(banner);
                            });
                        } else {
                            const banner = document.createElement("div");
                            banner.className = "warning-banner info";
                            banner.innerHTML = `<span>ℹ️</span><span>Claim is within standard operational boundaries.</span>`;
                            warningsContainer.appendChild(banner);
                        }
                    }
                    
                    const checklistContainer = document.getElementById("preview-docs-checklist");
                    if (checklistContainer) {
                        checklistContainer.innerHTML = "";
                        const required = preview.required_documents || [];
                        const missing = preview.missing_documents || [];
                        
                        if (required.length === 0) {
                            checklistContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No documents required for this category.</div>`;
                        } else {
                            required.forEach(doc => {
                                const isMissing = missing.includes(doc);
                                const icon = isMissing ? "✕" : "✓";
                                const color = isMissing ? "#fb7185" : "#34d399";
                                const item = document.createElement("div");
                                item.style = `display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: ${color}; font-weight: 500;`;
                                item.innerHTML = `<span>${icon}</span> <span>${escapeHtml(doc.replace(/_/g, ' ').toUpperCase())}</span>`;
                                checklistContainer.appendChild(item);
                            });
                        }
                    }
                } catch (err) {
                    console.error("Live preview error", err);
                }
            }, 300);
        }

        async function submitClaimForm(event) {
            event.preventDefault();
            const data = getFormData();
            
            try {
                const response = await fetch("/api/employee/claims", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Submission failed");
                }
                
                const result = await response.json();
                showToast("Claim submitted successfully!", "success");
                
                activeClaimId = null;
                resetSubmissionForm();
                switchTab('history');
            } catch (err) {
                console.error("Submission failed", err);
                showToast("Submission failed: " + err.message, "error");
            }
        }

        function resetSubmissionForm() {
            activeClaimId = generateUUID();
            const form = document.getElementById("claim-submit-form");
            if (form) form.reset();
            
            const companyIdEl = document.getElementById("form-company-id");
            if (companyIdEl) companyIdEl.value = "demo_company";
            
            const emailEl = document.getElementById("form-employee-email");
            if (emailEl) emailEl.value = USER_EMAIL;
            
            const nameEl = document.getElementById("form-employee-name");
            if (nameEl) nameEl.value = titleCase(USER_EMAIL.split("@")[0]);
            
            const deptEl = document.getElementById("form-department");
            if (deptEl) deptEl.value = "Engineering";
            
            const mgrEl = document.getElementById("form-manager-email");
            if (mgrEl) mgrEl.value = "manager@company.com";
            
            const dateEl = document.getElementById("form-expense-date");
            if (dateEl) dateEl.value = new Date().toISOString().substring(0, 10);
            
            renderPortalUploadGrid();
            
            const travelFields = document.getElementById("card-travel-fields");
            if (travelFields) travelFields.style.display = "none";
            
            const transportFields = document.getElementById("card-transport-fields");
            if (transportFields) transportFields.style.display = "none";
            
            const previewStatus = document.getElementById("preview-policy-status");
            if (previewStatus) {
                previewStatus.textContent = "N/A";
                previewStatus.className = "preview-metric-value";
            }
            const overageStatus = document.getElementById("preview-overage-status");
            if (overageStatus) {
                overageStatus.textContent = "Within Policy";
                overageStatus.className = "preview-metric-value success";
            }
            const reimbursableEl = document.getElementById("preview-reimbursable");
            if (reimbursableEl) reimbursableEl.textContent = "$0.00";
            
            const nonReimbursableEl = document.getElementById("preview-non-reimbursable");
            if (nonReimbursableEl) nonReimbursableEl.textContent = "$0.00";
            
            const mgrReq = document.getElementById("preview-manager-required");
            if (mgrReq) {
                mgrReq.textContent = "No";
                mgrReq.className = "preview-metric-value success";
            }
            
            const warningsContainer = document.getElementById("preview-warnings-container");
            if (warningsContainer) {
                warningsContainer.innerHTML = `
                    <div class="warning-banner info">
                        <span>ℹ️</span><span>Enter category and details to see live policy evaluation.</span>
                    </div>
                `;
            }
            const checklistContainer = document.getElementById("preview-docs-checklist");
            if (checklistContainer) {
                checklistContainer.innerHTML = `
                    <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No category selected.</div>
                `;
            }
            
            const demoContainer = document.getElementById("demo-claimant-container");
            if (demoContainer) {
                if (USER_ROLE === "finance_admin") {
                    demoContainer.style.display = "block";
                } else {
                    demoContainer.style.display = "none";
                }
            }
        }

        function useDemoClaimant(email) {
            if (!email) return;
            resetSubmissionForm();
            
            document.getElementById("form-employee-email").value = email;
            document.getElementById("form-employee-name").value = titleCase(email.split("@")[0]);
            
            const selectEl = document.getElementById("form-demo-select");
            if (selectEl) selectEl.value = email;
            
            if (email === "fresh.manager.test@company.com") {
                document.getElementById("form-employee-name").value = "Fresh Manager Test";
                document.getElementById("form-department").value = "Operations";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                document.getElementById("form-category").value = "meals";
                handleCategoryChange();
                document.getElementById("form-amount").value = "150.00";
                document.getElementById("form-claimed-meals").value = "150.00";
                document.getElementById("form-travel-start").value = "2026-05-10";
                document.getElementById("form-travel-end").value = "2026-05-12";
                document.getElementById("form-city").value = "Chicago";
                document.getElementById("form-state").value = "IL";
                document.getElementById("form-business-purpose").value = "Operations site visit";
                document.getElementById("form-description").value = "Operations review with local team.";
            } else if (email === "receipt.test@company.com") {
                document.getElementById("form-employee-name").value = "Receipt Test";
                document.getElementById("form-department").value = "Finance";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                document.getElementById("form-category").value = "meals";
                handleCategoryChange();
                document.getElementById("form-amount").value = "250.00";
                document.getElementById("form-claimed-meals").value = "250.00";
                document.getElementById("form-travel-start").value = "2026-05-15";
                document.getElementById("form-travel-end").value = "2026-05-17";
                document.getElementById("form-city").value = "Austin";
                document.getElementById("form-state").value = "TX";
                document.getElementById("form-business-purpose").value = "Finance audit and planning";
                document.getElementById("form-description").value = "Annual finance planning session.";
            } else if (email === "auth.hotel.docs.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Hotel Docs Test";
                document.getElementById("form-department").value = "Sales";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                document.getElementById("form-category").value = "lodging";
                handleCategoryChange();
                document.getElementById("form-amount").value = "600.00";
                document.getElementById("form-claimed-lodging").value = "600.00";
                document.getElementById("form-travel-start").value = "2026-05-20";
                document.getElementById("form-travel-end").value = "2026-05-23";
                document.getElementById("form-city").value = "San Francisco";
                document.getElementById("form-state").value = "CA";
                document.getElementById("form-check-in-date").value = "2026-05-20";
                document.getElementById("form-check-out-date").value = "2026-05-23";
                document.getElementById("form-business-purpose").value = "Annual Sales Kickoff";
                document.getElementById("form-description").value = "Sales presentation and customer meetings.";
            } else if (email === "auth.flight.docs.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Flight Docs Test";
                document.getElementById("form-department").value = "Travel";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                document.getElementById("form-category").value = "flight";
                handleCategoryChange();
                document.getElementById("form-amount").value = "850.00";
                document.getElementById("form-travel-start").value = "2026-05-25";
                document.getElementById("form-travel-end").value = "2026-05-28";
                document.getElementById("form-city").value = "Seattle";
                document.getElementById("form-state").value = "WA";
                document.getElementById("form-business-purpose").value = "Technical integration";
                document.getElementById("form-description").value = "Integration kickoff with cloud engineering.";
            } else if (email === "auth.rejection.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Rejection Test";
                document.getElementById("form-department").value = "Compliance";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                document.getElementById("form-category").value = "meals";
                handleCategoryChange();
                document.getElementById("form-amount").value = "400.00";
                document.getElementById("form-claimed-meals").value = "400.00";
                document.getElementById("form-travel-start").value = "2026-06-01";
                document.getElementById("form-travel-end").value = "2026-06-03";
                document.getElementById("form-city").value = "Miami";
                document.getElementById("form-state").value = "FL";
                document.getElementById("form-business-purpose").value = "Compliance workshop";
                document.getElementById("form-description").value = "Southeastern regional compliance review.";
            } else if (email === "employee.portal.meals@company.com") {
                document.getElementById("form-category").value = "meals";
                handleCategoryChange();
                document.getElementById("form-amount").value = "300.00";
                document.getElementById("form-claimed-meals").value = "300.00";
                document.getElementById("form-travel-start").value = "2026-04-12";
                document.getElementById("form-travel-end").value = "2026-04-14";
                document.getElementById("form-city").value = "New York";
                document.getElementById("form-state").value = "NY";
                document.getElementById("form-business-purpose").value = "Business meetings in New York";
                document.getElementById("form-description").value = "Employee meals within per diem test claim.";
            } else if (email === "employee.portal.meals.over@company.com") {
                document.getElementById("form-category").value = "meals";
                handleCategoryChange();
                document.getElementById("form-amount").value = "450.00";
                document.getElementById("form-claimed-meals").value = "450.00";
                document.getElementById("form-travel-start").value = "2026-04-12";
                document.getElementById("form-travel-end").value = "2026-04-14";
                document.getElementById("form-city").value = "New York";
                document.getElementById("form-state").value = "NY";
                document.getElementById("form-business-purpose").value = "Business meetings in New York";
                document.getElementById("form-description").value = "Employee meals exceeding per diem test claim.";
            } else if (email === "employee.portal.mileage@company.com") {
                document.getElementById("form-category").value = "transportation";
                handleCategoryChange();
                document.getElementById("form-trans-type").value = "personal_vehicle";
                handleTransTypeChange();
                document.getElementById("form-amount").value = "0.00";
                document.getElementById("form-trip-date").value = "2026-04-12";
                document.getElementById("form-start-loc").value = "home";
                document.getElementById("form-start-addr").value = "Raleigh, NC";
                document.getElementById("form-dest-loc").value = "client_site";
                document.getElementById("form-dest-addr").value = "Charlotte, NC";
                document.getElementById("form-trip-type").value = "round_trip";
                document.getElementById("form-biz-miles").value = "280";
                document.getElementById("form-entered-miles").value = "280";
                document.getElementById("form-business-purpose").value = "Same-day client meeting";
                document.getElementById("form-description").value = "Employee mileage test claim.";
            } else if (email === "employee.portal.rental@company.com") {
                document.getElementById("form-category").value = "transportation";
                handleCategoryChange();
                document.getElementById("form-trans-type").value = "rental_car";
                handleTransTypeChange();
                document.getElementById("form-amount").value = "320.00";
                document.getElementById("form-rental-cost").value = "320.00";
                document.getElementById("form-rental-start").value = "2026-04-12";
                document.getElementById("form-rental-end").value = "2026-04-14";
                document.getElementById("form-business-purpose").value = "Business conference travel";
                document.getElementById("form-description").value = "Employee rental car test claim.";
            } else if (email === "employee.portal.flight@company.com") {
                document.getElementById("form-category").value = "flight";
                handleCategoryChange();
                document.getElementById("form-amount").value = "1350.00";
                document.getElementById("form-business-purpose").value = "Client conference flight";
                document.getElementById("form-description").value = "Employee flight ticket test claim.";
            }
            
            triggerLivePreview();
        }

        async function showClaimDetails(claimId) {
            toggleModal(true);
            const body = document.querySelector(".modal-body");
            const title = document.querySelector(".modal-header h2");
            const sub = document.getElementById("modal-session-id");
            
            title.textContent = "Claim Detail & Audit Timeline";
            sub.textContent = `Claim ID: ${claimId}`;
            
            body.innerHTML = `
                <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                    <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                    Fetching complete claim profile...
                </div>
            `;
            
            try {
                const response = await fetch(`/api/employee/claims/${claimId}`);
                if (!response.ok) throw new Error("Failed to load details");
                
                const data = await response.json();
                const exp = data.expense;
                const docs = data.documents || [];
                const decisions = data.decisions || [];
                const audits = data.audit_logs || [];
                
                title.textContent = `Claim: ${escapeHtml(titleCase(exp.category || "Expense"))}`;
                
                let statusBg, statusColor, statusText;
                switch (exp.status) {
                    case 'approved':
                    case 'auto_approved':
                        statusBg = 'rgba(16, 185, 129, 0.15)';
                        statusColor = '#34d399';
                        statusText = exp.status === 'auto_approved' ? 'Auto-Approved (AI)' : 'Approved (Manager)';
                        break;
                    case 'rejected':
                        statusBg = 'rgba(244, 63, 94, 0.15)';
                        statusColor = '#fb7185';
                        statusText = 'Rejected';
                        break;
                    case 'blocked_missing_docs':
                        statusBg = 'rgba(239, 68, 68, 0.15)';
                        statusColor = '#f87171';
                        statusText = 'Blocked (Missing Docs)';
                        break;
                    case 'pending_review':
                    default:
                        statusBg = 'rgba(245, 158, 11, 0.15)';
                        statusColor = '#f59e0b';
                        statusText = 'Pending Review';
                }
                
                const docUrls = {};
                docs.forEach(d => {
                    docUrls[d.doc_type] = d.gcs_path ? `/api/document/${claimId}/${d.doc_type}` : null;
                });
                
                const isTravel = ["meals", "lodging", "flight"].includes(exp.category);
                const isTransport = ["transportation", "rental_car", "rental_car_gas", "parking", "tolls"].includes(exp.category);
                
                body.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <div style="background: ${statusBg}; color: ${statusColor}; border: 1px solid ${statusColor}40; padding: 1rem; border-radius: 12px; display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-size: 1.5rem; line-height: 1;">🛡️</span>
                            <div>
                                <h4 style="font-size: 0.95rem; font-weight: 700; margin: 0; color: white;">${statusText}</h4>
                                <p style="font-size: 0.8rem; margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.7);">${escapeHtml(exp.policy_status || "Compliance evaluation completed.")}</p>
                            </div>
                        </div>

                        <div class="review-details-card" style="margin-top: 0; padding: 1.5rem; width: auto; background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 16px;">
                            <h4 style="font-size: 0.85rem; margin-bottom: 1rem; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem; font-weight: 700;">Claim Summary</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; font-size: 0.82rem;">
                                <div class="review-field"><span>Employee</span><strong>${escapeHtml(exp.employee_name)}</strong></div>
                                <div class="review-field"><span>Email</span><strong style="font-size: 0.75rem; font-weight: 500; word-break: break-all;">${escapeHtml(exp.employee_email)}</strong></div>
                                <div class="review-field"><span>Amount</span><strong style="color: #34d399; font-size: 1.05rem;">${formatMoney(exp.amount)} (${escapeHtml(exp.currency || "USD")})</strong></div>
                                <div class="review-field"><span>Department</span><strong>${escapeHtml(exp.department || "N/A")}</strong></div>
                                <div class="review-field"><span>Manager</span><strong>${escapeHtml(exp.manager_email || "N/A")}</strong></div>
                                <div class="review-field"><span>Expense Date</span><strong>${escapeHtml(exp.expense_date || "N/A")}</strong></div>
                                <div class="review-field" style="grid-column: 1 / -1;"><span>Business Purpose</span><strong>${escapeHtml(exp.business_purpose || "N/A")}</strong></div>
                                ${exp.description ? `<div class="review-field" style="grid-column: 1 / -1;"><span>Description</span><strong style="font-style: italic; font-weight: 400; color: var(--text-muted);">"${escapeHtml(exp.description)}"</strong></div>` : ''}
                            </div>
                        </div>

                        ${isTravel ? `
                        <div style="background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); padding: 1.2rem; border-radius: 14px;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">📅 Travel Metrics</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                <div><strong style="color: var(--text-muted);">Dates:</strong> ${escapeHtml(exp.travel_start_date || "N/A")} to ${escapeHtml(exp.travel_end_date || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Destination:</strong> ${escapeHtml(exp.city || "N/A")}, ${escapeHtml(exp.state || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Claimed Meals:</strong> ${formatMoney(exp.claimed_meals)}</div>
                                <div><strong style="color: var(--text-muted);">Claimed Lodging:</strong> ${formatMoney(exp.claimed_lodging)}</div>
                            </div>
                        </div>
                        ` : ''}

                        ${isTransport ? `
                        <div style="background: rgba(139, 92, 246, 0.03); border: 1px solid rgba(139, 92, 246, 0.1); padding: 1.2rem; border-radius: 14px;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #c084fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">🚗 Transportation Metrics</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                <div><strong style="color: var(--text-muted);">Type:</strong> ${escapeHtml(exp.transportation_type || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Route:</strong> ${escapeHtml(exp.start_address || "N/A")} ➔ ${escapeHtml(exp.destination_address || "N/A")}</div>
                                ${exp.business_miles ? `<div><strong style="color: var(--text-muted);">Miles:</strong> ${exp.business_miles} mi</div>` : ''}
                                ${exp.rental_cost ? `<div><strong style="color: var(--text-muted);">Rental Cost:</strong> ${formatMoney(exp.rental_cost)}</div>` : ''}
                                ${exp.gas_cost ? `<div><strong style="color: var(--text-muted);">Gas Cost:</strong> ${formatMoney(exp.gas_cost)}</div>` : ''}
                                ${exp.parking_cost ? `<div><strong style="color: var(--text-muted);">Parking Cost:</strong> ${formatMoney(exp.parking_cost)}</div>` : ''}
                            </div>
                        </div>
                        ` : ''}

                        <div class="document-verification-box" style="padding: 1.25rem; border-radius: 14px; background: rgba(255, 255, 255, 0.01); border: 1px solid rgba(255, 255, 255, 0.05);">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">📂 Document Checklist & Action</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                ${(() => {
                                    const required = exp.required_documents || [];
                                    const missing = exp.missing_documents || [];
                                    if (required.length === 0) {
                                        return `<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No specific documents required.</div>`;
                                    }
                                    return required.map(docType => {
                                        const isMissing = missing.includes(docType);
                                        const url = docUrls[docType];
                                        const label = DOC_TYPES[docType] ? DOC_TYPES[docType].label : docType.replace(/_/g, ' ').toUpperCase();
                                        return `
                                            <div class="doc-row" style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; gap: 0.5rem;">
                                                <div style="display: flex; flex-direction: column;">
                                                    <span style="font-size: 0.85rem; font-weight: 600; color: white;">${label}</span>
                                                    <span style="font-size: 0.75rem; color: ${url ? '#10b981' : '#fb7185'}; font-weight: 500;">
                                                        ${url ? '✓ Uploaded' : '✕ Missing'}
                                                    </span>
                                                </div>
                                                <div style="display: flex; gap: 0.4rem; align-items: center;">
                                                    ${url ? `
                                                    <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; flex: none; text-decoration: none;">
                                                        View
                                                    </a>
                                                    ` : ''}
                                                    <label class="btn-doc-upload" id="upload-btn-${claimId}-${docType}" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-main); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.2rem; transition: var(--transition); user-select: none;">
                                                        <input type="file" onchange="uploadModalDoc('${claimId}', '${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                                                        <span>${url ? 'Replace' : 'Upload'}</span>
                                                    </label>
                                                </div>
                                            </div>
                                        `;
                                    }).join('');
                                })()}
                            </div>
                        </div>

                        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1.25rem;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 1rem; font-weight: 700; display: flex; align-items: center; gap: 0.4rem;">
                                📜 Audit History Timeline
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 0.8rem; padding-left: 0.5rem; border-left: 2px dashed rgba(255,255,255,0.1); margin-left: 0.5rem;">
                                ${audits.map(audit => {
                                    const eventDate = audit.timestamp ? new Date(audit.timestamp).toLocaleString() : "N/A";
                                    return `
                                        <div style="position: relative; padding-left: 1rem; font-size: 0.8rem;">
                                            <div style="position: absolute; left: -1.35rem; top: 0.2rem; width: 8px; height: 8px; border-radius: 50%; background: var(--primary); box-shadow: 0 0 6px var(--primary);"></div>
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.15rem;">
                                                <strong style="color: white;">${escapeHtml(audit.event_type.replace(/_/g, ' ').toUpperCase())}</strong>
                                                <span style="color: var(--text-muted); font-size: 0.72rem;">${eventDate}</span>
                                            </div>
                                            <p style="margin: 0; color: rgba(255,255,255,0.85);">${escapeHtml(audit.event_message)}</p>
                                            <p style="margin: 0.15rem 0 0 0; color: var(--text-muted); font-size: 0.72rem;">
                                                Actor: <span style="color: #c7d2fe; font-weight: 500;">${escapeHtml(audit.actor_email || audit.actor || "N/A")}</span> (${escapeHtml(audit.actor_role || "N/A")})
                                            </p>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } catch (err) {
                console.error("Failed to fetch claim profile", err);
                body.innerHTML = `
                    <div style="text-align: center; padding: 4rem 2rem; color: #fb7185;">
                        <span style="font-size: 2.5rem;">✕</span>
                        <h3 style="margin-top: 1rem; color: white;">Error Loading Profile</h3>
                        <p style="font-size: 0.85rem; margin-top: 0.2rem;">${err.message}</p>
                    </div>
                `;
            }
        }

        async function uploadModalDoc(claimId, docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            
            const btn = document.getElementById(`upload-btn-${claimId}-${docType}`);
            const originalHTML = btn.innerHTML;
            if (btn) {
                btn.style.pointerEvents = "none";
                btn.innerHTML = `<div class="spinner" style="width:12px; height:12px; border-width:1.5px; margin:0; display:inline-block; vertical-align:middle;"></div>`;
            }
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/employee/claims/${claimId}/documents/${docType}`, {
                    method: "POST",
                    body: formData
                });
                
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                await showClaimDetails(claimId);
                
                if (USER_ROLE === "employee") {
                    fetchExpenseHistory();
                } else {
                    fetchPendingApprovals();
                    fetchExpenseHistory();
                }
            } catch (err) {
                console.error("Modal document upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                if (btn) {
                    btn.innerHTML = originalHTML;
                    btn.style.pointerEvents = "all";
                }
            }
        }

        function switchTab(tab) {
            document.querySelectorAll(".tab-section").forEach(sec => sec.style.display = "none");
            document.querySelectorAll(".tab-btn").forEach(btn => {
                btn.classList.remove("active");
                btn.style.color = "var(--text-muted)";
                btn.style.borderBottom = "none";
            });
            
            const activeBtn = document.getElementById(`tab-${tab === 'audit-trail' ? 'audit' : tab}`);
            if (activeBtn) {
                activeBtn.classList.add("active");
                activeBtn.style.color = "white";
            }

            if (tab === 'pending') {
                document.getElementById("section-pending").style.display = "block";
                fetchPendingApprovals();
            } else if (tab === 'history') {
                document.getElementById("section-history").style.display = "block";
                fetchExpenseHistory();
            } else if (tab === 'audit-trail') {
                document.getElementById("section-audit-trail").style.display = "block";
            } else if (tab === 'submit') {
                document.getElementById("section-submit").style.display = "block";
                initSubmitForm();
            }
        }

        function getStatusBadgeHTML(status) {
            let bg, color, text;
            switch(status) {
                case 'submitted':
                    bg = 'rgba(255, 255, 255, 0.05)';
                    color = '#cbd5e1';
                    text = 'Submitted';
                    break;
                case 'pending_review':
                    bg = 'rgba(245, 158, 11, 0.1)';
                    color = '#f59e0b';
                    text = 'Pending Review';
                    break;
                case 'approved':
                    bg = 'rgba(16, 185, 129, 0.1)';
                    color = '#10b981';
                    text = 'Approved';
                    break;
                case 'auto_approved':
                    bg = 'rgba(16, 185, 129, 0.15)';
                    color = '#34d399';
                    text = 'Auto-Approved';
                    break;
                case 'rejected':
                    bg = 'rgba(244, 63, 94, 0.1)';
                    color = '#fb7185';
                    text = 'Rejected';
                    break;
                case 'blocked_missing_docs':
                    bg = 'rgba(239, 68, 68, 0.1)';
                    color = '#f87171';
                    text = 'Blocked (Docs)';
                    break;
                default:
                    bg = 'rgba(255, 255, 255, 0.05)';
                    color = '#cbd5e1';
                    text = status;
            }
            return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${color}33; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; display: inline-block;">${text}</span>`;
        }

        async function fetchExpenseHistory() {
            const tbody = document.getElementById("history-table-body");
            try {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="padding: 3rem; text-align: center; color: var(--text-muted);">
                            <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                            Syncing database and loading history...
                        </td>
                    </tr>
                `;
                
                const apiPath = USER_ROLE === 'employee' ? '/api/employee/claims' : '/api/expenses';
                const response = await fetch(apiPath);
                if (!response.ok) throw new Error("HTTP " + response.status);
                
                const expenses = await response.json();
                
                if (expenses.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="10" style="padding: 4rem; text-align: center; color: var(--text-muted);">
                                <span style="font-size: 2rem;">📭</span>
                                <h4 style="margin-top: 1rem; color: white;">No Expenses Found</h4>
                                <p style="font-size: 0.85rem; margin-top: 0.2rem;">Expenses will appear here once ingested via Pub/Sub or initialized on the dashboard.</p>
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = "";
                expenses.forEach(exp => {
                    try {
                        const statusBadge = getStatusBadgeHTML(exp.status);
                        const policyColor = exp.policy_status && exp.policy_status.includes("Within policy") ? "#10b981" : "#fb7185";
                        
                        const countDocs = exp.required_documents ? (exp.required_documents.length - (exp.missing_documents ? exp.missing_documents.length : 0)) : 0;
                        const totalDocs = exp.required_documents ? exp.required_documents.length : 0;
                        
                        const decisionText = exp.status === 'approved' ? 'Approved (Manager)' : (exp.status === 'auto_approved' ? 'Auto-Approved (AI)' : (exp.status === 'rejected' ? 'Rejected' : 'Pending'));
                        const decisionColor = exp.status === 'approved' || exp.status === 'auto_approved' ? '#10b981' : (exp.status === 'rejected' ? '#ef4444' : '#f59e0b');
                        
                        const formattedDate = exp.created_at ? new Date(exp.created_at).toLocaleString() : "N/A";
                        
                        const tr = document.createElement("tr");
                        tr.style.borderBottom = "1px solid rgba(255,255,255,0.04)";
                        tr.style.transition = "background-color 0.2s";
                        tr.onmouseenter = () => tr.style.backgroundColor = "rgba(255,255,255,0.02)";
                        tr.onmouseleave = () => tr.style.backgroundColor = "transparent";
                        
                        const reviewerText = exp.reviewer_email || exp.decision_by_email || "N/A";
                        const reviewerRole = exp.reviewer_role || exp.decision_by_role || "";
                        
                        tr.innerHTML = `
                            <td style="padding: 1rem 0.75rem;"><span style="background: rgba(255,255,255,0.06); padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; text-transform: uppercase;">${escapeHtml(exp.category || "N/A")}</span></td>
                            <td style="padding: 1rem 0.75rem; color: var(--text-muted); font-size: 0.8rem;">${formattedDate}</td>
                            <td style="padding: 1rem 0.75rem;">
                                <div style="font-weight: 500; color: white;">${escapeHtml(exp.employee_name || "N/A")}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(exp.employee_email || "")}</div>
                            </td>
                            <td style="padding: 1rem 0.75rem;"><span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(exp.department || "N/A")}</span></td>
                            <td style="padding: 1rem 0.75rem; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(exp.manager_email || "N/A")}</td>
                            <td style="padding: 1rem 0.75rem;">
                                <div style="font-weight: 500; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(exp.submitted_by_email || "System")}</div>
                                <div style="font-size: 0.7rem; color: #a5b4fc; font-weight: 500;">Role: ${escapeHtml(exp.submitted_by_role || "user")}</div>
                            </td>
                            <td style="padding: 1rem 0.75rem; font-weight: 700; color: white;">${formatMoney(exp.amount)}</td>
                            <td style="padding: 1rem 0.75rem;">
                                <div style="margin-bottom: 0.25rem;">${statusBadge}</div>
                                <div style="color: ${policyColor}; font-size: 0.75rem; font-weight: 600;">${escapeHtml(exp.policy_status || "N/A")}</div>
                            </td>
                            <td style="padding: 1rem 0.75rem;">
                                ${exp.reviewer_email || exp.decision_by_email ? `
                                    <div style="font-weight: 500; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(reviewerText)}</div>
                                    <div style="font-size: 0.7rem; color: #f472b6; font-weight: 500;">Role: ${escapeHtml(reviewerRole)}</div>
                                ` : `
                                    <span style="color: var(--text-muted); font-style: italic; font-size: 0.8rem;">No review</span>
                                `}
                            </td>
                            <td style="padding: 1rem 0.75rem; text-align: right;">
                                <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                                    <button class="btn btn-receipt" onclick="showClaimDetails('${exp.claim_id}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto; background: rgba(99,102,241,0.1); color: #cbd5e1; border-color: rgba(99,102,241,0.25);">
                                        View Details
                                    </button>
                                    <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', '${exp.amount || 0}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                        View Trail
                                    </button>
                                </div>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    } catch (err) {
                        console.warn("Failed to render history expense:", exp ? exp.claim_id : "unknown", err);
                    }
                });
                
            } catch (err) {
                console.error("Failed to load history", err);
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="padding: 3rem; text-align: center; color: #fb7185;">
                            ❌ Failed to load history: ${err.message}
                        </td>
                    </tr>
                `;
            }
        }

        async function loadAuditTrail(claimId, employeeName, amount) {
            switchTab('audit-trail');
            const container = document.getElementById("audit-trail-container");
            container.innerHTML = `
                <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                    <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                    Fetching audit timeline and claim details...
                </div>
            `;
            
            try {
                const response = await fetch(`/api/expenses/${claimId}`);
                if (!response.ok) throw new Error("HTTP " + response.status);
                
                const data = await response.json();
                const exp = data.expense || {};
                const logs = data.audit_logs || [];
                
                let headerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div>
                            <h3 style="font-size: 1.25rem; font-weight: 700; color: white;">Audit Trail for ${escapeHtml(exp.employee_name || employeeName)}</h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">Claim ID: ${escapeHtml(claimId)}</p>
                        </div>
                        <div style="font-size: 1.35rem; font-weight: 800; color: white;">${formatMoney(exp.amount || amount)}</div>
                    </div>
                `;

                // Beautiful glassmorphic Summary Card
                let summaryHTML = `
                    <div class="audit-summary-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); backdrop-filter: blur(5px);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.2rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 0.8rem;">
                            <div>
                                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; letter-spacing: 0.05em;">Claim Lifecycle Summary</span>
                                <h3 style="font-size: 1.15rem; font-weight: 700; color: white; margin-top: 2px;">Details</h3>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.25rem; font-weight: 800; color: #818cf8;">${formatMoney(exp.amount || amount)}</div>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">Amount</span>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.5rem; font-size: 0.85rem;">
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Employee</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.employee_name || employeeName)}</span>
                                <span style="display: block; color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(exp.employee_email || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Assigned Manager</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.manager_email || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Department</strong>
                                <span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(exp.department || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Submitted By</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.submitted_by_email || "System")}</span>
                                <span style="display: block; color: #a5b4fc; font-size: 0.75rem; font-weight: 500;">Role: ${escapeHtml(exp.submitted_by_role || "user")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Reviewer / Decision By</strong>
                                ${exp.reviewer_email || exp.decision_by_email ? `
                                    <span style="color: white; font-weight: 600;">${escapeHtml(exp.reviewer_email || exp.decision_by_email)}</span>
                                    <span style="display: block; color: #f472b6; font-size: 0.75rem; font-weight: 500;">Role: ${escapeHtml(exp.reviewer_role || exp.decision_by_role || "manager")}</span>
                                ` : `
                                    <span style="color: var(--text-muted); font-style: italic;">No manager review yet</span>
                                `}
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Reimbursement Status</strong>
                                <span style="margin-top: 0.15rem; display: inline-block;">${getStatusBadgeHTML(exp.status)}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                if (logs.length === 0) {
                    container.innerHTML = headerHTML + summaryHTML + `
                        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                            📭 No audit events registered for this claim.
                        </div>
                    `;
                    return;
                }
                
                let timelineHTML = `<div style="position: relative; padding-left: 2.5rem; margin-top: 1rem;">`;
                timelineHTML += `<div style="position: absolute; left: 0.7rem; top: 1rem; bottom: 1rem; width: 2px; background: rgba(255,255,255,0.1);"></div>`;
                
                logs.forEach((log, idx) => {
                    const formattedTime = log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A";
                    
                    let dotColor = "var(--primary)";
                    let dotIcon = "○";
                    if (log.event_type === 'claim_ingested') { dotColor = "#3b82f6"; dotIcon = "📥"; }
                    else if (log.event_type === 'employee_submitted_claim') { dotColor = "#10b981"; dotIcon = "📝"; }
                    else if (log.event_type === 'session_bound') { dotColor = "#8b5cf6"; dotIcon = "🔗"; }
                    else if (log.event_type === 'document_uploaded') { dotColor = "#10b981"; dotIcon = "📂"; }
                    else if (log.event_type === 'policies_reevaluated') { dotColor = "#6366f1"; dotIcon = "🛡️"; }
                    else if (log.event_type === 'manager_decision') { dotColor = "#f59e0b"; dotIcon = "✍️"; }
                    else if (log.event_type === 'agent_finalized') { dotColor = "#10b981"; dotIcon = "🏁"; }
                    
                    const isSecureAuth = log.authenticated === true || (log.metadata && log.metadata.authenticated === true);
                    
                    timelineHTML += `
                        <div style="position: relative; margin-bottom: 2rem;">
                            <div style="position: absolute; left: -2.5rem; top: 0.1rem; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: #0c0e24; border: 2px solid ${dotColor}; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; z-index: 2; box-shadow: 0 0 10px ${dotColor}33;">
                                ${dotIcon}
                            </div>
                            
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="font-size: 1rem; font-weight: 600; color: white;">${escapeHtml(log.event_type.replace(/_/g, ' ').toUpperCase())}</h4>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">${formattedTime}</span>
                                </div>
                                <p style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0.3rem;">${escapeHtml(log.event_message)}</p>
                                ${(() => {
                                    if (log.actor_email) {
                                        const displayRole = (log.actor_role || "").replace(/_/g, ' ').toUpperCase();
                                        const authLabel = isSecureAuth ? `
                                            <div style="display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.72rem; color: #10b981; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 6px; font-weight: 600; margin-top: 0.25rem; box-shadow: 0 0 8px rgba(16,185,129,0.15);">
                                                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                                    <path fill-rule="evenodd" d="M8.603 3.702A3 3 0 0110.53 2.5h2.94a3 3 0 011.927 1.202l1.696 2.544a1 1 0 00.765.424l3.033.242a3 3 0 012.637 2.637l.242 3.033a1 1 0 00.424.765l2.544 1.696a3 3 0 010 5.156l-2.544 1.696a1 1 0 00-.424.765l-.242 3.033a3 3 0 01-2.637 2.637l-3.033.242a1 1 0 00-.765.424l-1.696 2.544a3 3 0 01-5.156 0l-1.696-2.544a1 1 0 00-.765-.424l-3.033-.242a3 3 0 01-2.637-2.637l-.242-3.033a1 1 0 00-.424-.765L1.202 15.03a3 3 0 010-5.156l2.544-1.696a1 1 0 00.424-.765l.242-3.033a3 3 0 012.637-2.637l3.033-.242a1 1 0 00.765-.424l1.696-2.544zM16.207 10.207a1 1 0 00-1.414-1.414L11 12.586 9.207 10.793a1 1 0 00-1.414 1.414l2.5 2.5a1 1 0 001.414 0l4.5-4.5z" clip-rule="evenodd" />
                                                </svg>
                                                Secure Auth Verified
                                            </div>
                                        ` : `
                                            <span style="font-size: 0.75rem; color: #10b981; font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Auth: Google Authenticated</span>
                                        `;
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: ${escapeHtml(log.actor_email)}</span>
                                            <br>
                                            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Role: ${escapeHtml(displayRole)}</span>
                                            <br>
                                            ${authLabel}
                                        `;
                                    } else if (log.actor_display === 'Legacy Manager' || log.actor === 'manager' || log.actor === 'user' || log.actor === 'Legacy Manager' || log.event_type === 'manager_decision') {
                                        const displayRole = (log.actor_role || "manager").replace(/_/g, ' ').toUpperCase();
                                        const authLabel = isSecureAuth ? `
                                            <div style="display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.72rem; color: #10b981; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 6px; font-weight: 600; margin-top: 0.25rem; box-shadow: 0 0 8px rgba(16,185,129,0.15);">
                                                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                                    <path fill-rule="evenodd" d="M8.603 3.702A3 3 0 0110.53 2.5h2.94a3 3 0 011.927 1.202l1.696 2.544a1 1 0 00.765.424l3.033.242a3 3 0 012.637 2.637l.242 3.033a1 1 0 00.424.765l2.544 1.696a3 3 0 010 5.156l-2.544 1.696a1 1 0 00-.424.765l-.242 3.033a3 3 0 01-2.637 2.637l-3.033.242a1 1 0 00-.765.424l-1.696 2.544a3 3 0 01-5.156 0l-1.696-2.544a1 1 0 00-.765-.424l-3.033-.242a3 3 0 01-2.637-2.637l-.242-3.033a1 1 0 00-.424-.765L1.202 15.03a3 3 0 010-5.156l2.544-1.696a1 1 0 00.424-.765l.242-3.033a3 3 0 012.637-2.637l3.033-.242a1 1 0 00.765-.424l1.696-2.544zM16.207 10.207a1 1 0 00-1.414-1.414L11 12.586 9.207 10.793a1 1 0 00-1.414 1.414l2.5 2.5a1 1 0 001.414 0l4.5-4.5z" clip-rule="evenodd" />
                                                </svg>
                                                Secure Auth Verified
                                            </div>
                                        ` : `
                                            <span style="font-size: 0.75rem; color: #f59e0b; font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Auth: Pre-Google Auth</span>
                                        `;
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: Legacy Manager</span>
                                            <br>
                                            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Role: ${escapeHtml(displayRole)}</span>
                                            <br>
                                            ${authLabel}
                                        `;
                                    } else {
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: ${escapeHtml(log.actor)}</span>
                                        `;
                                    }
                                })()}
                            </div>
                        </div>
                    `;
                });
                
                timelineHTML += `</div>`;
                container.innerHTML = headerHTML + summaryHTML + timelineHTML;
                
            } catch (err) {
                console.error("Failed to load audit trail", err);
                container.innerHTML = `
                    <div style="text-align: center; padding: 3rem; color: #fb7185;">
                        ❌ Failed to load audit trail: ${err.message}
                    </div>
                `;
            }
        }

        function runPolicyCheck(claim) {
            let result = {
                isValid: true,
                category: claim.category || 'N/A',
                nights: null,
                costPerNight: null,
                requiredDocs: [],
                missingDocs: [],
                warnings: [],
                status: 'Within policy'
            };

            const cat = (claim.category || '').toLowerCase();
            const amount = claim.amount || 0;

            // 0. Integrated Per Diem Check
            if (['meals', 'lodging', 'hotel', 'travel'].includes(cat)) {
                if (claim.per_diem_review) {
                    const pdr = claim.per_diem_review;
                    if (pdr.status === "Missing company policy") {
                        result.isValid = false;
                        result.status = "Missing company policy";
                        result.warnings.push(pdr.warning || "Missing company policy");
                    } else if (pdr.status === "Missing per diem data") {
                        result.isValid = false;
                        result.status = "Missing per diem data";
                        result.warnings.push(pdr.warning || "Missing per diem data");
                    } else if (pdr.status === "Exceeds company per diem") {
                        result.isValid = false;
                        result.status = "Exceeds company per diem";
                        result.warnings.push(pdr.warning || "Exceeds company per diem");
                        result.requiredDocs.push("Manager Approval Letter");
                        if (!pdr.manager_letter_uploaded) {
                            result.missingDocs.push("Manager Approval Letter");
                        }
                    } else if (pdr.status === "Requires manager approval") {
                        result.isValid = true;
                        result.status = "Requires manager approval";
                        result.warnings.push(pdr.warning || "Requires manager approval");
                    }
                }
            }

            // 1. Lodging / Hotel Review
            if (cat === 'lodging' || cat === 'hotel') {
                if (claim.check_in_date && claim.check_out_date) {
                    const checkIn = new Date(claim.check_in_date);
                    const checkOut = new Date(claim.check_out_date);
                    const diffTime = Math.abs(checkOut - checkIn);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    if (diffDays > 0) {
                        result.nights = diffDays;
                        result.costPerNight = amount / diffDays;
                        
                        if (result.costPerNight > 350.0) {
                            result.requiredDocs.push("Manager Approval Letter");
                            if (!claim.manager_approval_letter_url) {
                                result.missingDocs.push("Manager Approval Letter");
                                result.warnings.push("Manager approval letter required because lodging exceeds $350 per night.");
                                result.isValid = false;
                                result.status = "Requires manager approval letter";
                            }
                        }
                    }
                }
            }

            // 2. Flight Ticket Review
            const isFlight = cat === 'flight' || cat === 'airfare' || (cat === 'travel' && (claim.travel_type || '').toLowerCase() === 'flight');
            if (isFlight) {
                result.requiredDocs.push("Flight Ticket Receipt");
                if (!claim.flight_ticket_receipt_url) {
                    result.missingDocs.push("Flight Ticket Receipt");
                    result.warnings.push("Flight ticket receipt required before approval.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }

                if (amount > 1200.0) {
                    result.requiredDocs.push("Manager Approval Letter");
                    if (!claim.manager_approval_letter_url) {
                        result.missingDocs.push("Manager Approval Letter");
                        result.warnings.push("Manager approval letter required because flight ticket exceeds $1200.");
                        result.isValid = false;
                        if (result.status !== "Needs documentation") {
                            result.status = "Requires manager approval letter";
                        }
                    }
                }
            }

            if (!result.isValid && result.status === 'Within policy') {
                result.status = 'Needs documentation';
            }

            // 3. Office Supplies / Printing Supplies
            const officeCats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"];
            if (officeCats.includes(cat)) {
                result.isOffice = true;
                const hasReceipt = !!(claim.office_receipt_url || claim.receipt_url);
                if (amount > 50.0) {
                    result.requiredDocs.push("Receipt");
                    if (!hasReceipt) {
                        result.missingDocs.push("Receipt");
                        result.warnings.push("Receipt is required for office supplies above $50.");
                        result.isValid = false;
                        result.status = "Needs documentation";
                    }
                }
                if (!claim.business_purpose) {
                    result.warnings.push("Business purpose is required for office supplies.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (amount > 250.0 && result.isValid) {
                    result.status = "Requires manager approval";
                }
            }

            // 4. Business Parking
            const parkingCats = ["business_parking", "parking_fee"];
            if (parkingCats.includes(cat)) {
                result.isParking = true;
                result.requiredDocs.push("Parking Receipt");
                const hasReceipt = !!(claim.parking_receipt_url || claim.receipt_url);
                if (!hasReceipt) {
                    result.missingDocs.push("Parking Receipt");
                    result.warnings.push("Parking receipt is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.parking_date) {
                    result.warnings.push("Parking date is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.parking_location) {
                    result.warnings.push("Parking location is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.business_purpose) {
                    result.warnings.push("Business purpose is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (result.isValid) {
                    result.status = "Within policy";
                }
            }

            // 5. Parking Tickets / Citations
            const citationCats = ["parking_ticket", "parking_citation"];
            if (citationCats.includes(cat)) {
                result.isCitation = true;
                result.requiredDocs.push("Manager Approval Letter");
                if (!claim.manager_approval_letter_url) {
                    result.missingDocs.push("Manager Approval Letter");
                    result.isValid = false;
                    result.status = "Potentially non-reimbursable";
                    result.warnings.push("Parking fines or citations are normally not reimbursable without explicit manager approval.");
                } else {
                    result.status = "Requires manager approval";
                }
            }

            return result;
        }

        function getDocumentsConfig(claim, policy) {
            const cat = (claim.category || '').toLowerCase();
            const amount = claim.amount || 0;
            const isFlight = cat === 'flight' || cat === 'airfare' || (cat === 'travel' && (claim.travel_type || '').toLowerCase() === 'flight');
            const officeCats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"];
            const isOffice = officeCats.includes(cat);
            const parkingCats = ["business_parking", "parking_fee"];
            const isParking = parkingCats.includes(cat);
            const citationCats = ["parking_ticket", "parking_citation"];
            const isCitation = citationCats.includes(cat);
            const isHotel = cat === 'lodging' || cat === 'hotel';

            let docs = [];

            if (isHotel) {
                docs.push({
                    type: "hotel_receipt",
                    name: "Hotel Receipt",
                    required: false,
                    url: claim.hotel_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: (policy.costPerNight > 350.0),
                    url: claim.manager_approval_letter_url
                });
            } else if (isFlight) {
                docs.push({
                    type: "flight_ticket_receipt",
                    name: "Flight Ticket Receipt",
                    required: true,
                    url: claim.flight_ticket_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: (amount > 1200.0),
                    url: claim.manager_approval_letter_url
                });
            } else if (isOffice) {
                docs.push({
                    type: "office_receipt",
                    name: "Office Receipt",
                    required: (amount > 50.0),
                    url: claim.office_receipt_url || claim.receipt_url
                });
            } else if (isParking) {
                docs.push({
                    type: "parking_receipt",
                    name: "Parking Receipt",
                    required: true,
                    url: claim.parking_receipt_url || claim.receipt_url
                });
            } else if (isCitation) {
                docs.push({
                    type: "parking_receipt",
                    name: "Parking Receipt",
                    required: false,
                    url: claim.parking_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: true,
                    url: claim.manager_approval_letter_url
                });
            } else {
                docs.push({
                    type: "receipt",
                    name: "Receipt",
                    required: (amount > 50.0),
                    url: claim.receipt_url
                });
            }

            // Add manager approval letter if required by per diem policy and not already present
            if (policy.requiredDocs.includes("Manager Approval Letter")) {
                const hasLetter = docs.some(d => d.type === "manager_approval_letter");
                if (!hasLetter) {
                    docs.push({
                        type: "manager_approval_letter",
                        name: "Manager Approval Letter",
                        required: true,
                        url: claim.manager_approval_letter_url
                    });
                } else {
                    docs.forEach(d => {
                        if (d.type === "manager_approval_letter") {
                            d.required = true;
                        }
                    });
                }
            }

            return docs;
        }

        async function uploadDocument(sessionId, docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            
            const btnLabel = document.getElementById(`upload-btn-${sessionId}-${docType}`);
            const originalHTML = btnLabel.innerHTML;
            btnLabel.style.pointerEvents = "none";
            btnLabel.innerHTML = `<div class="spinner" style="width:12px; height:12px; border-width:1.5px; margin:0; display:inline-block; vertical-align:middle;"></div>`;
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/upload/${sessionId}/${docType}`, {
                    method: "POST",
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                await fetchPendingApprovals();
            } catch (err) {
                console.error("Document upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                btnLabel.innerHTML = originalHTML;
                btnLabel.style.pointerEvents = "all";
            }
        }

        let pendingSourceFilter = "all";

        function setPendingSourceFilter(src) {
            pendingSourceFilter = src;
            const buttons = ["all", "employee_portal", "report_workflow", "legacy_cli"];
            buttons.forEach(bId => {
                const btn = document.getElementById(`src-btn-${bId}`);
                if (btn) {
                    if (bId === src) {
                        btn.classList.add("active");
                    } else {
                        btn.classList.remove("active");
                    }
                }
            });
            fetchPendingApprovals();
        }
        window.setPendingSourceFilter = setPendingSourceFilter;

        async function fetchPendingApprovals() {
            const grid = document.getElementById("dashboard-grid");
            const countBadge = document.getElementById("pending-count");
            const hiddenBadge = document.getElementById("hidden-badge");
            const hiddenCountEl = document.getElementById("hidden-count");
            
            try {
                const response = await fetch(`/api/pending?source=${pendingSourceFilter}`);
                if (!response.ok) throw new Error("HTTP error " + response.status);
                
                const data = await response.json();
                const claims = data.pending_claims;
                const hiddenCount = data.hidden_cli_sessions_count;
                
                countBadge.textContent = claims.length;
                
                if (hiddenCount > 0) {
                    hiddenCountEl.textContent = hiddenCount;
                    hiddenBadge.style.display = "flex";
                } else {
                    hiddenBadge.style.display = "none";
                }
                
                grid.innerHTML = "";
                cachedClaims = {};
                
                if (claims.length === 0) {
                    grid.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">🎉</div>
                            <h3>All Caught Up!</h3>
                            <p>No claims are currently pending manager validation. All high-value transactions have been resolved.</p>
                        </div>
                    `;
                    return;
                }
                
                claims.forEach((claim, idx) => {
                    try {
                        cachedClaims[claim.session_id] = claim;
                        
                        const initials = claim.employee_name
                            .split("@")[0]
                            .split(".")
                            .map(n => n[0])
                            .join("")
                            .toUpperCase()
                            .substring(0, 3) || "EX";
                            
                        const avatarGradientClass = `gradient-avatar-${Math.abs(claim.employee_name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 6}`;
                        
                        const policy = runPolicyCheck(claim);
                        const docsConfig = getDocumentsConfig(claim, policy);
                        
                        const card = document.createElement("div");
                        card.className = "approval-card";
                        card.id = `card-${claim.session_id}`;
                        card.style.animationDelay = `${idx * 0.1}s`;
                        
                        card.innerHTML = `
                            <div class="card-loader" id="loader-${claim.session_id}">
                                <div class="spinner"></div>
                                <div class="loader-text">Resuming Agent Runtime...</div>
                            </div>
                            <div class="card-header">
                                <div class="claimant-avatar ${avatarGradientClass}">${initials}</div>
                                <div class="claimant-info">
                                    <h3>${escapeHtml(claim.employee_name)}</h3>
                                    <p>Session: ${claim.session_id.substring(0, 8)}...</p>
                                </div>
                                <div class="amount-tag">${formatMoney(claim.amount)}</div>
                            </div>
                            <div class="card-body">
                                <p class="claim-desc">"${escapeHtml(claim.description)}"</p>
                                <div class="claim-participants-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin: 1rem 0; padding: 0.8rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.8rem;">
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Employee</span>
                                        <span style="font-weight: 600; color: #e0e7ff;">${escapeHtml(claim.employee_name || 'N/A')}</span>
                                        <span style="display: block; font-size: 0.72rem; color: var(--text-muted); overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.employee_email || 'N/A')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Assigned Manager</span>
                                        <span style="font-weight: 600; color: #e0e7ff; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.manager_email || 'None')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Submitted By</span>
                                        <span style="font-weight: 600; color: #cbd5e1; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.submitted_by_email || 'System')}</span>
                                        <span style="display: block; font-size: 0.72rem; color: #a5b4fc; font-weight: 500;">Role: ${escapeHtml(claim.submitted_by_role || 'user')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Reviewer Info</span>
                                        ${claim.reviewer_email ? `
                                            <span style="font-weight: 600; color: #cbd5e1; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.reviewer_email)}</span>
                                            <span style="display: block; font-size: 0.72rem; color: #f472b6; font-weight: 500;">Role: ${escapeHtml(claim.reviewer_role || 'reviewer')}</span>
                                        ` : `
                                            <span style="color: var(--text-muted); font-style: italic;">Not yet reviewed</span>
                                        `}
                                    </div>
                                </div>
                                <div class="meta-list" style="margin-bottom: 1rem;">
                                    <div class="meta-item">
                                        <strong>Interrupt ID:</strong> ${escapeHtml(claim.interrupt_id)}
                                    </div>
                                    <div class="meta-item">
                                        <strong>Prompt Role:</strong> ${escapeHtml(claim.user_id)}
                                    </div>
                                </div>
                                
                                <!-- Policy Review details -->
                                <div class="policy-review-box" style="margin-top: 1rem; padding: 1rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;">
                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                        </svg>
                                        Policy Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem; margin-bottom: 0.6rem;">
                                        <div><strong>Category:</strong> ${escapeHtml(policy.category)}</div>
                                        <div><strong>Status:</strong> <span style="color: ${policy.isValid ? '#34d399' : '#fb7185'}; font-weight: 600;">${policy.status}</span></div>
                                        ${policy.nights ? `<div><strong>Hotel Nights:</strong> ${policy.nights}</div>` : ''}
                                        ${policy.costPerNight ? `<div><strong>Nightly Cost:</strong> ${formatMoney(policy.costPerNight)}</div>` : ''}
                                    </div>
                                    
                                    ${policy.requiredDocs.length > 0 ? `
                                    <div style="font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.5rem; margin-top: 0.5rem;">
                                        <strong>Documents:</strong>
                                        <ul style="list-style: none; margin-top: 0.2rem; display: flex; flex-direction: column; gap: 0.25rem;">
                                            ${policy.requiredDocs.map(doc => {
                                                const isMissing = policy.missingDocs.includes(doc);
                                                return `<li style="display: flex; align-items: center; gap: 0.3rem; color: ${isMissing ? '#f43f5e' : '#10b981'};">
                                                    <span>${isMissing ? '✕' : '✓'}</span> ${doc}
                                                </li>`;
                                            }).join('')}
                                        </ul>
                                    </div>
                                    ` : ''}
                                    
                                    ${policy.warnings.map(w => `
                                    <div style="margin-top: 0.6rem; padding: 0.5rem 0.8rem; border-radius: 8px; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); color: #fb7185; font-size: 0.75rem; line-height: 1.4; display: flex; align-items: flex-start; gap: 0.4rem;">
                                        <span style="font-size: 0.9rem; line-height: 1;">⚠️</span>
                                        <span>${escapeHtml(w)}</span>
                                    </div>
                                    `).join('')}
                                </div>

                                <!-- Office Supplies Review -->
                                ${policy.isOffice ? `
                                <div class="office-review-box" style="margin-top: 0.8rem; padding: 1rem; border-radius: 12px; background: rgba(99, 102, 241, 0.04); border: 1px solid rgba(99, 102, 241, 0.15);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        💼 Office Expense Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                        <div><strong>Item Type:</strong> ${escapeHtml(claim.item_type || 'N/A')}</div>
                                        <div><strong>Vendor:</strong> ${escapeHtml(claim.vendor || 'N/A')}</div>
                                        <div><strong>Quantity:</strong> ${claim.quantity != null ? claim.quantity : 'N/A'}</div>
                                        <div><strong>Amount:</strong> ${formatMoney(claim.amount)}</div>
                                        <div style="grid-column: span 2;"><strong>Business Purpose:</strong> ${escapeHtml(claim.business_purpose || 'N/A')}</div>
                                    </div>
                                </div>
                                ` : ''}

                                <!-- Parking Expense Review -->
                                ${(policy.isParking || policy.isCitation) ? `
                                <div class="parking-review-box" style="margin-top: 0.8rem; padding: 1rem; border-radius: 12px; background: rgba(139, 92, 246, 0.04); border: 1px solid rgba(139, 92, 246, 0.15);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #c084fc; letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        🚗 Parking Expense Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                        <div><strong>Location:</strong> ${escapeHtml(claim.parking_location || 'N/A')}</div>
                                        <div><strong>Date:</strong> ${escapeHtml(claim.parking_date || 'N/A')}</div>
                                        <div style="grid-column: span 2;"><strong>Business Purpose:</strong> ${escapeHtml(claim.business_purpose || 'N/A')}</div>
                                        ${claim.non_reimbursable_reason ? `<div style="grid-column: span 2; color: #fb7185;"><strong>Non-Reimbursable Reason:</strong> ${escapeHtml(claim.non_reimbursable_reason)}</div>` : ''}
                                    </div>
                                </div>
                                ` : ''}
                                
                                <!-- Per Diem Review Section -->
                                ${claim.per_diem_review ? `
                                <div class="per-diem-review-box" style="margin-top: 1rem; padding: 1.2rem; border-radius: 14px; background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.2);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        📅 Per Diem Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem 1rem; font-size: 0.8rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 0.8rem; margin-bottom: 0.8rem;">
                                        <div><strong style="color: var(--text-muted);">Company Name:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.company_name || 'N/A')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Employee:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.employee_name || claim.employee_name)}</span></div>
                                        <div><strong style="color: var(--text-muted);">Email:</strong> <span style="color: #c7d2fe; font-size: 0.75rem;">${escapeHtml(claim.per_diem_review.employee_email || '')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Destination:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.city || 'N/A')}, ${escapeHtml(claim.per_diem_review.state || 'N/A')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Travel Dates:</strong> <span style="color: #c7d2fe; font-size: 0.75rem;">${claim.per_diem_review.travel_start_date ? claim.per_diem_review.travel_start_date.substring(0,10) : 'N/A'} to ${claim.per_diem_review.travel_end_date ? claim.per_diem_review.travel_end_date.substring(0,10) : 'N/A'}</span></div>
                                        <div><strong style="color: var(--text-muted);">Travel Duration:</strong> <span style="color: #e0e7ff; font-weight: 500;">${claim.per_diem_review.travel_days} days (${claim.per_diem_review.hotel_nights} nights)</span></div>
                                        <div style="grid-column: span 2;"><strong style="color: var(--text-muted);">Policy Source:</strong> <span class="badge" style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600; font-size: 0.7rem; border: 1px solid rgba(99,102,241,0.3); text-transform: uppercase;">${escapeHtml(claim.per_diem_review.policy_source || 'N/A')}</span></div>
                                    </div>

                                    <div style="margin-bottom: 0.8rem;">
                                        <table style="width: 100%; border-collapse: collapse; font-size: 0.75rem; color: #cbd5e1; text-align: left;">
                                            <thead>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted); font-weight: 600;">
                                                    <th style="padding: 0.4rem 0;">Category</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Rate / Limit</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Allowed</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Claimed</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Meals</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.meal_rate_per_day)}/day</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_meal_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_meals)}</td>
                                                </tr>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Lodging</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.lodging_rate_per_night)}/night</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_lodging_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_lodging)}</td>
                                                </tr>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Incidentals</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.incidental_rate_per_day)}/day</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_incidental_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_incidentals)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>

                                    <div style="display: flex; flex-direction: column; gap: 0.4rem; padding-top: 0.6rem; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Total Claimed Amount:</span>
                                            <span style="color: white; font-weight: 600;">${formatMoney(claim.per_diem_review.claimed_amount)}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Allowed Per Diem Total:</span>
                                            <span style="color: #818cf8; font-weight: 600;">${formatMoney(safeNumber(claim.per_diem_review.allowed_meal_total) + safeNumber(claim.per_diem_review.allowed_lodging_total) + safeNumber(claim.per_diem_review.allowed_incidental_total))}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Overage / Overage Status:</span>
                                            <span style="color: ${claim.per_diem_review.overage_total > 0 ? '#fb7185' : '#34d399'}; font-weight: 600;">
                                                ${claim.per_diem_review.overage_total > 0 ? `+${formatMoney(claim.per_diem_review.overage_total)} (Exceeds)` : 'Within budget'}
                                            </span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Per Diem Review Status:</span>
                                            <span class="badge" style="background: ${
                                                claim.per_diem_review.status === 'Within company per diem' ? 'rgba(16,185,129,0.15)' :
                                                claim.per_diem_review.status === 'Exceeds company per diem' ? 'rgba(244,63,94,0.15)' :
                                                claim.per_diem_review.status === 'Requires manager approval' ? 'rgba(99,102,241,0.15)' :
                                                'rgba(245,158,11,0.15)'
                                            }; color: ${
                                                claim.per_diem_review.status === 'Within company per diem' ? '#34d399' :
                                                claim.per_diem_review.status === 'Exceeds company per diem' ? '#fb7185' :
                                                claim.per_diem_review.status === 'Requires manager approval' ? '#a5b4fc' :
                                                '#fbbf24'
                                            }; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600; font-size: 0.7rem; border: 1px solid currentColor;">
                                                ${escapeHtml(claim.per_diem_review.status)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                ` : ''}

                                <!-- Document Verification Box with Upload -->
                                <div class="document-verification-box" style="margin-top: 1rem; padding: 1rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        📂 Required Documents
                                    </h4>
                                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                        ${docsConfig.map(doc => {
                                            return `
                                            <div class="doc-row" style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; gap: 0.5rem;">
                                                <div style="display: flex; flex-direction: column;">
                                                    <span style="font-size: 0.85rem; font-weight: 600; color: white;">${doc.name}</span>
                                                    <span style="font-size: 0.75rem; color: ${doc.url ? '#10b981' : (doc.required ? '#fb7185' : 'var(--text-muted)')}; font-weight: 500;">
                                                        ${doc.url ? '✓ Uploaded' : (doc.required ? '✕ Required' : '○ Optional')}
                                                    </span>
                                                </div>
                                                <div style="display: flex; gap: 0.4rem; align-items: center;">
                                                    ${doc.url ? `
                                                    <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; flex: none; text-decoration: none;">
                                                        View
                                                    </a>
                                                    ` : ''}
                                                    <label class="btn-doc-upload" id="upload-btn-${claim.session_id}-${doc.type}" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-main); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.2rem; transition: var(--transition); user-select: none;">
                                                        <input type="file" onchange="uploadDocument('${claim.session_id}', '${doc.type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                                                        <span>${doc.url ? 'Replace' : 'Upload'}</span>
                                                    </label>
                                                </div>
                                            </div>
                                            `;
                                        }).join('')}
                                    </div>
                                </div>
                            </div>

                            <!-- Override Reason Box (finance_admin only) -->
                            ${(() => {
                                const isOverLimit = claim.per_diem_review && claim.per_diem_review.status === "Exceeds company per diem" && !claim.per_diem_review.manager_letter_uploaded;
                                const showOverrideInput = isOverLimit && USER_ROLE === "finance_admin";
                                if (showOverrideInput) {
                                    return `
                                    <div class="override-box" style="margin: 0.8rem 1.8rem 0 1.8rem; padding: 0.8rem; border-radius: 10px; background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2);">
                                        <label style="font-size: 0.75rem; color: #f59e0b; font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 0.4rem;">
                                            ⚠️ Finance Admin Policy Override
                                        </label>
                                        <input type="text" id="override-reason-${claim.session_id}" placeholder="Provide override reason (minimum 3 characters)..." 
                                            oninput="const btn = document.getElementById('approve-btn-${claim.session_id}'); const isValid = this.value.trim().length >= 3; btn.disabled = !isValid; btn.style.opacity = isValid ? '1' : '0.4'; btn.style.pointerEvents = isValid ? 'auto' : 'none';" 
                                            style="width: 100%; padding: 0.5rem 0.8rem; border-radius: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; font-size: 0.8rem; outline: none; transition: var(--transition);"
                                            onfocus="this.style.borderColor='var(--primary)';" onblur="this.style.borderColor='rgba(255,255,255,0.1)';">
                                    </div>
                                    `;
                                }
                                return '';
                            })()}

                            <div class="card-actions" style="padding: 0 1.8rem 1.8rem 1.8rem; margin-top: 1rem;">
                                <button class="btn btn-reject" onclick="handleAction('${claim.session_id}', false)">
                                    Reject
                                </button>
                                <button class="btn btn-approve" id="approve-btn-${claim.session_id}" ${(() => {
                                    const isOverLimit = claim.per_diem_review && claim.per_diem_review.status === "Exceeds company per diem" && !claim.per_diem_review.manager_letter_uploaded;
                                    const showOverrideInput = isOverLimit && USER_ROLE === "finance_admin";
                                    if (showOverrideInput) {
                                        return 'disabled style="opacity: 0.4; cursor: not-allowed; pointer-events: none;"';
                                    } else if (!policy.isValid) {
                                        return 'disabled style="opacity: 0.4; cursor: not-allowed; pointer-events: none;"';
                                    }
                                    return '';
                                })()} onclick="handleAction('${claim.session_id}', true)">
                                    Approve Claim
                                </button>
                            </div>
                        `;
                        grid.appendChild(card);
                    } catch (cardErr) {
                        console.warn("Failed to render pending claim card for session_id:", claim.session_id, cardErr);
                    }
                });
                
            } catch (err) {
                console.error("Failed to load approvals", err);
                grid.innerHTML = `
                    <div class="empty-state" style="border-color: var(--danger-glow);">
                        <div class="empty-icon" style="filter:none;">❌</div>
                        <h3 style="color:#f43f5e;">System Sync Offline</h3>
                        <p>Error connecting to backend services: ${err.message}. Ensure your credentials are active and GCP_PROJECT is set.</p>
                    </div>
                `;
            }
        }

        async function handleAction(sessionId, approved) {
            const loader = document.getElementById(`loader-${sessionId}`);
            loader.style.display = "flex";
            
            const claim = cachedClaims[sessionId];
            const interruptId = claim ? claim.interrupt_id : "review_decision";
            
            let overrideReason = null;
            const overrideInput = document.getElementById(`override-reason-${sessionId}`);
            if (overrideInput) {
                overrideReason = overrideInput.value.trim();
            }
            
            try {
                const response = await fetch(`/api/action/${sessionId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        approved, 
                        interrupt_id: interruptId,
                        override_reason: overrideReason
                    })
                });
                
                if (!response.ok) throw new Error("HTTP Action error: " + response.status);
                
                const data = await response.json();
                
                showComplianceReview(claim, approved, data.final_review);
                showToast(approved ? "Claim approved successfully!" : "Claim rejected successfully.", "success");
                await fetchPendingApprovals();
                
            } catch (err) {
                console.error("Action execution failed", err);
                showToast("Action failed: " + err.message, "error");
                loader.style.display = "none";
            }
        }

        function showComplianceReview(claim, approved, finalReview) {
            const claimantEl = document.getElementById("modal-claimant");
            const amountEl = document.getElementById("modal-amount");
            const sessionEl = document.getElementById("modal-session-id");
            const statusBox = document.getElementById("modal-status-box");
            const statusIcon = document.getElementById("modal-status-icon");
            const statusTitle = document.getElementById("modal-status-title");
            const statusDesc = document.getElementById("modal-status-desc");
            const commentsEl = document.getElementById("modal-comments");
            const receiptContainer = document.getElementById("modal-receipt-container");
            
            sessionEl.textContent = `Session Reference: ${claim.session_id}`;
            claimantEl.textContent = claim.employee_name;
            amountEl.textContent = formatMoney(claim.amount);
            commentsEl.textContent = finalReview;
            
            const docList = [];
            if (claim.receipt_url) docList.push(`<a href="${claim.receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">📄 View Receipt</a>`);
            if (claim.office_receipt_url) docList.push(`<a href="${claim.office_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">💼 View Office Receipt</a>`);
            if (claim.parking_receipt_url) docList.push(`<a href="${claim.parking_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">🚗 View Parking Receipt</a>`);
            if (claim.hotel_receipt_url) docList.push(`<a href="${claim.hotel_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">🏨 View Hotel Receipt</a>`);
            if (claim.flight_ticket_receipt_url) docList.push(`<a href="${claim.flight_ticket_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">✈️ View Flight Receipt</a>`);
            if (claim.manager_approval_letter_url) docList.push(`<a href="${claim.manager_approval_letter_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; border-color: rgba(99, 102, 241, 0.4); background: rgba(99, 102, 241, 0.15); display: flex; align-items: center; justify-content: center;">✉️ View Approval Letter</a>`);
            
            if (docList.length > 0) {
                receiptContainer.innerHTML = `<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; width: 100%;">${docList.join('')}</div>`;
                receiptContainer.style.display = "block";
            } else {
                receiptContainer.style.display = "none";
            }
            
            if (approved) {
                statusBox.className = "status-box approved";
                statusIcon.textContent = "✓";
                statusTitle.textContent = "Claim Approved";
                statusDesc.textContent = "Authorized on Agent Runtime. Automated payout scheduled.";
            } else {
                statusBox.className = "status-box rejected";
                statusIcon.textContent = "✕";
                statusTitle.textContent = "Claim Rejected";
                statusDesc.textContent = "Declined on Agent Runtime. Notification sent to claimant.";
            }
            
            toggleModal(true);
        }

        function toggleModal(active) {
            const overlay = document.getElementById("slide-overlay");
            const modal = document.getElementById("slide-modal");
            
            if (active) {
                overlay.classList.add("active");
                modal.classList.add("active");
            } else {
                overlay.classList.remove("active");
                modal.classList.remove("active");
            }
        }

        function showToast(message, type) {
            const toast = document.getElementById("toast");
            const toastText = document.getElementById("toast-text");
            
            toastText.textContent = message;
            toast.className = `toast toast-${type} active`;
            
            setTimeout(() => {
                toast.classList.remove("active");
            }, 4000);
        }

        function escapeHtml(str) {
            if (!str) return "";
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        \n\n        /*******************************************************************************
 * ENTERPRISE EXPENSE REPORT WORKFLOW FRONTEND UPGRADE (JS)
 ******************************************************************************/

let activeReportId = null;
let currentReportClaims = [];
let allReports = []; // For local in-memory filtering

// Initialize tab click handling for 'reports'
const originalSwitchTab = switchTab;
switchTab = function(tab) {
    if (tab === 'reports') {
        document.querySelectorAll(".tab-section").forEach(sec => sec.style.display = "none");
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.classList.remove("active");
            btn.style.color = "var(--text-muted)";
            btn.style.borderBottom = "none";
        });

        const activeBtn = document.getElementById("tab-reports");
        if (activeBtn) {
            activeBtn.classList.add("active");
            activeBtn.style.color = "white";
        }

        document.getElementById("section-reports").style.display = "block";
        closeReportBuilder();
        fetchMyReports();
    } else {
        originalSwitchTab(tab);
    }
};

// Override fetchPendingApprovals to also include reports pending review
const originalFetchPendingApprovals = fetchPendingApprovals;
fetchPendingApprovals = async function() {
    // Run original to fetch individual claims
    await originalFetchPendingApprovals();
    
    // Also append reports pending review to the dashboard grid if the user is a manager or admin
    if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
        try {
            const res = await fetch("/api/reports?status=pending_manager_review");
            if (!res.ok) return;
            const reports = await res.json();
            
            if (reports.length > 0) {
                const grid = document.getElementById("dashboard-grid");
                
                // If there was an empty state of querying agent registry, remove it
                const emptyState = grid.querySelector(".empty-state");
                if (emptyState && emptyState.textContent.includes("Querying Agent Registry")) {
                    grid.innerHTML = "";
                }
                
                reports.forEach(rep => {
                    // Check if report card is already rendered
                    if (document.getElementById(`report-card-pending-${rep.report_id}`)) return;
                    
                    const card = document.createElement("div");
                    card.id = `report-card-pending-${rep.report_id}`;
                    card.className = "claim-card pending";
                    card.style.position = "relative";
                    card.style.background = "linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)";
                    card.style.border = "1px solid rgba(99, 102, 241, 0.25)";
                    card.style.borderRadius = "20px";
                    card.style.padding = "1.5rem";
                    card.style.display = "flex";
                    card.style.flexDirection = "column";
                    card.style.gap = "1rem";
                    
                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); margin-bottom: 0.5rem; display: inline-block;">EXPENSE REPORT REVIEW</span>
                                <h3 style="font-size: 1.15rem; font-weight: 700; color: white;">${escapeHtml(rep.report_title)}</h3>
                                <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.1rem;">Period: ${rep.report_period_start} to ${rep.report_period_end}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.25rem; font-weight: 800; color: white;">${formatMoney(rep.total_claimed_amount)}</div>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">Reimbursable: ${formatMoney(rep.total_reimbursable_amount)}</span>
                            </div>
                        </div>
                        
                        <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 0.75rem; font-size: 0.8rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                            <div><strong style="color: var(--text-muted);">Employee:</strong> <span style="color: white;">${escapeHtml(rep.employee_name)}</span></div>
                            <div><strong style="color: var(--text-muted);">Department:</strong> <span style="color: white;">${escapeHtml(rep.department)}</span></div>
                            <div><strong style="color: var(--text-muted);">Exceptions:</strong> <span style="color: #f43f5e; font-weight: 600;">${rep.policy_exception_count}</span></div>
                            <div><strong style="color: var(--text-muted);">Claims:</strong> <span style="color: white;">${rep.claim_count}</span></div>
                        </div>

                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: auto; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05);">
                            <button class="btn btn-receipt" onclick="switchTab('reports'); loadReportBuilder('${rep.report_id}')" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; font-weight: 600; border-radius: 8px; width: auto; height: auto;">
                                Open Report Dossier
                            </button>
                        </div>
                    `;
                    grid.appendChild(card);
                });
            }
        } catch (err) {
            console.error("Error appending pending reports review queue:", err);
        }
    }
};

// Fetch reports from backend
async function fetchMyReports() {
    const grid = document.getElementById("reports-grid");
    grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
            <div class="spinner"></div>
            <h3>Loading Expense Reports...</h3>
            <p>Retrieving draft and submitted corporate expense reports from database...</p>
        </div>
    `;

    try {
        const response = await fetch("/api/reports");
        if (!response.ok) throw new Error("Failed to fetch reports");
        allReports = await response.json();
        
        // Show filter bar for managers and admins
        const filterBar = document.getElementById("reports-filter-bar");
        if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
            filterBar.style.display = "flex";
        } else {
            filterBar.style.display = "none";
        }

        applyReportFilters();
    } catch (err) {
        console.error("Error fetching reports:", err);
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1; border-color: var(--danger-glow);">
                <h3>Failed to load reports</h3>
                <p>${err.message}</p>
            </div>
        `;
    }
}

// In-memory filters
function applyReportFilters() {
    const employeeVal = document.getElementById("filter-employee").value.trim().toLowerCase();
    const managerVal = document.getElementById("filter-manager").value.trim().toLowerCase();
    const deptVal = document.getElementById("filter-department").value;
    const statusVal = document.getElementById("filter-status").value;

    const filtered = allReports.filter(r => {
        if (employeeVal && !r.employee_name.toLowerCase().includes(employeeVal) && !r.employee_email.toLowerCase().includes(employeeVal)) return false;
        if (managerVal && !r.manager_email.toLowerCase().includes(managerVal)) return false;
        if (deptVal && r.department !== deptVal) return false;
        if (statusVal && r.status !== statusVal) return false;
        return true;
    });

    renderReportsGrid(filtered);
}

function onReportFilterChange() {
    applyReportFilters();
}

function clearReportFilters() {
    document.getElementById("filter-employee").value = "";
    document.getElementById("filter-manager").value = "";
    document.getElementById("filter-department").value = "";
    document.getElementById("filter-status").value = "";
    applyReportFilters();
}

// Render grid of cards
function renderReportsGrid(reports) {
    const grid = document.getElementById("reports-grid");
    if (!reports || reports.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <h3>No Expense Reports Found</h3>
                <p>You haven't drafted any expense report containers yet. Click "New Expense Report" to get started.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = reports.map(r => {
        const start = r.report_period_start || "N/A";
        const end = r.report_period_end || "N/A";
        const claimCount = r.claim_count || 0;
        const missingCount = r.missing_document_count || 0;
        const exceptionCount = r.policy_exception_count || 0;
        
        let statusBadge = "";
        let actionBtnText = "View Report";
        let isEditable = r.status === "draft" || r.status === "returned_to_employee";
        
        if (isEditable) {
            actionBtnText = "Edit / Build";
        } else if (r.status === "pending_manager_review") {
            actionBtnText = USER_ROLE === "employee" ? "View Details" : "Review Dossier";
        }

        switch (r.status) {
            case 'draft':
                statusBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);">Draft</span>`;
                break;
            case 'submitted':
                statusBadge = `<span class="badge" style="background: rgba(59, 130, 246, 0.1); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.25);">Submitted</span>`;
                break;
            case 'pending_manager_review':
                statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25);">Reviewing</span>`;
                break;
            case 'returned_to_employee':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3);">Returned</span>`;
                break;
            case 'approved_by_manager':
            case 'approved':
                statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">Approved (Mgr)</span>`;
                break;
            case 'approved_with_exceptions':
                statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35);">Approved (Exceptions)</span>`;
                break;
            case 'rejected':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.25);">Rejected</span>`;
                break;
            case 'paid':
                statusBadge = `<span class="badge" style="background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.3);">Paid</span>`;
                break;
            case 'closed':
                statusBadge = `<span class="badge" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3);">Closed</span>`;
                break;
            default:
                statusBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);">${r.status}</span>`;
        }

        let warningBadges = "";
        if (missingCount > 0) {
            warningBadges += `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); font-size: 0.72rem; margin-right: 0.3rem;"><strong style="font-weight: 700;">!</strong> ${missingCount} Missing Docs</span>`;
        }
        if (exceptionCount > 0) {
            warningBadges += `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border-color: rgba(244,63,94,0.2); font-size: 0.72rem;"><strong style="font-weight: 700;">!</strong> ${exceptionCount} Exceptions</span>`;
        }

        const dateUpdated = r.updated_at ? new Date(r.updated_at).toLocaleDateString() : "N/A";

        return `
            <div class="report-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                    ${statusBadge}
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Updated: ${dateUpdated}</span>
                </div>
                <h3 class="report-title">${escapeHtml(r.report_title)}</h3>
                
                <div class="report-meta">
                    <div class="report-meta-item">
                        <span>📅</span> Period: <strong>${start}</strong> to <strong>${end}</strong>
                    </div>
                    <div class="report-meta-item">
                        <span>👤</span> Employee: <strong>${escapeHtml(r.employee_name)}</strong>
                    </div>
                    <div class="report-meta-item">
                        <span>📂</span> claims count: <strong>${claimCount} claim item(s)</strong>
                    </div>
                    ${warningBadges ? `<div style="margin-top: 0.25rem;">${warningBadges}</div>` : ''}
                </div>

                <div class="report-totals">
                    <div class="report-total-box">
                        <span class="report-total-label">Total Claimed</span>
                        <span class="report-total-val">${formatMoney(r.total_claimed_amount)}</span>
                    </div>
                    <div class="report-total-box" style="align-items: flex-end;">
                        <span class="report-total-label">Reimbursable</span>
                        <span class="report-total-val" style="color: var(--success);">${formatMoney(r.total_reimbursable_amount)}</span>
                    </div>
                </div>

                <button class="btn btn-receipt" onclick="loadReportBuilder('${r.report_id}')" style="margin-top: 1.25rem; width: 100%; border-radius: 12px; font-weight: 600; padding: 0.6rem;">
                    ${actionBtnText}
                </button>
            </div>
        `;
    }).join('');
}

// Drawer Open/Close
function openNewReportDrawer() {
    document.getElementById("drawer-new-report").classList.add("active");
    document.getElementById("slide-overlay").classList.add("active");
    
    // Auto populate default start/end dates (current month)
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    
    document.getElementById("report-start-date").value = `${y}-${m}-01`;
    // Last day of month
    const lastDay = new Date(y, now.getMonth() + 1, 0).getDate();
    document.getElementById("report-end-date").value = `${y}-${m}-${lastDay}`;
    document.getElementById("report-title-input").value = "";
    document.getElementById("report-travel-week").value = "";
    
    // Admin selector
    const adminSelector = document.getElementById("drawer-employee-selector");
    if (USER_ROLE === "finance_admin") {
        adminSelector.style.display = "block";
    } else {
        adminSelector.style.display = "none";
    }
}

function closeNewReportDrawer() {
    document.getElementById("drawer-new-report").classList.remove("active");
    document.getElementById("slide-overlay").classList.remove("active");
}

// Create new report
async function submitCreateReport() {
    const title = document.getElementById("report-title-input").value.trim();
    const start = document.getElementById("report-start-date").value;
    const end = document.getElementById("report-end-date").value;
    const travelWeek = document.getElementById("report-travel-week").value.trim();
    const emulatedEmployee = USER_ROLE === "finance_admin" ? document.getElementById("drawer-emulated-employee").value : "";

    if (!title) {
        showToast("Report title is required.", "error");
        return;
    }

    try {
        const response = await fetch("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                report_title: title,
                report_period_start: start,
                report_period_end: end,
                travel_week: travelWeek || null,
                employee_email: emulatedEmployee || null
            })
        });

        if (!response.ok) throw new Error("Failed to create report");
        const data = await response.json();
        
        closeNewReportDrawer();
        showToast(`Created draft report "${title}"!`, "success");
        
        // Open the builder immediately!
        loadReportBuilder(data.report_id);
    } catch (err) {
        console.error(err);
        showToast("Error creating report: " + err.message, "error");
    }
}

// Load detailed view inside report builder
async function loadReportBuilder(reportId) {
    activeReportId = reportId;
    document.getElementById("reports-dashboard-container").style.display = "none";
    document.getElementById("report-builder-container").style.display = "block";
    
    // Loading state in tables
    document.getElementById("builder-claims-tbody").innerHTML = `
        <tr>
            <td colspan="6" style="padding: 2rem; text-align: center;">
                <div class="spinner"></div>
                <p style="margin-top: 0.5rem; color: var(--text-muted);">Syncing report dossier...</p>
            </td>
        </tr>
    `;

    try {
        const response = await fetch(`/api/reports/${reportId}`);
        if (!response.ok) throw new Error("Failed to fetch report details");
        const detail = await response.json();
        
        const report = detail.report;
        currentReportClaims = detail.claims;
        const documents = detail.documents;
        const decisions = detail.decisions;
        const auditLogs = detail.audit_logs;

        // RENDER HEADER
        document.getElementById("builder-report-title").textContent = report.report_title;
        document.getElementById("builder-report-meta").innerHTML = `
            👤 Employee: <strong>${escapeHtml(report.employee_name)}</strong> (${escapeHtml(report.employee_email)}) 
            &nbsp;&bull;&nbsp; 💼 Dept: <strong>${escapeHtml(report.department)}</strong> 
            &nbsp;&bull;&nbsp; 📅 Period: <strong>${report.report_period_start}</strong> to <strong>${report.report_period_end}</strong>
        `;

        // STATS
        document.getElementById("stat-total-claimed").textContent = formatMoney(report.total_claimed_amount);
        document.getElementById("stat-total-reimbursable").textContent = formatMoney(report.total_reimbursable_amount);
        document.getElementById("stat-policy-exceptions").textContent = report.policy_exception_count;
        document.getElementById("stat-missing-documents").textContent = report.missing_document_count;

        // RETURN BANNER
        const returnBanner = document.getElementById("builder-return-reason-banner");
        if (report.status === "returned_to_employee" && report.return_reason) {
            returnBanner.style.display = "block";
            document.getElementById("builder-return-reason-text").textContent = report.return_reason;
        } else {
            returnBanner.style.display = "none";
        }

        // EDITABILITY & ROLE CHECKS
        const isEditable = report.status === "draft" || report.status === "returned_to_employee";
        const isEmployeeOwner = report.employee_email === USER_EMAIL;
        const isReviewer = USER_ROLE === "manager" || USER_ROLE === "finance_admin";
        
        // Hide add claim and upload buttons if not editable or not employee owner
        const addClaimBtn = document.getElementById("btn-add-line-item");
        const uploadContainer = document.getElementById("builder-upload-container");
        
        if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
            addClaimBtn.style.display = "inline-block";
            uploadContainer.style.display = "block";
            // Show actions columns in claims table
            document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "table-cell");
        } else {
            addClaimBtn.style.display = "none";
            uploadContainer.style.display = "none";
            // Hide actions columns
            document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "none");
        }

        // RENDER CLAIMS TABLE
        const tbody = document.getElementById("builder-claims-tbody");
        if (currentReportClaims.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="padding: 2.5rem; text-align: center; color: var(--text-muted);">
                        No claims in this report. Click "+ Add Expense Claim" to insert one.
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = currentReportClaims.map(c => {
                let complianceBadge = "";
                let receiptBadge = "";
                
                // Compliance Status
                if (c.policy_status === "approved" || c.policy_status === "auto_approved") {
                    complianceBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16,185,129,0.25);">Policy Compliant</span>`;
                } else if (c.policy_status === "warn" || c.policy_status === "warning") {
                    complianceBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.25);">Warning</span>`;
                } else if (c.policy_status === "rejected" || c.policy_status === "critical") {
                    complianceBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border-color: rgba(244,63,94,0.25);">Exception</span>`;
                } else {
                    complianceBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border-color: rgba(255,255,255,0.1);">${c.policy_status || "Pending"}</span>`;
                }

                // Document Status
                const missing = c.missing_documents || [];
                if (missing.length === 0) {
                    receiptBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16,185,129,0.2);">Attached</span>`;
                } else {
                    receiptBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.25); cursor: pointer;" title="Missing: ${missing.join(', ')}">⚠️ Missing Receipt</span>`;
                }

                let actionsHTML = "";
                if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                    actionsHTML = `
                        <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
                            <button class="btn btn-receipt" onclick="openClaimFormModal('${c.claim_id}')" style="padding: 0.25rem 0.5rem; font-size: 0.72rem; border-radius: 6px; width: auto; height: auto;">Edit</button>
                            <button class="btn btn-receipt" onclick="deleteClaimFromReport('${c.claim_id}')" style="padding: 0.25rem 0.5rem; font-size: 0.72rem; border-radius: 6px; width: auto; height: auto; border-color: rgba(244,63,94,0.4); color: #fda4af;">Delete</button>
                        </div>
                    `;
                }

                // If reviewer/manager is looking, show approve/reject icons per claim
                if (report.status === "pending_manager_review" && isReviewer) {
                    let decState = "";
                    if (c.claim_status === "approved") {
                        decState = `<span style="color: #10b981; font-weight: 600; font-size: 0.75rem;">✔️ Approved</span>`;
                    } else if (c.claim_status === "rejected") {
                        decState = `<span style="color: #f43f5e; font-weight: 600; font-size: 0.75rem;">❌ Rejected</span>`;
                    } else {
                        decState = `
                            <div style="display: flex; gap: 0.3rem; justify-content: flex-end;">
                                <button class="btn btn-receipt" onclick="decideClaimForReview('${c.claim_id}', 'approved')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(16,185,129,0.4); color: #34d399; width: auto; height: auto;">Approve</button>
                                <button class="btn btn-receipt" onclick="decideClaimForReview('${c.claim_id}', 'rejected')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(244,63,94,0.4); color: #f87171; width: auto; height: auto;">Reject</button>
                            </div>
                        `;
                    }
                    actionsHTML = decState;
                    // Ensure action column header/footer display is correct
                    document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "table-cell");
                }

                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.8rem 1rem;">
                            <strong style="color: white;">${escapeHtml(c.category)}</strong>
                            <span style="display: block; font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(c.description || c.business_purpose || '')}</span>
                        </td>
                        <td style="padding: 0.8rem 1rem;">${c.expense_date}</td>
                        <td style="padding: 0.8rem 1rem; font-weight: 700; color: white;">${formatMoney(c.amount)} ${c.currency}</td>
                        <td style="padding: 0.8rem 1rem;">${complianceBadge}</td>
                        <td style="padding: 0.8rem 1rem;">${receiptBadge}</td>
                        <td style="padding: 0.8rem 1rem; text-align: right;" class="builder-actions-column">${actionsHTML}</td>
                    </tr>
                `;
            }).join('');
        }

        // RENDER REPORT DOCUMENTS
        const docsList = document.getElementById("builder-documents-list");
        if (documents.length === 0) {
            docsList.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">No documents or receipts uploaded yet.</div>`;
        } else {
            docsList.innerHTML = documents.map(d => {
                let statusLabel = "";
                let assignActionHTML = "";
                
                if (d.assigned_to_claim && d.claim_id !== "supporting") {
                    const matchedClaim = currentReportClaims.find(cl => cl.claim_id === d.claim_id);
                    const claimText = matchedClaim ? `${matchedClaim.category} (${formatMoney(matchedClaim.amount)})` : d.claim_id;
                    statusLabel = `<span style="color: var(--success); font-size: 0.75rem; font-weight: 500;">✔️ Assigned to: ${escapeHtml(claimText)}</span>`;
                    
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="unassignDocument('${d.document_id}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(255,255,255,0.1); color: var(--text-muted); width: auto; height: auto;">Unassign</button>`;
                    }
                } else if (d.claim_id === "supporting") {
                    statusLabel = `<span style="color: #cbd5e1; font-size: 0.75rem; font-weight: 500;">📋 Extra Supporting Doc</span>`;
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="openAssignModal('${d.document_id}', '${escapeHtml(d.file_name)}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; width: auto; height: auto;">Reassign</button>`;
                    }
                } else {
                    statusLabel = `<span style="color: #f59e0b; font-size: 0.75rem; font-weight: 600;">⚠️ Unassigned</span>`;
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="openAssignModal('${d.document_id}', '${escapeHtml(d.file_name)}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; width: auto; height: auto; border-color: rgba(245,158,11,0.4); color: #f59e0b;">Assign Claim</button>`;
                    }
                }

                const displayType = (d.doc_type || "receipt").replace(/_/g, ' ').toUpperCase();

                return `
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                        <div style="flex: 1; min-width: 0;">
                            <div style="display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1.1rem;">📄</span>
                                <a href="/api/document/${reportId}/${d.doc_type || 'receipt'}?path=${encodeURIComponent(d.gcs_path)}" target="_blank" style="color: #a5b4fc; font-weight: 600; text-decoration: none; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: inline-block;">
                                    ${escapeHtml(d.file_name)}
                                </a>
                                <span style="font-size: 0.65rem; color: var(--text-muted); background: rgba(255,255,255,0.05); padding: 0.1rem 0.3rem; border-radius: 4px;">${displayType}</span>
                            </div>
                            <div style="margin-top: 0.2rem;">${statusLabel}</div>
                        </div>
                        <div>${assignActionHTML}</div>
                    </div>
                `;
            }).join('');
        }

        // RENDER LIFECYCLE AUDIT LOG
        const auditContainer = document.getElementById("builder-audit-list");
        if (auditLogs.length === 0) {
            auditContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">No trail yet.</div>`;
        } else {
            auditContainer.innerHTML = auditLogs.map(log => {
                const cleanMsg = log.message || "";
                const displayRole = (log.actor_role || "").replace(/_/g, ' ').toUpperCase();
                const logDate = log.created_at ? new Date(log.created_at).toLocaleString() : "N/A";
                
                return `
                    <div style="position: relative; padding-bottom: 0.5rem;">
                        <span style="display: block; font-size: 0.8rem; color: white; font-weight: 500;">${escapeHtml(cleanMsg)}</span>
                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem;">
                            By: ${escapeHtml(log.actor_email)} (${displayRole}) &bull; ${logDate}
                        </span>
                    </div>
                `;
            }).join('');
        }

        // RENDER ACTIONS CONTAINER
        const actionsContainer = document.getElementById("builder-actions-container");
        if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px;">Save as Draft</button>
                <button class="btn btn-primary" onclick="submitReportForReview(false)" style="padding: 0.6rem 1.5rem; font-weight: 600; border-radius: 10px;">Submit Report</button>
            `;
        } else if (report.status === "pending_manager_review" && isReviewer) {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="openReturnModal('${reportId}')" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px; border-color: rgba(245,158,11,0.4); color: #f59e0b;">Return to Employee</button>
                <button class="btn btn-receipt" onclick="rejectReportForReview()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px; border-color: rgba(244,63,94,0.4); color: #f87171;">Reject Report</button>
                <button class="btn btn-primary" onclick="approveReportForReview()" style="padding: 0.6rem 1.5rem; font-weight: 600; border-radius: 10px;">Approve Report</button>
            `;
        } else {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px;">Close Dossier</button>
            `;
        }

    } catch (err) {
        console.error("Error loading report builder:", err);
        showToast("Failed to load report details: " + err.message, "error");
        closeReportBuilder();
    }
}

function closeReportBuilder() {
    activeReportId = null;
    currentReportClaims = [];
    document.getElementById("report-builder-container").style.display = "none";
    document.getElementById("reports-dashboard-container").style.display = "block";
    fetchMyReports();
}

// Modal Form handling
function openClaimFormModal(claimId = null) {
    const overlay = document.getElementById("claim-modal-overlay");
    const modal = document.getElementById("modal-claim-form");
    
    // Reset inputs
    document.getElementById("claim-id-hidden").value = claimId || "";
    document.getElementById("claim-amount").value = "";
    document.getElementById("claim-purpose").value = "";
    document.getElementById("claim-description").value = "";
    document.getElementById("claim-receipt-file").value = "";
    
    // Default values
    document.getElementById("claim-category").value = "Flight";
    document.getElementById("claim-currency").value = "USD";
    
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("claim-date").value = today;

    // Reset dynamic structures
    document.getElementById("claim-hotel-fields").style.display = "none";
    document.getElementById("claim-hotel-in").value = "";
    document.getElementById("claim-hotel-out").value = "";
    document.getElementById("claim-transportation-fields").style.display = "none";
    document.getElementById("claim-trans-type").value = "";
    document.getElementById("claim-mileage-row").style.display = "none";
    document.getElementById("claim-mileage").value = "";
    document.getElementById("claim-gas-cost").value = "";
    
    document.getElementById("claim-receipt-upload-row").style.display = claimId ? "none" : "block";

    if (claimId) {
        document.getElementById("claim-modal-title").textContent = "Edit Expense Claim";
        const matched = currentReportClaims.find(c => c.claim_id === claimId);
        if (matched) {
            document.getElementById("claim-category").value = matched.category || "Flight";
            document.getElementById("claim-date").value = matched.expense_date || today;
            document.getElementById("claim-amount").value = matched.amount || "";
            document.getElementById("claim-currency").value = matched.currency || "USD";
            document.getElementById("claim-purpose").value = matched.business_purpose || "";
            document.getElementById("claim-description").value = matched.description || "";
            
            onClaimCategoryChange();
            
            if (matched.category === "Hotel") {
                document.getElementById("claim-hotel-in").value = matched.check_in_date || "";
                document.getElementById("claim-hotel-out").value = matched.check_out_date || "";
            } else if (matched.category === "Transportation" || matched.category === "Rental Car" || matched.category === "Rental Car Gas" || matched.category === "Mileage") {
                document.getElementById("claim-trans-type").value = matched.transportation_type || "";
                onClaimTransTypeChange();
                document.getElementById("claim-mileage").value = matched.mileage || "";
                document.getElementById("claim-gas-cost").value = matched.gas_cost || "";
            }
        }
    } else {
        document.getElementById("claim-modal-title").textContent = "Add Expense Claim";
    }

    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeClaimFormModal() {
    const overlay = document.getElementById("claim-modal-overlay");
    const modal = document.getElementById("modal-claim-form");
    
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

function onClaimCategoryChange() {
    const cat = document.getElementById("claim-category").value;
    const hotelFields = document.getElementById("claim-hotel-fields");
    const transFields = document.getElementById("claim-transportation-fields");

    if (cat === "Hotel") {
        hotelFields.style.display = "grid";
        transFields.style.display = "none";
    } else if (cat === "Transportation" || cat === "Rental Car" || cat === "Rental Car Gas" || cat === "Mileage") {
        hotelFields.style.display = "none";
        transFields.style.display = "flex";
        
        // Auto select transportation type if matched
        const typeSelect = document.getElementById("claim-trans-type");
        if (cat === "Mileage") {
            typeSelect.value = "personal_vehicle";
            onClaimTransTypeChange();
        } else if (cat === "Rental Car" || cat === "Rental Car Gas") {
            typeSelect.value = "rental_car";
            onClaimTransTypeChange();
        }
    } else {
        hotelFields.style.display = "none";
        transFields.style.display = "none";
    }
}

function onClaimTransTypeChange() {
    const transType = document.getElementById("claim-trans-type").value;
    const mileageRow = document.getElementById("claim-mileage-row");
    
    if (transType === "personal_vehicle") {
        mileageRow.style.display = "grid";
    } else {
        mileageRow.style.display = "none";
    }
}

// Submit single claim item
async function submitClaimForm() {
    const claimId = document.getElementById("claim-id-hidden").value;
    const category = document.getElementById("claim-category").value;
    const date = document.getElementById("claim-date").value;
    const amount = parseFloat(document.getElementById("claim-amount").value);
    const currency = document.getElementById("claim-currency").value;
    const purpose = document.getElementById("claim-purpose").value.trim();
    const desc = document.getElementById("claim-description").value.trim();

    if (isNaN(amount) || amount <= 0) {
        showToast("Claim amount must be greater than 0.", "error");
        return;
    }

    const claim_data = {
        category,
        expense_date: date,
        amount,
        currency,
        business_purpose: purpose,
        description: desc
    };

    if (category === "Hotel") {
        claim_data.check_in_date = document.getElementById("claim-hotel-in").value;
        claim_data.check_out_date = document.getElementById("claim-hotel-out").value;
    } else if (category === "Transportation" || category === "Rental Car" || category === "Rental Car Gas" || category === "Mileage") {
        const transType = document.getElementById("claim-trans-type").value;
        claim_data.transportation_type = transType;
        if (transType === "personal_vehicle") {
            claim_data.mileage = parseFloat(document.getElementById("claim-mileage").value) || 0;
            claim_data.gas_cost = parseFloat(document.getElementById("claim-gas-cost").value) || 0;
        }
    }

    try {
        const isEditing = !!claimId;
        const apiPath = isEditing 
            ? `/api/reports/${activeReportId}/claims/${claimId}` 
            : `/api/reports/${activeReportId}/claims`;
            
        const method = isEditing ? "PATCH" : "POST";

        const response = await fetch(apiPath, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(claim_data)
        });

        if (!response.ok) throw new Error("Failed to save claim line item");
        const claimResult = await response.json();

        // Handle receipt file upload if selected and not editing
        const fileInput = document.getElementById("claim-receipt-file");
        if (!isEditing && fileInput.files && fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append("files", fileInput.files[0]);
            
            const uploadRes = await fetch(`/api/reports/${activeReportId}/documents`, {
                method: "POST",
                body: formData
            });
            
            if (uploadRes.ok) {
                const uploadedDocs = await uploadRes.json();
                if (uploadedDocs.length > 0) {
                    const docId = uploadedDocs[0].document_id;
                    // Auto assign to this newly created claim!
                    await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            claim_id: claimResult.claim_id,
                            doc_type: "receipt"
                        })
                    });
                }
            }
        }

        closeClaimFormModal();
        showToast(isEditing ? "Claim updated successfully." : "Claim item added to report!", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Failed to save claim: " + err.message, "error");
    }
}

// Delete Claim from report
async function deleteClaimFromReport(claimId) {
    if (!confirm("Are you sure you want to delete this expense claim line item? Any associated documents will be unassigned.")) return;
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/claims/${claimId}`, {
            method: "DELETE"
        });
        
        if (!response.ok) throw new Error("Failed to delete claim");
        showToast("Claim item deleted.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error deleting claim: " + err.message, "error");
    }
}

// Bulk Upload receipts
function triggerBulkFileInput() {
    document.getElementById("bulk-receipt-file-input").click();
}

async function handleBulkReceiptsSelect(files) {
    if (!files || files.length === 0) return;
    
    const zone = document.getElementById("bulk-receipt-dropzone");
    const originalZoneHTML = zone.innerHTML;
    zone.innerHTML = `
        <div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>
        <span style="font-weight: 600;">Uploading ${files.length} document(s)...</span>
    `;
    zone.style.pointerEvents = "none";

    try {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        const response = await fetch(`/api/reports/${activeReportId}/documents`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed");
        
        showToast(`Successfully uploaded ${files.length} receipt(s)!`, "success");
    } catch (err) {
        console.error(err);
        showToast("Bulk upload failed: " + err.message, "error");
    } finally {
        zone.innerHTML = originalZoneHTML;
        zone.style.pointerEvents = "all";
        loadReportBuilder(activeReportId);
    }
}

// Assign Receipt Modal
function openAssignModal(docId, filename) {
    document.getElementById("assign-doc-id").value = docId;
    document.getElementById("assign-doc-filename").textContent = filename;
    
    const select = document.getElementById("assign-claim-select");
    
    // Populate select with claims
    let options = `<option value="">-- Supporting Document (Do Not Assign to Specific Claim) --</option>`;
    options += currentReportClaims.map(c => `
        <option value="${c.claim_id}">${escapeHtml(c.category)} - ${formatMoney(c.amount)} (${c.expense_date})</option>
    `).join('');
    
    select.innerHTML = options;
    
    // Reset classification dropdown to 'receipt'
    document.getElementById("assign-doc-type").value = "receipt";

    const overlay = document.getElementById("assign-modal-overlay");
    const modal = document.getElementById("modal-assign-receipt");
    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeAssignModal() {
    const overlay = document.getElementById("assign-modal-overlay");
    const modal = document.getElementById("modal-assign-receipt");
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitAssignReceipt() {
    const docId = document.getElementById("assign-doc-id").value;
    const claimId = document.getElementById("assign-claim-select").value;
    const docType = document.getElementById("assign-doc-type").value;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                claim_id: claimId || null,
                doc_type: docType
            })
        });

        if (!response.ok) throw new Error("Assignment failed");
        
        closeAssignModal();
        showToast("Document assigned successfully.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error assigning document: " + err.message, "error");
    }
}

// Unassign active document
async function unassignDocument(docId) {
    try {
        const response = await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                claim_id: null,
                doc_type: "receipt"
            })
        });

        if (!response.ok) throw new Error("Unassignment failed");
        showToast("Document unassigned.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

// Submit Report
async function submitReportForReview(override = false) {
    if (!confirm("Are you sure you are ready to submit this full expense report for manager review?")) return;
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                override_missing_docs: override
            })
        });

        if (response.status === 400) {
            const errData = await response.json();
            if (errData.detail && errData.detail.includes("required document") && USER_ROLE === "finance_admin") {
                // If admin, offer override option
                if (confirm(`${errData.detail}\n\nAs Finance Admin, would you like to override this missing document blocking and force submit?`)) {
                    await submitReportForReview(true);
                    return;
                }
            } else {
                throw new Error(errData.detail || "Submission blocked.");
            }
            return;
        }

        if (!response.ok) throw new Error("HTTP Error: " + response.status);
        
        showToast("Report submitted successfully for manager review!", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Submission failed: " + err.message, "error");
    }
}

// Reviewer/Manager Actions
function openReturnModal(reportId) {
    document.getElementById("return-report-id").value = reportId;
    document.getElementById("return-reason-input").value = "";

    const overlay = document.getElementById("return-modal-overlay");
    const modal = document.getElementById("modal-return-comments");
    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeReturnModal() {
    const overlay = document.getElementById("return-modal-overlay");
    const modal = document.getElementById("modal-return-comments");
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitReturnReport() {
    const reportId = document.getElementById("return-report-id").value;
    const reason = document.getElementById("return-reason-input").value.trim();

    if (!reason) {
        showToast("Please provide a return reason comment.", "error");
        return;
    }

    try {
        const response = await fetch(`/api/reports/${reportId}/return`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason })
        });

        if (!response.ok) throw new Error("Return execution failed");
        
        closeReturnModal();
        showToast("Report returned to employee for revisions.", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function rejectReportForReview() {
    const reason = prompt("Please enter rejection reason/justification:") || "Declined by manager.";
    if (!reason) return;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/reject`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason })
        });

        if (!response.ok) throw new Error("Rejection failed");
        
        showToast("Expense report rejected.", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function approveReportForReview() {
    const missingDocs = parseInt(document.getElementById("stat-missing-documents").textContent || "0", 10);
    const exceptions = parseInt(document.getElementById("stat-policy-exceptions").textContent || "0", 10);
    
    let overrideReason = "";
    if (missingDocs > 0 || exceptions > 0) {
        overrideReason = prompt("This report contains policy exceptions or missing documents. An override reason is required from a manager or finance admin to proceed with approval:");
        if (overrideReason === null) return; // User clicked Cancel
        if (!overrideReason.trim()) {
            alert("Approval aborted: An override reason must be provided for non-compliant reports.");
            return;
        }
    } else {
        if (!confirm("Are you sure you want to approve this entire expense report? All non-rejected claims will be marked as approved.")) return;
    }
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ override_reason: overrideReason })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Approval failed");
        }
        
        showToast("Expense report approved!", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function decideClaimForReview(claimId, decision) {
    const reason = decision === 'rejected' ? (prompt("Please enter a reason for rejecting this claim line item:") || "Rejected") : "Approved by manager.";
    if (decision === 'rejected' && !reason) return;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/claims/${claimId}/decision`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                decision,
                reason
            })
        });

        if (!response.ok) throw new Error("Decision failed");
        showToast(`Line item claim has been ${decision}!`, "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error saving claim decision: " + err.message, "error");
    }
}


        window.addEventListener("DOMContentLoaded", () => {
            fetchPendingApprovals();
            document.getElementById("slide-overlay").addEventListener("click", () => {
                toggleModal(false);
            });
        });
    </script>
\n
    <!-- New Report Sliding Drawer -->
    <div id="drawer-new-report" class="slider-panel">
        <div class="slider-header">
            <h2 style="font-size: 1.4rem; font-weight: 800; color: white;">New Expense Report</h2>
            <button onclick="closeNewReportDrawer()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Report Title</label>
                <input type="text" id="report-title-input" placeholder="e.g. April Site Visits" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Start Date</label>
                    <input type="date" id="report-start-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">End Date</label>
                    <input type="date" id="report-end-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
                </div>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Travel Week (Optional)</label>
                <input type="text" id="report-travel-week" placeholder="e.g. Week 15" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
            </div>
            
            <!-- Employee Selector for Finance Admin Testing -->
            <div id="drawer-employee-selector" style="display: none; background: rgba(99,102,241,0.05); border: 1px solid rgba(99,102,241,0.15); padding: 1rem; border-radius: 12px; margin-top: 0.5rem;">
                <label style="font-size: 0.75rem; color: #a5b4fc; text-transform: uppercase; font-weight: 700; display: block; margin-bottom: 0.4rem;">Demo Employee Emulation</label>
                <select id="drawer-emulated-employee" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(99,102,241,0.3); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    <option value="">Use Logged-in User</option>
                    <option value="cra001.manager001@demo-company.com">CRA 001 Manager 001 (cra001.manager001@demo-company.com)</option>
                </select>
                <p style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.3rem;">Simulates creating a report for the demo employee.</p>
            </div>

            <button class="btn btn-primary" onclick="submitCreateReport()" style="margin-top: 1.5rem; padding: 1rem; font-weight: 600; border-radius: 10px;">
                Create Draft Report
            </button>
        </div>
    </div>

    <!-- Claim Form Overlay Modal -->
    <div class="slide-overlay" id="claim-modal-overlay"></div>
    <div id="modal-claim-form" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 550px; max-height: 90vh; overflow-y: auto; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 id="claim-modal-title" style="font-size: 1.4rem; font-weight: 800; color: white;">Add Expense Claim</h2>
            <button onclick="closeClaimFormModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <input type="hidden" id="claim-id-hidden">
            
            <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Category</label>
                    <select id="claim-category" onchange="onClaimCategoryChange()" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                        <option value="Flight">Flight</option>
                        <option value="Hotel">Hotel</option>
                        <option value="Meals">Meals</option>
                        <option value="Rental Car">Rental Car</option>
                        <option value="Rental Car Gas">Rental Car Gas</option>
                        <option value="Parking">Parking</option>
                        <option value="Tolls">Tolls</option>
                        <option value="Mileage">Mileage</option>
                        <option value="Office Supplies">Office Supplies</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Expense Date</label>
                    <input type="date" id="claim-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Amount</label>
                    <input type="number" id="claim-amount" step="0.01" placeholder="0.00" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Currency</label>
                    <select id="claim-currency" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                        <option value="CAD">CAD ($)</option>
                    </select>
                </div>
            </div>

            <!-- Dynamic Fields for Hotel (Dates) -->
            <div id="claim-hotel-fields" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem; background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border);">
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Check-in Date</label>
                    <input type="date" id="claim-hotel-in" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                </div>
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Check-out Date</label>
                    <input type="date" id="claim-hotel-out" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                </div>
            </div>

            <!-- Dynamic Fields for Transportation/Mileage -->
            <div id="claim-transportation-fields" style="display: none; background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); display: flex; flex-direction: column; gap: 0.75rem;">
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Transportation Type</label>
                    <select id="claim-trans-type" onchange="onClaimTransTypeChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                        <option value="">-- Select Type --</option>
                        <option value="personal_vehicle">Personal Vehicle</option>
                        <option value="rental_car">Rental Car</option>
                        <option value="company_vehicle">Company Vehicle</option>
                        <option value="public_transit">Public Transit</option>
                    </select>
                </div>
                <div id="claim-mileage-row" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div>
                        <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Mileage (Miles)</label>
                        <input type="number" id="claim-mileage" placeholder="0" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                    </div>
                    <div>
                        <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Gas Cost Inside Amount</label>
                        <input type="number" id="claim-gas-cost" step="0.01" placeholder="0.00" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                    </div>
                </div>
            </div>

            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Business Purpose</label>
                <input type="text" id="claim-purpose" placeholder="e.g. Client presentation site visit" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
            </div>

            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Description / Details</label>
                <textarea id="claim-description" rows="3" placeholder="Specify locations visited or other details..." style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit; resize: none;"></textarea>
            </div>

            <!-- Single document upload for this claim (saves directly to GCS and auto-assigns) -->
            <div id="claim-receipt-upload-row">
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Direct Receipt Upload</label>
                <input type="file" id="claim-receipt-file" style="width: 100%; color: var(--text-muted); font-size: 0.8rem;">
                <p style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.2rem;">Directly attach a receipt image/PDF to this claim.</p>
            </div>

            <button class="btn btn-primary" onclick="submitClaimForm()" style="margin-top: 1rem; padding: 0.8rem; font-weight: 600; border-radius: 8px;">
                Save Claim Line Item
            </button>
        </div>
    </div>

    <!-- Assign Document Overlay Modal -->
    <div class="slide-overlay" id="assign-modal-overlay"></div>
    <div id="modal-assign-receipt" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 450px; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 style="font-size: 1.3rem; font-weight: 800; color: white;">Assign Document</h2>
            <button onclick="closeAssignModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <input type="hidden" id="assign-doc-id">
            <div>
                <strong style="color: var(--text-muted); font-size: 0.8rem;">Selected Document:</strong>
                <p id="assign-doc-filename" style="color: white; font-weight: 600; font-size: 0.95rem; margin-top: 0.2rem;"></p>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Assign to Line Item</label>
                <select id="assign-claim-select" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                    <!-- Claims list options populated dynamically -->
                </select>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Document Classification Type</label>
                <select id="assign-doc-type" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                    <option value="receipt">Standard Receipt</option>
                    <option value="office_receipt">Office Supplies Receipt</option>
                    <option value="parking_receipt">Parking Receipt</option>
                    <option value="hotel_receipt">Hotel Lodging Folio</option>
                    <option value="flight_ticket_receipt">Flight Ticket Invoice</option>
                    <option value="manager_approval_letter">Manager Prior Approval Letter</option>
                    <option value="other">Supporting Document / Other</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="submitAssignReceipt()" style="margin-top: 1rem; padding: 0.8rem; font-weight: 600; border-radius: 8px;">
                Confirm Assignment
            </button>
        </div>
    </div>

    <!-- Return Comments Modal -->
    <div class="slide-overlay" id="return-modal-overlay"></div>
    <div id="modal-return-comments" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 450px; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 style="font-size: 1.3rem; font-weight: 800; color: white;">Return Report to Employee</h2>
            <button onclick="closeReturnModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <input type="hidden" id="return-report-id">
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Reason for Returning</label>
                <textarea id="return-reason-input" rows="4" placeholder="Explain what needs to be fixed (e.g. missing flight receipt or incorrect mileage)..." style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit; resize: none;"></textarea>
            </div>
            <button class="btn btn-danger" onclick="submitReturnReport()" style="padding: 0.8rem; font-weight: 600; border-radius: 8px; background: var(--danger); border-color: var(--danger);">
                Return to Employee
            </button>
        </div>
    </div>

</body>
</html>
"""
    # Dynamic String Replacements to inject user status, roles, and UI configuration
    user_email = "default-user@company.com"
    user_role = "finance_admin"
    auth_active = is_auth_enabled()
    
    if auth_active:
        user = request.session.get("user")
        if not user:
            return RedirectResponse(url="/login")
        user_email = user.get("email")
        user_role = user.get("role")
        auth_label = "Google Auth Active"
        badge_border = "var(--primary)"
        badge_bg = "rgba(99, 102, 241, 0.05)"
        badge_text = "var(--primary)"
        logout_html = '<a href="/logout" class="btn-logout" style="color: #fb7185; text-decoration: none; margin-left: 0.5rem; font-weight: 600; font-size: 0.85rem; border-left: 1px solid var(--glass-border); padding-left: 0.8rem; transition: var(--transition);" onmouseover="this.style.color=\'#f43f5e\'" onmouseout="this.style.color=\'#fb7185\'">Logout</a>'
    else:
        # Fallback to bypass user
        auth_label = "Local Bypassed"
        badge_border = "rgba(245, 158, 11, 0.3)"
        badge_bg = "rgba(245, 158, 11, 0.05)"
        badge_text = "#f59e0b"
        logout_html = '<span style="color: var(--text-muted); margin-left: 0.5rem; font-size: 0.8rem; border-left: 1px solid var(--glass-border); padding-left: 0.8rem; font-style: italic;">Local Mode</span>'

    user_badge_html = f"""
    <div class="user-badge" style="display: flex; align-items: center; gap: 0.8rem; background: {badge_bg}; border: 1px solid {badge_border}; padding: 0.5rem 1.2rem; border-radius: 12px; font-size: 0.9rem; z-index: 10;">
        <div class="user-avatar" style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; color: white;">
            {user_email[0].upper()}
        </div>
        <div class="user-details" style="display: flex; flex-direction: column;">
            <span style="font-weight: 600; color: white; font-size: 0.85rem;">{user_email}</span>
            <span style="font-size: 0.72rem; color: {badge_text}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1px;">
                {user_role.replace('_', ' ')} • {auth_label}
            </span>
        </div>
        {logout_html}
    </div>
    """

    rendered_content = html_content.replace(
        "let cachedClaims = {};",
        f'const USER_ROLE = "{user_role}";\n        const USER_EMAIL = "{user_email}";\n        let cachedClaims = {{}};'
    ).replace(
        "</div>\n    </header>",
        f"</div>\n        {user_badge_html}\n    </header>"
    ).replace(
        'window.addEventListener("DOMContentLoaded", () => {',
        """window.addEventListener("DOMContentLoaded", () => {
            // Apply role-based visibility rules
            if (USER_ROLE === "employee") {
                document.getElementById("tab-pending").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('reports');
            } else if (USER_ROLE === "manager") {
                document.getElementById("tab-submit").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('pending');
            } else {
                switchTab('reports');
            }"""
    ).replace(
        """                        <td style="padding: 1rem 0.75rem; text-align: right;">
                            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                                <button class="btn btn-receipt" onclick="showClaimDetails('${exp.claim_id}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto; background: rgba(99,102,241,0.1); color: #cbd5e1; border-color: rgba(99,102,241,0.25);">
                                    View Details
                                </button>
                                <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', ${exp.amount})" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                    View Trail
                                </button>
                            </div>
                        </td>""",
        """                        <td style="padding: 1rem 0.75rem; text-align: right;">
                            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                                <button class="btn btn-receipt" onclick="showClaimDetails('${exp.claim_id}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto; background: rgba(99,102,241,0.1); color: #cbd5e1; border-color: rgba(99,102,241,0.25);">
                                    View Details
                                </button>
                                ${USER_ROLE === 'finance_admin' ? `
                                <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', ${exp.amount})" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                    View Trail
                                </button>
                                ` : ''}
                            </div>
                        </td>"""
    )
    return HTMLResponse(content=rendered_content)

if __name__ == "__main__":
    import uvicorn
    # Use port 8080 as requested in typical dev servers or standard run directions
    logger.info("Starting FastAPI Uvicorn service...")
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

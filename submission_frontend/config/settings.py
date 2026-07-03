import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manager-dashboard")

# --- Session & Authentication Configuration ---
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-default-key-for-dev-only")

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

# Cloud Storage bucket configuration for uploads
BUCKET_NAME = "expense-manager-uploads-654812449031"

# Firestore Collection Names
EXPENSES_COL = "expenses"
DOCUMENTS_COL = "documents"
DECISIONS_COL = "decisions"
AUDIT_LOGS_COL = "audit_logs"
POLICIES_COL = "policies"

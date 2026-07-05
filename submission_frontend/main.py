import os
import re
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manager-dashboard")

# Import settings, constants, and credentials
from submission_frontend.config.settings import (
    PROJECT_ID,
    AGENT_RUNTIME_ID,
    BUCKET_NAME,
    SESSION_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    ALLOWED_ADMIN_EMAILS,
    ALLOWED_MANAGER_EMAILS,
    ALLOWED_EMPLOYEE_DOMAIN,
    EXPENSES_COL,
    DOCUMENTS_COL,
    DECISIONS_COL,
    AUDIT_LOGS_COL,
    POLICIES_COL
)

# Initialize and warm Vertex AI reasoning engines
import submission_frontend.services.vertexai_service

# Import Firestore DB client and seeding utility
from submission_frontend.services.firestore_service import db, seed_demo_employees

# Import Auth & Helper functions
from submission_frontend.middleware.auth import (
    is_auth_enabled,
    resolve_role,
    get_current_user_and_role,
    get_redirect_uri
)

# Import Core Helpers & Sanitizers
from submission_frontend.utilities.helpers import (
    add_audit_log,
    enrich_claim_with_employee_info,
    filter_and_enrich_claims,
    sanitize_claim_dict
)

# Initialize FastAPI Application
app = FastAPI(title="Manager Expense Approval Dashboard")

@app.middleware("http")
async def clear_cache_on_mutation(request: Request, call_next):
    if request.method in ["POST", "PATCH", "DELETE"]:
        try:
            from submission_frontend.routes import api_routes
            api_routes._pending_cache.clear()
            api_routes._expenses_cache.clear()
            logger.info("Cleared API caches due to mutation request: %s %s", request.method, request.url.path)
        except Exception as e:
            logger.error(f"Error clearing caches in middleware: {e}")
    response = await call_next(request)
    return response

# Session Middleware Configuration (1 day session expiry)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, max_age=86400)

# Mount Static Files Directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Import and Include Modular Routers
from submission_frontend.routes import auth_routes, ui_routes, api_routes

app.include_router(auth_routes.router)
app.include_router(ui_routes.router)
app.include_router(api_routes.router)

# Dynamic Cloud Storage Bucket function targeting the expected BUCKET_NAME
def get_gcs_bucket():
    """
    Returns the storage bucket instance for manager uploads.
    """
    client = storage.Client(project=PROJECT_ID)
    return client.bucket(BUCKET_NAME)

if __name__ == "__main__":
    import uvicorn
    # Use port 8080 as requested in typical dev servers or standard run directions
    logger.info("Starting FastAPI Uvicorn service...")
    uvicorn.run("submission_frontend.main:app", host="0.0.0.0", port=8080, reload=True)

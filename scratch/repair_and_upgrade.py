import os

original_main_path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
api_routes_path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\submission_frontend\routes\api_routes.py"

if not os.path.exists(original_main_path):
    print(f"Error: {original_main_path} does not exist.")
    exit(1)

print("Reading original_main.py...")
with open(original_main_path, "r", encoding="utf-16") as f:
    lines = f.readlines()

print(f"Total lines read: {len(lines)}")

# Line 1485 to 4508 inclusive correspond to index 1484 to 4507 inclusive.
start_idx = 1484
end_idx = 4507

api_lines = lines[start_idx:end_idx + 1]
api_code = "".join(api_lines)

# Replace decorators
api_code = api_code.replace("@app.get(", "@router.get(")
api_code = api_code.replace("@app.post(", "@router.post(")
api_code = api_code.replace("@app.put(", "@router.put(")
api_code = api_code.replace("@app.delete(", "@router.delete(")
api_code = api_code.replace("@app.patch(", "@router.patch(")

header = """import os
import re
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List
from google.cloud import firestore
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
from google.adk.sessions import VertexAiSessionService

# Dynamic Global Delegation class to allow unit tests to patch globals on main
class DynamicGlobal:
    def __init__(self, name):
        self.name = name
    def __getattr__(self, item):
        import submission_frontend.main as main
        actual = getattr(main, self.name)
        return getattr(actual, item)
    def __bool__(self):
        import submission_frontend.main as main
        actual = getattr(main, self.name)
        return bool(actual)
    def __call__(self, *args, **kwargs):
        import submission_frontend.main as main
        actual = getattr(main, self.name)
        return actual(*args, **kwargs)

# Instantiated Dynamic Globals mapped to main's attributes
db = DynamicGlobal("db")
logger = DynamicGlobal("logger")
get_current_user_and_role = DynamicGlobal("get_current_user_and_role")
get_gcs_bucket = DynamicGlobal("get_gcs_bucket")
is_auth_enabled = DynamicGlobal("is_auth_enabled")

# Constants
from submission_frontend.config.settings import (
    BUCKET_NAME,
    PROJECT_ID,
    EXPENSES_COL,
    DOCUMENTS_COL,
    DECISIONS_COL,
    AUDIT_LOGS_COL,
    POLICIES_COL,
    LOCATION,
    ENGINE_ID,
    AGENT_RUNTIME_ID
)

from submission_frontend.schemas.schemas import ApprovalAction

# Imported Utilities
from submission_frontend.utilities.helpers import (
    add_audit_log,
    enrich_claim_with_employee_info,
    filter_and_enrich_claims,
    sanitize_claim_dict
)
from submission_frontend.utilities.policy_engine import (
    run_per_diem_check,
    run_policy_check_py
)
from submission_frontend.utilities.workflow_engine import (
    find_and_bind_expense,
    reevaluate_expense_policies,
    sync_completed_sessions,
    parse_claim_from_session,
    check_claim_missing_documents,
    recalculate_report_totals,
    add_report_audit_log
)

import time
import logging

# Suppress noisy informational logs from google-genai and Vertex AI libraries
for logger_name in ["google", "google_genai", "google.genai", "google_genai._api_client", "google_genai.api_client"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Module-level caching for dashboard performance tuning
_pending_cache = {}  # key: params_tuple, value: (timestamp, data_dict)
_pending_cache_ttl = 30.0  # cache TTL in seconds

_expenses_cache = {}  # key: params_tuple, value: (timestamp, expenses_list)
_expenses_cache_ttl = 30.0  # cache TTL in seconds

router = APIRouter()
"""

# Let's save the code
os.makedirs(os.path.dirname(api_routes_path), exist_ok=True)
with open(api_routes_path, "w", encoding="utf-8") as f:
    f.write(header + "\n" + api_code)

print(f"Successfully extracted {len(api_lines)} lines to {api_routes_path}")

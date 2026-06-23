import os
import sys
import asyncio
import json

# Force UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add submission_frontend to path so we can import modules
sys.path.append(os.path.abspath("submission_frontend"))

import main
from google.adk.sessions import VertexAiSessionService

async def run_trigger():
    print("=== Triggering Per Diem Session Bindings programmatically ===")
    project = "project-5d38f91a-29a3-45bd-8d4"
    location = "us-west1"
    engine_id = "8516245322706452480"
    
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    
    print(f"Initializing VertexAiSessionService for project={project}, location={location}, engine={engine_id}")
    s = VertexAiSessionService(
        project=project,
        location=location,
        agent_engine_id=engine_id
    )
    
    print("Listing sessions from Vertex AI...")
    list_resp = await s.list_sessions(app_name="app")
    print(f"Found {len(list_resp.sessions)} sessions total.")
    
    # Sort sessions by recency
    sessions_sorted = sorted(
        list_resp.sessions,
        key=lambda x: getattr(x, "last_update_time", 0.0),
        reverse=True
    )
    
    # Scan the 30 most recent active non-cli sessions
    active_summaries = [sess for sess in sessions_sorted if sess.user_id != "cli-user"][:30]
    print(f"Scanning up to {len(active_summaries)} active sessions for pending input...")
    
    target_emails = [
        "employee.ny.within@company.com",
        "employee.ny.over@company.com",
        "employee.sc.over@company.com",
        "employee.mn.within@company.com",
        "employee.unknown.policy@company.com"
    ]
    
    bound_count = 0
    for summary in active_summaries:
        try:
            sess = await asyncio.wait_for(
                s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id),
                timeout=5.0
            )
            if not sess:
                continue
                
            # Check for unresolved calls
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
            
            is_per_diem = str(sess.user_id).startswith("perdiem-user-")
            if unresolved_calls or is_per_diem:
                claim_details = main.parse_claim_from_session(sess)
                emp_email = claim_details.get("employee_email")
                emp_name = claim_details.get("employee_name")
                
                # Try to find target email
                matched_email = None
                if emp_email in target_emails:
                    matched_email = emp_email
                elif emp_name in target_emails:
                    matched_email = emp_name
                elif is_per_diem:
                    idx_str = str(sess.user_id).replace("perdiem-user-", "")
                    try:
                        idx = int(idx_str) - 1
                        if 0 <= idx < len(target_emails):
                            matched_email = target_emails[idx]
                            claim_details["employee_email"] = matched_email
                            # Also set employee_name or any other details if they help match
                            claim_details["employee_name"] = "Unknown Claimant"
                    except Exception as ex:
                        print(f"Error mapping index: {ex}", file=sys.stderr)
                
                if matched_email:
                    print(f"\nProcessing active session {sess.id} for {matched_email}:")
                    # Run find_and_bind_expense
                    expense_data, claim_id = await asyncio.to_thread(
                        main.find_and_bind_expense, sess.id, sess.user_id, claim_details
                    )
                    print(f"  Bound to Claim ID: {claim_id}")
                    print(f"  Status updated to: {expense_data.get('status')}")
                    print(f"  Policy status:     {expense_data.get('policy_status')}")
                    bound_count += 1
                    
        except Exception as e:
            print(f"Error checking session {summary.id}: {e}", file=sys.stderr)
            
    print(f"\nCompleted per diem session binding. Bound {bound_count} sessions.")

if __name__ == "__main__":
    asyncio.run(run_trigger())

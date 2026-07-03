"""
Workflow Engine for Enterprise Expense Report Management.
Coordinates claims matching, policy status re-evaluations, document assignments,
recalculating report totals, and synchronizing completed reasoning engine sessions.
"""

import re
import uuid
from datetime import datetime
from pydantic import BaseModel
from google.adk.sessions import VertexAiSessionService
from submission_frontend.config.settings import (
    logger,
    EXPENSES_COL,
    DOCUMENTS_COL,
    DECISIONS_COL,
    PROJECT_ID,
    LOCATION,
    ENGINE_ID
)
from submission_frontend.services.firestore_service import db
from submission_frontend.utilities.policy_engine import run_policy_check_py, run_per_diem_check
from submission_frontend.utilities.helpers import add_audit_log

class ApprovalAction(BaseModel):
    approved: bool
    interrupt_id: str = "review_decision"
    override_reason: str | None = None

# Regex fallback for extracting claim details from interrupt message if first user JSON is unparseable
DETAIL_RE = re.compile(r"Expense of \$([0-9.,]+) by (.*?) for '(.*?)'", re.IGNORECASE)

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
        "company_id": "demo_company",
        "employee_email": None
    }
    
    # 1. Search for JSON in first user message
    for event in sess.events:
        if event.author == "user" and event.content and event.content.parts:
            text = "".join([part.text for part in event.content.parts if getattr(part, "text", None)])
            if text:
                # Basic JSON cleanup
                try:
                    import json
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        raw_claim = json.loads(json_match.group(0))
                        for k, v in raw_claim.items():
                            if k in details:
                                if k == "amount":
                                    try:
                                        details[k] = float(v)
                                    except ValueError:
                                        pass
                                else:
                                    details[k] = v
                        break
                except Exception:
                    pass
                    
    # 2. Fallback: Parse the user interrupt or model function call parameters
    has_amount = details["amount"] > 0.0
    if not has_amount or details["employee_name"] == "Unknown Claimant":
        for event in sess.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and fc.name == "adk_request_input":
                        args = fc.args
                        msg = args.get("message") or ""
                        match = DETAIL_RE.search(msg)
                        if match:
                            try:
                                if not has_amount:
                                    details["amount"] = float(match.group(1).replace(",", ""))
                                if details["employee_name"] == "Unknown Claimant":
                                    details["employee_name"] = match.group(2).strip()
                                if details["description"] == "No description provided":
                                    details["description"] = match.group(3).strip()
                            except Exception:
                                pass
                                
    # Run per diem integration review to enrich details
    try:
        pdr = run_per_diem_check(details)
        details["per_diem_review"] = pdr
        if pdr.get("company_id"):
            details["company_id"] = pdr.get("company_id")
        if pdr.get("employee_email"):
            details["employee_email"] = pdr.get("employee_email")
    except Exception as e:
        logger.warning(f"Error enriching claim parsed from session: {e}")
        
    return details

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

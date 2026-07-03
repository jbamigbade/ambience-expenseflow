import os

file_path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\submission_frontend\routes\api_routes.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's locate the start of get_pending
get_pending_target = """@router.get("/api/pending")
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
):"""

# Let's make sure we find it. If not, let's search with slightly different whitespace
if get_pending_target not in content:
    print("Error: Target get_pending_target not found in api_routes.py")
    exit(1)

# We want to replace everything from get_pending_target up to the next route:
# "@router.post(\"/api/action/{session_id}\")"
get_pending_end_target = '@router.post("/api/action/{session_id}")'
if get_pending_end_target not in content:
    print("Error: Target get_pending_end_target not found")
    exit(1)

start_pos = content.find(get_pending_target)
end_pos = content.find(get_pending_end_target)

# New optimized, cached get_pending implementation
new_get_pending = """@router.get("/api/pending")
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
    source: str = "all",
    refresh: bool = False,
    force_sync: bool = False
):
    \"\"\"
    Queries VertexAiSessionService only when force_sync is True, fetches full histories in parallel,
    and returns sessions with unresolved adk_request_input events.
    Optimized with caching and robust error/timeout fallback.
    \"\"\"
    current_user = get_current_user_and_role(request)
    email = current_user["email"]
    
    cache_key = (source, email, search, department, manager, status, category, company, hide_old_test_sessions, assigned_to_me, show_all_fa, force_sync)
    
    if refresh:
        # Clear caches for this user on manual refresh
        keys_to_del_p = [k for k in _pending_cache if k[1] == email]
        for k in keys_to_del_p:
            _pending_cache.pop(k, None)
        keys_to_del_e = [k for k in _expenses_cache if k[0] == email]
        for k in keys_to_del_e:
            _expenses_cache.pop(k, None)
    else:
        cached_val = _pending_cache.get(cache_key)
        if cached_val:
            ts, data = cached_val
            if time.time() - ts < _pending_cache_ttl:
                logger.info(f"Returning cached pending approvals for user {email}")
                return data

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
    
    pending_claims = []
    hidden_cli_sessions_count = 0
    warning_msg = None
    
    try:
        if force_sync:
            try:
                s = VertexAiSessionService(
                    project=PROJECT_ID,
                    location=LOCATION,
                    agent_engine_id=ENGINE_ID
                )
                
                try:
                    # Individual list sessions fetch timeout of 5.0 seconds
                    list_resp = await asyncio.wait_for(s.list_sessions(app_name="app"), timeout=5.0)
                    
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
                                # Individual session fetch timeout of 3.0 seconds
                                sess = await asyncio.wait_for(
                                    s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id),
                                    timeout=3.0
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
                except Exception as ve:
                    logger.warning(f"Vertex AI Agent Registry fetch timed out or failed: {ve}. Proceeding with offline mode.")
                    warning_msg = f"Agent registry connection slow or offline: {str(ve)}"
            except Exception as outer_e:
                logger.warning(f"Error initializing VertexAiSessionService: {outer_e}")
                warning_msg = f"Agent registry initialization failed: {str(outer_e)}"
                
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
        
        response_data = {
            "pending_claims": sanitized_pending_claims,
            "hidden_cli_sessions_count": hidden_cli_sessions_count
        }
        if warning_msg:
            response_data["warning"] = warning_msg
            
        # Cache the response
        _pending_cache[cache_key] = (time.time(), response_data)
        return response_data
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sessions: {str(e)}"
        )


"""

content = content[:start_pos] + new_get_pending + content[end_pos:]

# Now let's locate and replace get_expenses
get_expenses_target = """@router.get("/api/expenses")
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
):"""

if get_expenses_target not in content:
    print("Error: Target get_expenses_target not found in api_routes.py")
    exit(1)

get_expenses_end_target = '@router.get("/api/expenses/{claim_id}")'
if get_expenses_end_target not in content:
    print("Error: Target get_expenses_end_target not found")
    exit(1)

start_pos_exp = content.find(get_expenses_target)
end_pos_exp = content.find(get_expenses_end_target)

# New optimized get_expenses implementation
new_get_expenses = """@router.get("/api/expenses")
async def get_expenses(
    request: Request,
    background_tasks: BackgroundTasks,
    search: str = None,
    department: str = None,
    manager: str = None,
    status: str = None,
    category: str = None,
    company: str = None,
    hide_old_test_sessions: bool = False,
    assigned_to_me: bool = False,
    show_all_fa: bool = False,
    refresh: bool = False,
    force_sync: bool = False
):
    \"\"\"
    Returns recent expenses from Firestore, syncing completed sessions as a background task only if forced.
    Optimized with caching and background execution to prevent blocking.
    \"\"\"
    current_user = get_current_user_and_role(request)
    email = current_user["email"]
    
    cache_key = (email, search, department, manager, status, category, company, hide_old_test_sessions, assigned_to_me, show_all_fa, force_sync)
    
    if refresh:
        # Clear caches for this user on manual refresh
        keys_to_del_p = [k for k in _pending_cache if k[1] == email]
        for k in keys_to_del_p:
            _pending_cache.pop(k, None)
        keys_to_del_e = [k for k in _expenses_cache if k[0] == email]
        for k in keys_to_del_e:
            _expenses_cache.pop(k, None)
    else:
        cached_val = _expenses_cache.get(cache_key)
        if cached_val:
            ts, expenses_list = cached_val
            if time.time() - ts < _expenses_cache_ttl:
                logger.info(f"Returning cached expenses list for user {email}")
                return expenses_list

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
            if force_sync:
                # Sync completed sessions in background only if forced
                background_tasks.add_task(sync_completed_sessions)
                
            expenses_ref = db.collection(EXPENSES_COL).order_by("created_at", direction=firestore.Query.DESCENDING)
            docs = list(expenses_ref.get())
            all_claims = [doc.to_dict() for doc in docs]
            filtered_claims = filter_and_enrich_claims(all_claims, current_user, params, is_pending=False)
            res = [sanitize_claim_dict(c) for c in filtered_claims]
            
            # Cache the result
            _expenses_cache[cache_key] = (time.time(), res)
            return res
        return []
    except Exception as e:
        logger.error(f"Error fetching expenses from Firestore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch expenses: {str(e)}")


"""

content = content[:start_pos_exp] + new_get_expenses + content[end_pos_exp:]

# Now let's append /api/health, /api/sessions, and /api/claims to the end of the file
extra_routes = """


@router.get("/api/health")
async def get_api_health():
    return {"status": "healthy"}


@router.get("/api/sessions")
async def get_api_sessions(request: Request):
    \"\"\"
    Returns reasoning engine sessions.
    \"\"\"
    try:
        s = VertexAiSessionService(
            project=PROJECT_ID,
            location=LOCATION,
            agent_engine_id=ENGINE_ID
        )
        list_resp = await s.list_sessions(app_name="app")
        sessions_list = []
        for sess in list_resp.sessions:
            sess_dict = {
                "id": sess.id,
                "user_id": sess.user_id,
                "app_name": sess.app_name,
                "state": getattr(sess, "state", {}),
                "last_update_time": getattr(sess, "last_update_time", 0.0)
            }
            sessions_list.append(sess_dict)
        return {"sessions": sessions_list}
    except Exception as e:
        logger.error(f"Error in get_api_sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/claims")
async def get_api_claims(
    request: Request,
    background_tasks: BackgroundTasks,
    search: str = None,
    department: str = None,
    manager: str = None,
    status: str = None,
    category: str = None,
    company: str = None,
    hide_old_test_sessions: bool = False,
    assigned_to_me: bool = False,
    show_all_fa: bool = False,
    refresh: bool = False,
    force_sync: bool = False
):
    return await get_expenses(
        request=request,
        background_tasks=background_tasks,
        search=search,
        department=department,
        manager=manager,
        status=status,
        category=category,
        company=company,
        hide_old_test_sessions=hide_old_test_sessions,
        assigned_to_me=assigned_to_me,
        show_all_fa=show_all_fa,
        refresh=refresh,
        force_sync=force_sync
    )
"""

content = content.strip() + extra_routes + "\n"

# Write the final upgraded content
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully applied upgrades and appended extra endpoints!")

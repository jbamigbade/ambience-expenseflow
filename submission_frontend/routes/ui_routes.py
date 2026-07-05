import os
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

# Deferred import of main is done locally within routes to avoid circular imports

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serves the beautifully stylized glassmorphic Manager Dashboard.
    """
    import submission_frontend.main as main
    auth_active = main.is_auth_enabled()
    
    try:
        user_info = main.get_current_user_and_role(request)
    except Exception:
        return RedirectResponse(url="/login")
        
    # If not authenticated (not in active session), redirect to /login
    if not user_info.get("authenticated") and not request.session.get("user"):
        return RedirectResponse(url="/login")
        
    user_email = user_info.get("email")
    user_role = user_info.get("role")
    
    if auth_active:
        auth_label = "Google OIDC"
        badge_border = "var(--primary)"
        badge_bg = "rgba(99, 102, 241, 0.05)"
        badge_text = "var(--primary)"
    else:
        auth_label = "Local Mode"
        badge_border = "rgba(245, 158, 11, 0.3)"
        badge_bg = "rgba(245, 158, 11, 0.05)"
        badge_text = "#f59e0b"
        
    logout_html = '<a href="/logout" class="btn-logout" style="color: #fb7185; text-decoration: none; margin-left: 0.5rem; font-weight: 600; font-size: 0.85rem; border-left: 1px solid var(--glass-border); padding-left: 0.8rem; transition: var(--transition);" onmouseover="this.style.color=\'#f43f5e\'" onmouseout="this.style.color=\'#fb7185\'">Logout</a>'

    user_badge_html = f"""
    <div class="user-badge" style="display: flex; align-items: center; gap: 0.8rem; background: {badge_bg}; border: 1px solid {badge_border}; padding: 0.5rem 1.2rem; border-radius: 12px; font-size: 0.9rem; z-index: 10;">
        <div class="user-avatar" style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; color: white;">
            {user_email[0].upper() if user_email else 'U'}
        </div>
        <div class="user-details" style="display: flex; flex-direction: column;">
            <span style="font-weight: 600; color: white; font-size: 0.85rem;">{user_email}</span>
            <span style="font-size: 0.72rem; color: {badge_text}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1px;">
                {user_role.replace('_', ' ') if user_role else ''} • {auth_label}
            </span>
        </div>
        {logout_html}
    </div>
    """

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read().replace("\r\n", "\n")

    rendered_content = html_content.replace(
        "let cachedClaims = {};",
        f'const USER_ROLE = "{user_role}";\n        const USER_EMAIL = "{user_email}";\n        let cachedClaims = {{}};'
    ).replace(
        "        </div>\n    </header>",
        f"        </div>\n        {user_badge_html}\n    </header>"
    ).replace(
        'window.addEventListener("DOMContentLoaded", () => {',
        """window.addEventListener("DOMContentLoaded", () => {
            // Apply role-based visibility rules
            if (USER_ROLE === "employee") {
                document.getElementById("tab-pending").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                const tc = document.getElementById("tab-cards");
                if (tc) tc.style.display = "none";
                switchTab('reports');
            } else if (USER_ROLE === "manager") {
                document.getElementById("tab-submit").style.display = "none";
                const tc = document.getElementById("tab-cards");
                if (tc) tc.style.display = "inline-block";
                switchTab('pending');
            } else {
                const tc = document.getElementById("tab-cards");
                if (tc) tc.style.display = "inline-block";
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
                                ${(USER_ROLE === 'finance_admin' || USER_ROLE === 'manager' || USER_ROLE === 'auditor' || USER_ROLE === 'admin') ? `
                                <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', ${exp.amount})" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                    View Trail
                                </button>
                                ` : ''}
                            </div>
                        </td>"""
    )
    if auth_active:
        rendered_content = rendered_content.replace(
            'id="local-workflow-banner" style="display: flex;',
            'id="local-workflow-banner" style="display: none !important; display: flex;'
        )
    return HTMLResponse(content=rendered_content)

@router.get("/marketing", response_class=HTMLResponse)
async def get_marketing(request: Request):
    """
    Serves the beautifully stylized standalone enterprise marketing website.
    """
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "marketing.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


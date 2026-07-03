from fastapi import Request, HTTPException, status
from submission_frontend.config.settings import (
    is_auth_enabled,
    ALLOWED_ADMIN_EMAILS,
    ALLOWED_MANAGER_EMAILS,
    ALLOWED_EMPLOYEE_DOMAIN,
    GOOGLE_REDIRECT_URI,
    GOOGLE_CLIENT_ID
)

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
    # Resolve session user if present to support customized local/manager logins
    try:
        user = request.session.get("user")
        if user and isinstance(user, dict) and "email" in user:
            return {
                "email": user["email"],
                "role": user.get("role", "employee"),
                "name": user.get("name", ""),
                "authenticated": True
            }
    except Exception:
        pass

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

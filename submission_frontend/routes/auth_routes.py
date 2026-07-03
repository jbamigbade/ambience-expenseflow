import os
import urllib.parse
import urllib.request
import urllib.error
import secrets
import json
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

# Deferred import of main is done locally within routes to avoid circular imports

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """
    Serves the beautifully stylized glassmorphic Login Page.
    """
    import submission_frontend.main as main
    if main.is_auth_enabled():
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
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "login.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    return HTMLResponse(content=template_content.replace("{content_html}", content_html))

@router.get("/login-bypass")
async def login_bypass(request: Request):
    """
    Bypasses authentication and logs in as default finance admin for local testing.
    """
    import submission_frontend.main as main
    if main.is_auth_enabled():
        return RedirectResponse(url="/login")
    request.session["user"] = {
        "email": "default-user@company.com",
        "name": "Default Administrator",
        "role": "finance_admin"
    }
    return RedirectResponse(url="/")

@router.get("/login-google")
async def login_google(request: Request):
    """
    Initiates Google OAuth authentication flow.
    """
    import submission_frontend.main as main
    if not main.is_auth_enabled():
        return RedirectResponse(url="/")
        
    state = secrets.token_hex(16)
    request.session["state"] = state
    
    redirect_uri = main.get_redirect_uri(request)
    
    params = {
        "client_id": main.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(auth_url)

@router.get("/oauth2callback")
async def oauth2callback(request: Request):
    """
    Handles redirect callback from Google OAuth service.
    """
    import submission_frontend.main as main
    if not main.is_auth_enabled():
        return RedirectResponse(url="/")
        
    state = request.query_params.get("state")
    saved_state = request.session.get("state")
    if not state or state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state token (possible CSRF attempt)")
        
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code returned from Google")
        
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = main.get_redirect_uri(request)
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": main.GOOGLE_CLIENT_ID,
        "client_secret": main.GOOGLE_CLIENT_SECRET,
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
            
        if token_info.get("aud") != main.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="ID token audience mismatch")
            
        email = token_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email address not returned by Google")
            
        role = main.resolve_role(email)
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
        main.logger.error(f"Google Token Exchange HTTP Error: {e.code} - {error_body}")
        raise HTTPException(status_code=500, detail=f"Google sign-in token exchange failed: {error_body}")
    except Exception as e:
        main.logger.error(f"Error during Google OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth login failed: {str(e)}")

@router.get("/logout")
async def logout(request: Request):
    """
    Clears the user session and redirects to the login screen.
    """
    request.session.clear()
    return RedirectResponse(url="/login")

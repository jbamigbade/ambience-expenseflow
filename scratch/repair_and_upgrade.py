import os

# 1. Load variables from apply_frontend_upgrade.py and reports_upgrade.js
with open("scratch/apply_frontend_upgrade.py", "r", encoding="utf-8") as f:
    code = f.read()

mock_main_content = """
</style>
</head>
<body>
    <div class="glow-spot-1"
<button class="tab-btn" id="tab-submit" onclick="switchTab('submit')"
<!-- 1. Pending Approvals Section -->
</body>
</html>
window.addEventListener("DOMContentLoaded", () => {
            // Apply role-based visibility rules
            if (USER_ROLE === "employee") {
                document.getElementById("tab-pending").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('submit');
            } else if (USER_ROLE === "manager") {
                document.getElementById("tab-submit").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                fetchPendingApprovals();
            } else {
                fetchPendingApprovals();
            }
"""

class MockFile:
    def __init__(self, *args, **kwargs):
        pass
    def read(self):
        return mock_main_content
    def write(self, content):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

def mock_open(file, mode="r", *args, **kwargs):
    if file == "scratch/reports_upgrade.js":
        return open(file, mode, *args, **kwargs)
    return MockFile()

namespace = {
    "open": mock_open,
    "__file__": "scratch/apply_frontend_upgrade.py",
    "__name__": "__main__"
}

try:
    exec(code, namespace)
except Exception as e:
    print(f"Extraction execution error: {e}")

css_code = namespace.get("css_code")
tab_reports_btn = namespace.get("tab_reports_btn")
html_reports_section = namespace.get("html_reports_section")
html_modals = namespace.get("html_modals")
js_code = namespace.get("js_code")

print(f"css_code: {len(css_code)} chars")
print(f"tab_reports_btn: {repr(tab_reports_btn)}")
print(f"html_reports_section: {len(html_reports_section)} chars")
print(f"html_modals: {len(html_modals)} chars")
print(f"js_code: {len(js_code)} chars")

# 2. Read the corrupted main.py
with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

# We want to find the line that ends html_content
# html_content ends with:
# \n</body>
# </html>
# """
# We can find this closing triple quote. But wait, since html_modals, etc. were appended, they were inside html_content.
# Let's search for the end of get_dashboard, which is "def get_dashboard"
# Inside main.py, let's find the closing string literal of html_content:
# In the original file, it was followed by:
# "    # Dynamic String Replacements to inject user status, roles, and UI configuration"
marker = "    # Dynamic String Replacements to inject user status, roles, and UI configuration"
marker_idx = main_content.find(marker)
if marker_idx == -1:
    print("CRITICAL: marker not found in main.py!")
    exit(1)

print(f"Marker found at index {marker_idx}")

# part1 is everything before the marker, which includes html_content = """ ... """
# but wait! We want part1 to end exactly with the closing of the string literal: """\n
part1 = main_content[:marker_idx]

# Clean up part1 from any previous mess in a loop
print("Cleaning up previous duplicate injections from HTML content...")

# Remove css_code
count = 0
while css_code in part1:
    part1 = part1.replace(css_code, "")
    count += 1
print(f"Removed {count} occurrences of css_code")

# Remove tab_reports_btn
count = 0
while tab_reports_btn in part1:
    part1 = part1.replace(tab_reports_btn, "")
    count += 1
print(f"Removed {count} occurrences of tab_reports_btn")

# Remove html_reports_section
count = 0
while html_reports_section in part1:
    part1 = part1.replace(html_reports_section, "")
    count += 1
print(f"Removed {count} occurrences of html_reports_section")

# Remove html_modals
count = 0
while html_modals in part1:
    part1 = part1.replace(html_modals, "")
    count += 1
print(f"Removed {count} occurrences of html_modals")

# Remove js_code
count = 0
while js_code in part1:
    part1 = part1.replace(js_code, "")
    count += 1
print(f"Removed {count} occurrences of js_code")

# Clean up standard anchors in case they were messed up
# Wait, let's check if the standard anchors are clean in part1.
# Since we replaced the injected codes with "", the anchors should be back to original!
# Let's verify.
print("Applying upgrades to clean HTML content exactly once...")

# A. CSS
part1 = part1.replace("</style>", css_code + "\n</style>", 1)

# B. Tab Button
part1 = part1.replace(
    '<button class="tab-btn" id="tab-submit" onclick="switchTab(\'submit\')"',
    tab_reports_btn + '\n        <button class="tab-btn" id="tab-submit" onclick="switchTab(\'submit\')"',
    1
)

# C. Reports Section
part1 = part1.replace(
    "<!-- 1. Pending Approvals Section -->",
    html_reports_section + "\n        <!-- 1. Pending Approvals Section -->",
    1
)

# D. Modals
# Find the LAST </body> in part1 to put modals right before it
body_idx = part1.rfind("</body>")
if body_idx != -1:
    part1 = part1[:body_idx] + html_modals + "\n" + part1[body_idx:]
else:
    print("WARNING: </body> not found in part1!")

# E. JS code inside script tag
part1 = part1.replace(
    'window.addEventListener("DOMContentLoaded", () => {',
    js_code + "\n\n        window.addEventListener(\"DOMContentLoaded\", () => {",
    1
)

# 3. Define the clean, upgraded part2
part2 = """    # Dynamic String Replacements to inject user status, roles, and UI configuration
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
        logout_html = '<a href="/logout" class="btn-logout" style="color: #fb7185; text-decoration: none; margin-left: 0.5rem; font-weight: 600; font-size: 0.85rem; border-left: 1px solid var(--glass-border); padding-left: 0.8rem; transition: var(--transition);" onmouseover="this.style.color=\\'#f43f5e\\'" onmouseout="this.style.color=\\'#fb7185\\'">Logout</a>'
    else:
        # Fallback to bypass user
        auth_label = "Local Bypassed"
        badge_border = "rgba(245, 158, 11, 0.3)"
        badge_bg = "rgba(245, 158, 11, 0.05)"
        badge_text = "#f59e0b"
        logout_html = '<span style="color: var(--text-muted); margin-left: 0.5rem; font-size: 0.8rem; border-left: 1px solid var(--glass-border); padding-left: 0.8rem; font-style: italic;">Local Mode</span>'

    user_badge_html = f\"\"\"
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
    \"\"\"

    rendered_content = html_content.replace(
        "let cachedClaims = {};",
        f'const USER_ROLE = "{user_role}";\\n        const USER_EMAIL = "{user_email}";\\n        let cachedClaims = {{}};'
    ).replace(
        "</div>\\n    </header>",
        f"</div>\\n        {user_badge_html}\\n    </header>"
    ).replace(
        'window.addEventListener("DOMContentLoaded", () => {',
        \"\"\"window.addEventListener("DOMContentLoaded", () => {
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
            }\"\"\"
    ).replace(
        \"\"\"                        <td style="padding: 1rem 0.75rem; text-align: right;">
                            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                                <button class="btn btn-receipt" onclick="showClaimDetails('${exp.claim_id}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto; background: rgba(99,102,241,0.1); color: #cbd5e1; border-color: rgba(99,102,241,0.25);">
                                    View Details
                                </button>
                                <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', ${exp.amount})" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                    View Trail
                                </button>
                            </div>
                        </td>\"\"\",
        \"\"\"                        <td style="padding: 1rem 0.75rem; text-align: right;">
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
                        </td>\"\"\"
    )
    return HTMLResponse(content=rendered_content)

if __name__ == "__main__":
    import uvicorn
    # Use port 8080 as requested in typical dev servers or standard run directions
    logger.info("Starting FastAPI Uvicorn service...")
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
"""

final_content = part1 + part2

with open("submission_frontend/main.py", "w", encoding="utf-8") as f:
    f.write(final_content)

print("SUCCESS: main.py has been completely repaired, cleaned, and upgraded cleanly exactly once!")

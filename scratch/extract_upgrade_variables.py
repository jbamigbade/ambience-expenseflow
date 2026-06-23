import sys
import os

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
    print(f"Execution error: {e}")

css_code = namespace.get("css_code")
tab_reports_btn = namespace.get("tab_reports_btn")
html_reports_section = namespace.get("html_reports_section")
html_modals = namespace.get("html_modals")
js_code = namespace.get("js_code")

print(f"css_code loaded: {len(css_code) if css_code else 0} chars")
print(f"tab_reports_btn loaded: {len(tab_reports_btn) if tab_reports_btn else 0} chars")
print(f"html_reports_section loaded: {len(html_reports_section) if html_reports_section else 0} chars")
print(f"html_modals loaded: {len(html_modals) if html_modals else 0} chars")
print(f"js_code loaded: {len(js_code) if js_code else 0} chars")

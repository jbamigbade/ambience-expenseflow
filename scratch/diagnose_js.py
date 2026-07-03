import subprocess
import sys

# Test parsing of dashboard.js using node
try:
    result = subprocess.run(
        ["node", "-c", "submission_frontend/static/js/dashboard.js"],
        capture_output=True,
        text=True,
        check=True
    )
    print("No syntax errors found in dashboard.js")
except subprocess.CalledProcessError as e:
    print("Syntax error found in dashboard.js:")
    print(e.stderr)
    print(e.stdout)
except FileNotFoundError:
    print("node is not installed or not in PATH")

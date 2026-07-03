import re

with open("submission_frontend/templates/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
for i, line in enumerate(lines):
    # look for lone 'x' or 'x' in unusual places (not in tags or style)
    # e.g., line containing just 'x', or starting with 'x', or containing ' x '
    if re.search(r'\bx\b', line) or line.strip() == 'x':
        # ignore common words like 'box', 'index', etc. and match exact 'x'
        print(f"Line {i+1}: {repr(line)}")

with open("submission_frontend/static/js/dashboard.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines[:100]):
    indent = len(line) - len(line.lstrip())
    print(f"Line {i+1} (indent {indent}): {line.strip()[:100]}")

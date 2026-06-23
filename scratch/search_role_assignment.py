with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if '"role"' in line or 'role = ' in line or "role_assignment" in line or "allowed_admin" in line or "allowed_manager" in line:
        if 'def' in line or '=' in line:
            print(f"Line {idx+1}: {line.strip()[:120]}")

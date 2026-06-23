with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if '"/api/expenses"' in line or "'/api/expenses'" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        for j in range(idx, min(idx + 50, len(lines))):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break

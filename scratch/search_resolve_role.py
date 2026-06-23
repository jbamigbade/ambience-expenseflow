with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def resolve_role" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        for j in range(idx, min(idx + 40, len(lines))):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = False
for idx, line in enumerate(lines):
    if "def get_current_user" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        found = True
        for j in range(idx, min(idx + 50, len(lines))):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
if not found:
    print("def get_current_user not found")

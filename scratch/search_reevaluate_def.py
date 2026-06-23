with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = False
for idx, line in enumerate(lines):
    if "def reevaluate_expense_policies" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        found = True
        for j in range(idx, min(idx + 100, len(lines))):
            print(f"Line {j+1}: {lines[j].rstrip()}")
        break
if not found:
    print("def reevaluate_expense_policies not found")

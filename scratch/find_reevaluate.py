with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def reevaluate_expense" in line or "reevaluate_expense_policies" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        # print 50 lines
        for j in range(idx, min(idx + 80, len(lines))):
            print(f"Line {j+1}: {lines[j].rstrip()}")

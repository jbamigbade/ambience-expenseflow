import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "function showComplianceReview" in line:
        print(f"Line {idx+1}: {line.strip()[:100]}")
        # print the next 150 lines
        for j in range(idx, min(idx + 150, len(lines))):
            print(f"  Line {j+1}: {lines[j].rstrip()}")
        break

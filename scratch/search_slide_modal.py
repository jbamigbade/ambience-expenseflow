import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'slide-panel' in line or 'slide-content' in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        for j in range(idx - 10, min(idx + 100, len(lines))):
            print(f"  Line {j+1}: {lines[j].rstrip()}")
        break

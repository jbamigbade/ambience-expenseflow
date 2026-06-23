import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(3950, min(4005, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

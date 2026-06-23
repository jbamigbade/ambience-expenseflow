import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'onclick="' in line and ('view' in line or 'show' in line or 'load' in line or 'open' in line):
        print(f"Line {idx+1}: {line.strip()[:120]}")

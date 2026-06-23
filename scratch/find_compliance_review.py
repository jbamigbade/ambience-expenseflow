import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(4710, min(4760, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

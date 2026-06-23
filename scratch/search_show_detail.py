import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'slide-modal' in line or 'modal-claimant' in line or 'modal-amount' in line:
        if 'def' in line or 'function' in line or '=' in line:
            print(f"Line {idx+1}: {line.strip()[:120]}")

import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'showComplianceReview' in line or 'toggleModal' in line or 'slide-panel' in line:
            print(f"Line {idx}: {line.strip()[:120]}")

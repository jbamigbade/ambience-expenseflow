import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'def run_policy_check' in line:
            print(f"Line {idx}: {line.strip()}")

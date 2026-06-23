import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== LOADAUDITTRAIL JS 3990 - 4060 ===")
for idx in range(3989, min(4060, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

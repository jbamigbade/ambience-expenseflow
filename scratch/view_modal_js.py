import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== MODAL & COMPLIANCE JS 4740 - 4850 ===")
for idx in range(4739, min(4850, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

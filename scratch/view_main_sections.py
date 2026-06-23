with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== SECTIONS 3720 - 3770 ===")
for idx in range(3719, min(3770, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

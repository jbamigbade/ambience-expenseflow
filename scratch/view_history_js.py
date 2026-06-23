with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== FETCH EXPENSE HISTORY JS 3913 - 3990 ===")
for idx in range(3912, min(3990, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

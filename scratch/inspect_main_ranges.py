with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== TAB BAR ===")
for idx in range(3695, min(3725, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

print("\n=== ROLE REPLACEMENT / END OF GET_DASHBOARD ===")
for idx in range(4885, min(4938, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

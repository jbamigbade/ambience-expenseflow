with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== API ENDPOINTS 2140 - 2400 ===")
for idx in range(2139, min(2400, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")

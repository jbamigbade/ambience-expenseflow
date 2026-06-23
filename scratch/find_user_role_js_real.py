with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'if (USER_ROLE === "employee")' in line or 'USER_ROLE === "employee"' in line:
        print(f"Found on line {i+1}: {line.strip()}")
        for j in range(max(0, i - 15), min(i + 30, len(lines))):
            clean_line = lines[j].rstrip().encode('ascii', 'replace').decode('ascii')
            print(f"{j+1}: {clean_line}")
        print("---")

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Printing lines 7600 to 7745 (ASCII clean):")
for j in range(7600, min(7745, len(lines))):
    clean_line = lines[j].rstrip().encode('ascii', 'replace').decode('ascii')
    print(f"{j+1}: {clean_line}")

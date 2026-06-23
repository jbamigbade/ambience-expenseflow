with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Printing lines 7740 to 7853 of main.py:")
for j in range(7739, min(7853, len(lines))):
    clean_line = lines[j].rstrip().encode('ascii', 'replace').decode('ascii')
    print(f"{j+1}: {clean_line}")

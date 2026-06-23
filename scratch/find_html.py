with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Printing lines 4390 to 4450:")
for j in range(4389, min(4450, len(lines))):
    print(f"{j+1}: {lines[j].rstrip()}")

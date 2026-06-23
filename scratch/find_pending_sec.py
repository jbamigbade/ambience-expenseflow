with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Printing lines 5360 to 5390:")
for j in range(5359, min(5390, len(lines))):
    print(f"{j+1}: {lines[j].rstrip()}")

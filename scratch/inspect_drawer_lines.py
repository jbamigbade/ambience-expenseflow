with open("submission_frontend/templates/dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(695, 710):
    if i < len(lines):
        print(f"{i+1}: {repr(lines[i])}")

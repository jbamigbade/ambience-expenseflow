with open("submission_frontend/templates/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

print("Literal '\\n' in dashboard.html:", content.count("\\n"))
print("Occurrences of 'x' or similar around drawer:")
lines = content.splitlines()
for i, line in enumerate(lines):
    if "\\n" in line:
        print(f"Line {i+1}: {repr(line)}")

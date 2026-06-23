with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

print(f"Occurrences of reports-grid: {content.count('reports-grid')}")
print(f"Occurrences of tab-reports: {content.count('tab-reports')}")
print(f"Occurrences of section-reports: {content.count('section-reports')}")
print(f"Occurrences of slide-overlay: {content.count('slide-overlay')}")

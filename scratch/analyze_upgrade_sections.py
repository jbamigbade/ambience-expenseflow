import os

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

upgrade_comment = "ENTERPRISE EXPENSE REPORT WORKFLOW FRONTEND UPGRADE"
print(f"Occurrences of upgrade comment: {content.count(upgrade_comment)}")

idx = -1
while True:
    idx = content.find(upgrade_comment, idx + 1)
    if idx == -1:
        break
    print(f"Found upgrade comment at index {idx}")
    print("BEFORE:")
    print(repr(content[max(0, idx-100):idx]))
    print("AFTER:")
    print(repr(content[idx:idx+150]))
    print("=" * 60)

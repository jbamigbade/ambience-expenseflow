import os

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

target = 'window.addEventListener("DOMContentLoaded", () => {'
print(f"Total occurrences of target: {content.count(target)}")

# Find indices of target
idx = -1
while True:
    idx = content.find(target, idx + 1)
    if idx == -1:
        break
    print(f"Found target at index {idx}")
    # print 100 characters before
    print("BEFORE:")
    print(repr(content[max(0, idx-200):idx]))
    print("AFTER:")
    print(repr(content[idx:idx+200]))
    print("-" * 40)

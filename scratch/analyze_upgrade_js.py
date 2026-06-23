with open("scratch/reports_upgrade.js", "r", encoding="utf-8") as f:
    js_code = f.read()

target = 'window.addEventListener("DOMContentLoaded", () => {'
print(f"Target in reports_upgrade.js: {js_code.count(target)}")

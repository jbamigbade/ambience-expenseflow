import os

print("Reverting JS upgrade...")

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

with open("scratch/reports_upgrade.js", "r", encoding="utf-8") as f:
    js_code = f.read()

js_end_target = 'window.addEventListener("DOMContentLoaded", () => {'

# The exact replacement was: js_code + "\n\n        " + js_end_target
upgrade_pattern = js_code + "\n\n        " + js_end_target

if upgrade_pattern in main_content:
    print("Found upgraded JS pattern, reverting...")
    main_content = main_content.replace(upgrade_pattern, js_end_target)
    with open("submission_frontend/main.py", "w", encoding="utf-8") as f:
        f.write(main_content)
    print("Revert complete!")
else:
    print("Upgrade pattern not found directly, trying without leading spaces...")
    upgrade_pattern_no_spaces = js_code + "\n\n" + js_end_target
    if upgrade_pattern_no_spaces in main_content:
        print("Found upgraded JS pattern (no spaces), reverting...")
        main_content = main_content.replace(upgrade_pattern_no_spaces, js_end_target)
        with open("submission_frontend/main.py", "w", encoding="utf-8") as f:
            f.write(main_content)
        print("Revert complete!")
    else:
        print("Revert failed: Pattern not found!")

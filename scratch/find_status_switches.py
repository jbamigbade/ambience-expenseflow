main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

target_statuses = ["returned_to_employee", "approved_by_manager", "approved_with_exceptions", "paid", "closed"]
for idx, line in enumerate(lines):
    for status in target_statuses:
        if status in line:
            if idx > 7000: # We only care about front-end JS logic (which is at the end of main.py)
                print(f"Line {idx+1}: {line}")
                break

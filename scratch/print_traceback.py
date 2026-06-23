with open(r"C:\Users\johnb\.gemini\antigravity-cli\brain\aa589895-e91e-4997-8ffa-0598d7284a09\.system_generated\tasks\task-9814.log", "r", encoding="utf-8") as f:
    log_content = f.read()

lines = log_content.splitlines()
start_print = False
fail_count = 0
for idx, line in enumerate(lines, 1):
    if "test_manager_queue_and_actions" in line and "FAIL" in line:
        start_print = True
    elif "test_manager_queue_and_actions" in line:
        # Check if traceback is starting
        if idx > 10 and any("test_manager_queue_and_actions" in lines[i] for i in range(idx-10, idx)):
            start_print = True
    
    if start_print or "test_manager_queue_and_actions" in line:
        print(f"--- START FAILURE LOG {idx} ---")
        for l in lines[max(0, idx - 10):idx + 100]:
            print(l)
        print("--- END FAILURE LOG ---")
        break

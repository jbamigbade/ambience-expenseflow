with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the end of html_content in main.py
import re
match = re.search(r'html_content\s*=\s*"""', content)
if match:
    start_pos = match.start()
    # Find the next """
    end_match = re.search(r'"""', content[match.end():])
    if end_match:
        end_pos = match.end() + end_match.start()
        print(f"html_content is from position {start_pos} to {end_pos}")
        # Convert positions to line numbers
        lines_before_start = content[:start_pos].count("\n") + 1
        lines_before_end = content[:end_pos].count("\n") + 1
        print(f"Line range: {lines_before_start} to {lines_before_end}")
else:
    print("Could not find html_content declaration.")

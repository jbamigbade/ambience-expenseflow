# Search original_main.py for occurrences of "New Expense Report" or related strings
import os

path = "D:\\02_AI_and_Data\\Kaggle-AI-Agents\\Capstone\\scratch\\original_main.py"
if os.path.exists(path):
    print("File exists, size:", os.path.getsize(path))
    with open(path, "r", encoding="utf-16") as f:
        content = f.read()
    
    print("Content length:", len(content))
    print("Occurrences of 'New Expense Report':", content.count("New Expense Report"))
    
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "New Expense Report" in line:
            safe_line = line.encode('ascii', errors='replace').decode('ascii')
            print(f"Line {i+1}: {repr(safe_line)}")
            for j in range(max(0, i-5), min(len(lines), i+6)):
                safe_j = lines[j].encode('ascii', errors='replace').decode('ascii')
                print(f"  {j+1}: {repr(safe_j)}")
else:
    print("original_main.py not found.")

import os

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        content = f.read()
    
    print("Occurrences of get_fast_api_app:", content.count("get_fast_api_app"))
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "get_fast_api_app" in line:
            print(f"Line {i+1}: {line}")
else:
    print("original_main.py not found.")

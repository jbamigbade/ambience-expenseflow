import os

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        content = f.read()
    
    lines = content.splitlines()
    print(f"Total lines: {len(lines)}")
    
    found_decorators = []
    for i, line in enumerate(lines):
        if line.strip().startswith("@app.") or line.strip().startswith("@router."):
            found_decorators.append((i+1, line.strip()))
            
    print(f"Found {len(found_decorators)} decorators:")
    for line_num, decorator in found_decorators:
        print(f"Line {line_num:5d} | {decorator}")
else:
    print("original_main.py not found.")

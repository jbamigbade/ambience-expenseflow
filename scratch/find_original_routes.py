import os
import re

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        content = f.read()
    
    lines = content.splitlines()
    print(f"Total lines: {len(lines)}")
    
    # Regex to match @app.get, @app.post, etc.
    route_pattern = re.compile(r'^\s*@app\.(get|post|put|delete|patch|options|head)\((["\'])(.*?)\2')
    
    found_routes = []
    for i, line in enumerate(lines):
        match = route_pattern.match(line)
        if match:
            method = match.group(1)
            route_path = match.group(3)
            # Find the function definition on the next few lines
            func_name = "unknown"
            for j in range(i + 1, min(len(lines), i + 10)):
                if "def " in lines[j]:
                    func_match = re.search(r'def\s+(\w+)\s*\(', lines[j])
                    if func_match:
                        func_name = func_match.group(1)
                    break
            found_routes.append((i + 1, method, route_path, func_name))
            
    print(f"Found {len(found_routes)} routes:")
    for line_num, method, r_path, func in found_routes:
        print(f"Line {line_num:5d} | {method.upper():6s} | {r_path:50s} | def {func}")
else:
    print("original_main.py not found.")

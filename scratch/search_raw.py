import os

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        content = f.read()
    
    lines = content.splitlines()
    print(f"Total lines: {len(lines)}")
    
    # Check for "health"
    health_lines = [i+1 for i, line in enumerate(lines) if "health" in line.lower()]
    print(f"Occurrences of 'health': {len(health_lines)} (Lines: {health_lines})")
    
    # Check for "/api/sessions"
    sessions_lines = [i+1 for i, line in enumerate(lines) if "/api/sessions" in line.lower()]
    print(f"Occurrences of '/api/sessions': {len(sessions_lines)} (Lines: {sessions_lines})")
    
    # Check for "/api/claims"
    claims_lines = [i+1 for i, line in enumerate(lines) if "/api/claims" in line.lower()]
    print(f"Occurrences of '/api/claims': {len(claims_lines)} (Lines: {claims_lines})")
else:
    print("original_main.py not found.")

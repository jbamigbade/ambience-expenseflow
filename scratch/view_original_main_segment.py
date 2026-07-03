import os

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading segment of original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        lines = f.readlines()
    for idx in range(1400, min(1520, len(lines))):
        print(f"{idx+1:4d}: {lines[idx]}", end="")
else:
    print("original_main.py not found.")

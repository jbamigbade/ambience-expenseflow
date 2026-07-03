import os

path = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\scratch\original_main.py"
if os.path.exists(path):
    print("Reading first 100 lines of original_main.py...")
    with open(path, "r", encoding="utf-16") as f:
        lines = [f.readline() for _ in range(120)]
    for i, line in enumerate(lines):
        print(f"{i+1:3d}: {repr(line)}")
else:
    print("original_main.py not found.")

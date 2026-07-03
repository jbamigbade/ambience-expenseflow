with open("D:\\02_AI_and_Data\\Kaggle-AI-Agents\\Capstone\\scratch\\original_main.py", "r", encoding="utf-16") as f:
    content = f.read()

lines = content.splitlines()
for i, line in enumerate(lines):
    if "slider-panel" in line:
        print(f"Line {i+1}: {repr(line)}")

with open("D:\\02_AI_and_Data\\Kaggle-AI-Agents\\Capstone\\scratch\\original_main.py", "r", encoding="utf-16") as f:
    content = f.read()

lines = content.splitlines()
for i, line in enumerate(lines):
    if "<!-- 0. Expense Reports Section -->" in line:
        print(f"Found on line {i+1}: {repr(line)}")
        for j in range(max(0, i-5), min(len(lines), i+6)):
            safe_j = lines[j].encode('ascii', errors='replace').decode('ascii')
            print(f"  {j+1}: {repr(safe_j)}")

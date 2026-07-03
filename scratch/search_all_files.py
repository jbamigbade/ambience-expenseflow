import os

folder = r"D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone\submission_frontend"
queries = ["sessions", "claims", "health"]

for q in queries:
    print(f"=== Searching for query: {q} ===")
    matches = 0
    for root, dirs, files in os.walk(folder):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if q in content.lower():
                    print(f"Found in: {os.path.relpath(path, folder)}")
                    # Find lines
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if q in line.lower():
                            print(f"  Line {i+1}: {line.strip()[:100]}")
                            matches += 1
                            if matches >= 20:
                                break
            except Exception as e:
                pass
            if matches >= 20:
                break
    print(f"Total matches for {q}: {matches}\n")

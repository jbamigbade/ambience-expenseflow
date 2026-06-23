import os

for root, dirs, files in os.walk("."):
    for f in files:
        if "main" in f or "backup" in f or f.endswith(".py"):
            path = os.path.join(root, f)
            if "venv" not in path and "cache" not in path:
                print(f"{path}: {os.path.getsize(path)} bytes")

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/all_sessions.txt", "r", encoding="utf-16") as f:
    content = f.read()

sessions = content.split("--- Session ID:")
for s in sessions:
    if "bob@company.com" in s or '"amount": 45' in s or '"amount":45' in s or "Team lunch" in s:
        # Get the first line to extract the ID
        lines = s.strip().split("\n")
        session_header = lines[0] if lines else "Unknown Session"
        print(f"\n================ SESSION ID: {session_header} ================")
        for line in lines[1:]:
            print("  " + line)

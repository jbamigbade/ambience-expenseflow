import subprocess
import json

project = "project-5d38f91a-29a3-45bd-8d4"
filter_str = 'logName="projects/project-5d38f91a-29a3-45bd-8d4/logs/aiplatform.googleapis.com%2Freasoning_engine_stderr" AND timestamp >= "2026-06-19T22:50:45Z" AND timestamp <= "2026-06-19T22:50:52Z"'
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

res = subprocess.run([
    gcloud,
    "logging",
    "read",
    filter_str,
    f"--project={project}",
    "--format=json"
], capture_output=True, text=True)

if res.returncode == 0:
    try:
        logs = json.loads(res.stdout)
        print(f"Found {len(logs)} log entries:")
        for log in reversed(logs):
            print(log.get('textPayload', ''))
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Raw output:", res.stdout)
else:
    print("Error:", res.stderr)

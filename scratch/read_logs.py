import subprocess
import json

project = "project-5d38f91a-29a3-45bd-8d4"
# Search for any references to '45', 'bob', or 'ValidationError' or 'ValueError' in all reasoning engine logs
filter_str = 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND (textPayload:"ValidationError" OR textPayload:"45" OR textPayload:"bob" OR textPayload:"ValueError")'

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

res = subprocess.run([
    gcloud,
    "logging",
    "read",
    filter_str,
    f"--project={project}",
    "--format=json",
    "--limit=50"
], capture_output=True, text=True)

if res.returncode == 0:
    logs = json.loads(res.stdout)
    print(f"Found {len(logs)} log entries:")
    for log in reversed(logs):
        log_name = log.get('logName', '').split('%2F')[-1]
        print(f"[{log.get('timestamp')}] [{log_name}] {log.get('textPayload')}")
else:
    print("Error:", res.stderr)

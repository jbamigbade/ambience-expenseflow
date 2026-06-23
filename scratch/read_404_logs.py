import subprocess
import json

project = "project-5d38f91a-29a3-45bd-8d4"
filter_str = 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND logName="projects/project-5d38f91a-29a3-45bd-8d4/logs/aiplatform.googleapis.com%2Freasoning_engine_stdout"'

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

res = subprocess.run([
    gcloud,
    "logging",
    "read",
    filter_str,
    f"--project={project}",
    "--format=json",
    "--limit=100"
], capture_output=True, text=True)

if res.returncode == 0:
    logs = json.loads(res.stdout)
    print(f"Found {len(logs)} stdout log entries:")
    for log in reversed(logs):
        text = log.get('textPayload', '')
        if "POST" in text or "404" in text or "query" in text:
            print(f"[{log.get('timestamp')}] {text.strip()}")
else:
    print("Error:", res.stderr)

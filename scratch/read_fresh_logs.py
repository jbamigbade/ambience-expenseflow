import subprocess
import json

project = "project-5d38f91a-29a3-45bd-8d4"
filter_str = 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND timestamp >= "2026-06-20T12:57:00Z"'

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

res = subprocess.run([
    gcloud,
    "logging",
    "read",
    filter_str,
    f"--project={project}",
    "--format=json",
    "--limit=300"
], capture_output=True, text=True)

if res.returncode == 0:
    logs = json.loads(res.stdout)
    print(f"Found {len(logs)} log entries:")
    # Group logs by timestamp or print them sequentially to show complete stack trace
    for log in reversed(logs):
        log_name = log.get('logName', '').split('%2F')[-1]
        text = log.get('textPayload', '')
        # Only print stderr lines with details or stdout status codes
        if "reasoning_engine_stderr" in log_name:
            print(f"[{log.get('timestamp')}] [stderr] {text.strip()}")
        elif "reasoning_engine_stdout" in log_name:
            print(f"[{log.get('timestamp')}] [stdout] {text.strip()}")
else:
    print("Error:", res.stderr)

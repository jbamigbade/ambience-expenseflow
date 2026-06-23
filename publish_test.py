import json
import subprocess

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

payload = {
    "employee_name": "Bob (meals)",
    "amount": 45.0,
    "description": "Team lunch"
}

message = json.dumps({
    "input": {
        "message": json.dumps(payload),
        "user_id": "default-user"
    }
})


print("Publishing meals expense ($45):")
print(message)

subprocess.run([
    gcloud,
    "pubsub",
    "topics",
    "publish",
    topic,
    f"--project={project}",
    f"--message={message}"
], check=True)


import json
import subprocess

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

payload = {
    "employee_name": "Alice (travel)",
    "amount": 250.0,
    "description": "NYC Flight Tickets"
}

message = json.dumps({
    "input": {
        "message": json.dumps(payload),
        "user_id": "default-user"
    }
})


print("Publishing travel expense ($250):")
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


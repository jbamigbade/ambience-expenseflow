FROM python:3.11-slim

WORKDIR /app

# Install dependencies directly to be fast and completely reliable
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn>=0.28.0" \
    "google-adk[gcp]>=2.0.0,<3.0.0" \
    "google-cloud-aiplatform>=1.156.0" \
    "google-cloud-storage>=2.14.0" \
    "python-multipart>=0.0.9" \
    "google-cloud-firestore>=2.14.0" \
    "itsdangerous>=2.1.0"

# Copy application files
COPY main.py .

# Expose standard Cloud Run port
EXPOSE 8080

# Run uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

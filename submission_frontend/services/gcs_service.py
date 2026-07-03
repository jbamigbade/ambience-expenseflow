from google.cloud import storage
from submission_frontend.config.settings import PROJECT_ID, BUCKET_NAME

def get_gcs_bucket():
    """
    Returns the storage bucket instance for manager uploads.
    """
    client = storage.Client(project=PROJECT_ID)
    return client.bucket(BUCKET_NAME)

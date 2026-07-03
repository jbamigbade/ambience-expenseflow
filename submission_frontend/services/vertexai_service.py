import vertexai
from vertexai.preview import reasoning_engines
from google.cloud.aiplatform_v1beta1 import types as aip_types
from submission_frontend.config.settings import PROJECT_ID, LOCATION, AGENT_RUNTIME_ID, logger

def init_vertexai():
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        # Instantiate reasoning engine to warm client
        _remote_engine = reasoning_engines.ReasoningEngine(AGENT_RUNTIME_ID)
        logger.info("Successfully connected to reasoning engine execution client.")
    except Exception as e:
        logger.error(f"Error initializing Vertex AI Reasoning Engine: {e}")

# Initialize Vertex AI
init_vertexai()

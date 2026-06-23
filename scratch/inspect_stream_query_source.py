import inspect
from vertexai.agent_engines.templates.adk import AdkApp

try:
    print(inspect.getsource(AdkApp.stream_query))
except Exception as e:
    print("Error:", e)

import inspect
from vertexai.agent_engines.templates.adk import AdkApp

print("AdkApp.stream_query signature:")
print(inspect.signature(AdkApp.stream_query))

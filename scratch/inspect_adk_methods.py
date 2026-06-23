import inspect
from vertexai.agent_engines.templates.adk import AdkApp

print("AdkApp methods:")
for name, member in inspect.getmembers(AdkApp, predicate=inspect.isfunction):
    print(f"- {name}")

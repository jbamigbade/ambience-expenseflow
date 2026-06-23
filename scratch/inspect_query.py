from app.agent_runtime_app import agent_runtime
print("agent_runtime class:", type(agent_runtime))
print("agent_runtime operations:", agent_runtime.register_operations())
print("agent_runtime query attribute exists:", hasattr(agent_runtime, "query"))
if hasattr(agent_runtime, "query"):
    import inspect
    print("query signature:", inspect.signature(agent_runtime.query))

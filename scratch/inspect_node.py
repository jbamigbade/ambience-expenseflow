from app.agent import review_agent
print(dir(review_agent))
if hasattr(review_agent, "func"):
    print("Has .func:", review_agent.func)
if hasattr(review_agent, "_func"):
    print("Has ._func:", review_agent._func)

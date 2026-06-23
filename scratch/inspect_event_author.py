import os
import asyncio
import sys

sys.path.append(os.path.abspath("submission_frontend"))
from google.adk.sessions import VertexAiSessionService

async def inspect():
    project = "project-5d38f91a-29a3-45bd-8d4"
    location = "us-west1"
    engine_id = "8516245322706452480"
    
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    s = VertexAiSessionService(project=project, location=location, agent_engine_id=engine_id)
    
    # Let's get perdiem-user-1 session
    sess = await s.get_session(app_name="app", user_id="perdiem-user-1", session_id="1058272794908819456")
    if sess:
        print(f"Session {sess.id}:")
        for i, ev in enumerate(sess.events):
            print(f"Event {i}: author={getattr(ev, 'author', 'N/A')}, author_type={type(getattr(ev, 'author', None))}")
            if ev.content and ev.content.parts:
                for p in ev.content.parts:
                    txt = getattr(p, 'text', 'N/A')
                    print(f"  Part text: {txt}")
                    try:
                        import json
                        parsed = json.loads(txt)
                        print(f"  Parsed JSON successfully! Keys: {list(parsed.keys())}")
                        print(f"  Values: {parsed}")
                    except Exception as je:
                        print(f"  JSON load error: {je}")

if __name__ == "__main__":
    asyncio.run(inspect())

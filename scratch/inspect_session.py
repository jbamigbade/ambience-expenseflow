import asyncio
import sys

# Reconfigure stdout to use utf-8 to prevent CP1252 errors on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from google.adk.sessions import VertexAiSessionService

async def main():
    project = "project-5d38f91a-29a3-45bd-8d4"
    location = "us-west1"
    agent_engine_id = "8516245322706452480"
    
    s = VertexAiSessionService(
        project=project,
        location=location,
        agent_engine_id=agent_engine_id
    )
    
    list_resp = await s.list_sessions(app_name="app")
    if not list_resp.sessions:
        print("No sessions found.")
        return
        
    summary = list_resp.sessions[0]
    sess = await s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id)
    if not sess:
        print("Could not retrieve first session.")
        return
        
    print(f"Session: {sess}")
    print(f"Session type: {type(sess)}")
    print(f"Session fields: {sess.__dict__.keys()}")
    if sess.events:
        e = sess.events[0]
        print(f"First event: {e}")
        print(f"First event type: {type(e)}")
        print(f"First event fields: {dir(e)}")
        print(f"First event dict keys: {e.__dict__.keys() if hasattr(e, '__dict__') else 'No __dict__'}")
        if hasattr(e, 'model_fields'):
            print(f"First event Pydantic model fields: {e.model_fields.keys()}")

if __name__ == "__main__":
    asyncio.run(main())

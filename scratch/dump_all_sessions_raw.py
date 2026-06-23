import asyncio
import json
import sys

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
    print(f"Total sessions: {len(list_resp.sessions)}")
    
    for summary in list_resp.sessions:
        print(f"\n==========================================")
        print(f"Session ID: {summary.id}")
        print(f"User ID: {summary.user_id}")
        
        sess = await s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id)
        if not sess:
            print("Could not retrieve session details")
            continue
            
        for i, event in enumerate(sess.events):
            print(f"  Event {i}: author={event.author}")
            if event.content:
                for p_idx, part in enumerate(event.content.parts):
                    if part.text:
                        print(f"    Part {p_idx} [Text]: {part.text}")
                    if getattr(part, 'function_call', None):
                        fc = part.function_call
                        print(f"    Part {p_idx} [Function Call]: {fc.name} args={fc.args}")
                    if getattr(part, 'function_response', None):
                        fr = part.function_response
                        print(f"    Part {p_idx} [Function Response]: {fr.name} response={fr.response}")

if __name__ == "__main__":
    asyncio.run(main())

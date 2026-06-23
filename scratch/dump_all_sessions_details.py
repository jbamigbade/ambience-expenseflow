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
    
    for i, summary in enumerate(list_resp.sessions):
        sess = await s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id)
        if not sess:
            continue
            
        print(f"\n[{i+1}] Session ID: {sess.id} (User: {sess.user_id})")
        # Extract first and last event
        if sess.events:
            first = sess.events[0]
            last = sess.events[-1]
            first_text = ""
            if first.content and first.content.parts:
                first_text = first.content.parts[0].text or ""
            print(f"  First Event Author: {first.author}")
            print(f"  First Event Text: {first_text[:200]}")
            
            # Count unresolved request inputs
            unresolved = []
            for e in sess.events:
                if e.content and e.content.parts:
                    for part in e.content.parts:
                        fc = getattr(part, 'function_call', None)
                        if fc and fc.name == "adk_request_input":
                            unresolved.append(fc.args.get('interruptId', 'review_decision'))
                        fr = getattr(part, 'function_response', None)
                        if fr and fr.name == "adk_request_input":
                            response_id = getattr(fr, 'id', None)
                            if response_id in unresolved:
                                unresolved.remove(response_id)
            print(f"  Unresolved Interrupts: {unresolved}")

if __name__ == "__main__":
    asyncio.run(main())

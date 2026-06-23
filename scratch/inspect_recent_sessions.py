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
    
    s = VertexAiSessionService(
        project=project,
        location=location,
        agent_engine_id=engine_id
    )
    
    list_resp = await s.list_sessions(app_name="app")
    print(f"Found {len(list_resp.sessions)} sessions total.")
    
    sessions_sorted = sorted(
        list_resp.sessions,
        key=lambda x: getattr(x, "last_update_time", 0.0),
        reverse=True
    )
    
    for sess_summary in sessions_sorted[:15]:
        print(f"\nSession ID: {sess_summary.id} | User ID: {sess_summary.user_id} | Updated: {getattr(sess_summary, 'last_update_time', 'N/A')}")
        try:
            sess = await s.get_session(app_name="app", user_id=sess_summary.user_id, session_id=sess_summary.id)
            if sess:
                print(f"  Number of events: {len(sess.events)}")
                # Print the first and last event content summary
                if sess.events:
                    first_evt = sess.events[0]
                    last_evt = sess.events[-1]
                    print(f"  First event: {getattr(first_evt, 'name', 'N/A')} | {type(first_evt)}")
                    print(f"  Last event: {getattr(last_evt, 'name', 'N/A')} | {type(last_evt)}")
                    # Let's check for any function calls or text in the last few events
                    for i, evt in enumerate(sess.events[-3:]):
                        print(f"  Evt -{3-i}:")
                        if evt.content and evt.content.parts:
                            for part in evt.content.parts:
                                if part.text:
                                    print(f"    Text: {part.text[:100]}")
                                if getattr(part, 'function_call', None):
                                    print(f"    Function Call: {part.function_call.name} with args {part.function_call.args}")
                                if getattr(part, 'function_response', None):
                                    print(f"    Function Response: {part.function_response.name}")
        except Exception as e:
            print(f"  Error getting details: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())

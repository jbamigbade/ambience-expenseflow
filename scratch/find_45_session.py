import asyncio
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
    print(f"Found {len(list_resp.sessions)} sessions.")
    
    for summary in list_resp.sessions:
        sess = await s.get_session(app_name="app", user_id=summary.user_id, session_id=summary.id)
        if not sess:
            continue
            
        # Check if any event has bob@company.com or 45
        session_text = ""
        for e in sess.events:
            if e.content:
                for part in e.content.parts:
                    if part.text:
                        session_text += part.text + " "
                    fc = getattr(part, 'function_call', None)
                    if fc:
                        session_text += str(fc.args) + " "
                        
        if "bob" in session_text.lower() or "45" in session_text or "lunch" in session_text.lower():
            print(f"\n================ MATCH FOUND ================")
            print(f"Session ID: {sess.id} (User: {sess.user_id})")
            for idx, e in enumerate(sess.events):
                route = None
                state_delta = None
                if hasattr(e, 'actions') and e.actions is not None:
                    route = getattr(e.actions, 'route', None)
                    state_delta = getattr(e.actions, 'state_delta', None)
                    
                node_path = None
                if hasattr(e, 'node_info') and e.node_info is not None:
                    node_path = getattr(e.node_info, 'path', None)
                    
                print(f"  Event {idx}: author={e.author}, route={route}, node_path={node_path}")
                if state_delta:
                    print(f"    State Delta: {state_delta}")
                if e.output:
                    print(f"    Output: {e.output}")
                if e.content:
                    for p_idx, part in enumerate(e.content.parts):
                        if part.text:
                            print(f"    Part {p_idx} [Text]: {part.text}")
                        if getattr(part, "function_call", None):
                            fc = part.function_call
                            print(f"    Part {p_idx} [Function Call]: {fc.name} args={fc.args}")
                        if getattr(part, "function_response", None):
                            fr = part.function_response
                            print(f"    Part {p_idx} [Function Response]: {fr.name} response={fr.response}")

if __name__ == "__main__":
    asyncio.run(main())

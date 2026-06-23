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
    print(f"Total sessions listed: {len(list_resp.sessions)}")
    for summary in list_resp.sessions:
        print(f"Session ID: {summary.id}, User ID: {summary.user_id}, App Name: {summary.app_name}")

if __name__ == "__main__":
    asyncio.run(main())

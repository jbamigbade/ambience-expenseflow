"""
Audit Intelligence Agent.
Creates standardized, structured, immutable audit log events to record and track
agentic steps, compliance checks, and approval decisions.
"""

import uuid
from datetime import datetime

class AuditIntelligenceAgent:
    """
    Agent responsible for translating workflow stages and findings into structured audit events.
    """

    def create_event(self, event_type: str, message: str, actor: str = "system", metadata: dict = None) -> dict:
        """
        Creates a structured, timestamped audit event dictionary.
        
        Args:
            event_type (str): Type of the event (e.g., 'intake_validated', 'policy_warning').
            message (str): Explanatory message of what occurred.
            actor (str): The specific agent or module that triggered the event.
            metadata (dict, optional): Additional contextual metadata.
            
        Returns:
            dict: The structured audit event.
        """
        return {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "message": message,
            "actor": actor,
            "metadata": metadata or {}
        }
        
    def generate_report_audit_trail(self, report_id: str, stages: list) -> list:
        """
        Helper to construct a complete set of audit events for a report based on stages.
        """
        events = []
        for stage in stages:
            events.append(self.create_event(
                event_type=stage.get("event_type", "stage_completed"),
                message=stage.get("message", "Stage processed"),
                actor=stage.get("actor", "agent"),
                metadata={**(stage.get("metadata", {})), "report_id": report_id}
            ))
        return events

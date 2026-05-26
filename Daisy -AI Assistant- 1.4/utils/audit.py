"""
Audit logging for all actions and decisions
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from schemas import TranscriptionResult, AssistantIntent, AssistantAction, ActionResult


class AuditLogger:
    """Append-only audit log for all actions and decisions"""
    
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_transcription(self, transcript: TranscriptionResult) -> None:
        """Log a transcription result"""
        data = transcript.dict()
        # Convert datetime to ISO string
        if 'timestamp' in data and isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        self._append({
            "type": "transcription",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        })
    
    def log_intent(self, intent: AssistantIntent) -> None:
        """Log a structured intent"""
        data = intent.dict()
        # Convert datetime to ISO string
        if 'timestamp' in data and isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        self._append({
            "type": "intent",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        })
    
    def log_action(self, action: AssistantAction, approved: bool, reason: Optional[str] = None) -> None:
        """Log an action decision (approved/denied)"""
        data = action.dict()
        self._append({
            "type": "action_decision",
            "timestamp": datetime.now().isoformat(),
            "approved": approved,
            "reason": reason,
            "data": data,
        })
    
    def log_execution(self, result: ActionResult) -> None:
        """Log action execution result"""
        data = result.dict()
        # Convert datetime to ISO string
        if 'timestamp' in data and isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        if 'action' in data and isinstance(data['action'], dict):
            # Recursively convert datetime in nested action
            action_data = data['action']
            # Action itself might have datetime fields, but it's a dict now
        self._append({
            "type": "execution",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        })
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error"""
        self._append({
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        })
    
    def _append(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the audit log"""
        def convert_datetime(obj):
            """Recursively convert datetime objects to ISO strings"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        entry_serialized = convert_datetime(entry)
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry_serialized) + '\n')


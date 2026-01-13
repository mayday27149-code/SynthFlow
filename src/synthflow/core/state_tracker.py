import sqlite3
import json
import uuid
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..utils.logger import get_logger

class ExecutionState(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    trace_id: str
    step_id: Optional[str] = None
    status: str # "running", "completed", "failed", "paused"
    details: Dict[str, Any] = Field(default_factory=dict)
    duration: float = 0.0 # Duration in seconds

class ExecutionTimeline(BaseModel):
    events: List[ExecutionState] = Field(default_factory=list)

class StateTracker:
    """
    负责维护流程执行状态和历史，支持 SQLite 持久化
    """
    
    def __init__(self, db_path="synthflow.db", trace_id: str = None):
        self._timeline = ExecutionTimeline()
        self._current_state: Optional[ExecutionState] = None
        self._context: Dict[str, Any] = {}
        self.logger = get_logger("StateTracker")
        self.db_path = db_path
        self.trace_id = trace_id or str(uuid.uuid4())
        self._step_start_times: Dict[str, float] = {}
        self._pending_interaction: Optional[Dict[str, Any]] = None
        self._interaction_result: Optional[Dict[str, Any]] = None
        self._init_db()

    def set_pending_interaction(self, interaction_data: Dict[str, Any]):
        self._pending_interaction = interaction_data
        self.logger.info(f"Pending interaction set: {interaction_data}")

    def get_pending_interaction(self) -> Optional[Dict[str, Any]]:
        return self._pending_interaction

    def resolve_interaction(self, result: Dict[str, Any]):
        self._interaction_result = result
        self._pending_interaction = None
        self.logger.info(f"Interaction resolved: {result}")
        
    def wait_for_interaction_result(self, timeout: int = 300) -> Optional[Dict[str, Any]]:
        start = time.time()
        self._interaction_result = None
        while time.time() - start < timeout:
            if self._interaction_result:
                res = self._interaction_result
                self._interaction_result = None
                return res
            time.sleep(0.5)
        return None

    def _init_db(self):
        """Initialize SQLite database for audit logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic table creation
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trace_id TEXT,
                        timestamp TEXT,
                        step_id TEXT,
                        status TEXT,
                        details TEXT,
                        context_snapshot TEXT,
                        duration REAL
                    )
                """)
                
                # Migration: Check if new columns exist, if not add them (Simulated migration)
                # For simplicity in this dev environment, we assume table might need recreation 
                # or we just try to add columns and ignore errors if they exist.
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(audit_log)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if "trace_id" not in columns:
                    conn.execute("ALTER TABLE audit_log ADD COLUMN trace_id TEXT")
                if "duration" not in columns:
                    conn.execute("ALTER TABLE audit_log ADD COLUMN duration REAL")
                    
        except Exception as e:
            self.logger.error(f"Failed to initialize audit DB: {e}")

    def set_context(self, key: str, value: Any):
        self._context[key] = value
        self.logger.debug(f"Context updated: {key} = {str(value)[:50]}...")

    def get_context(self, key: str) -> Any:
        return self._context.get(key)
        
    def get_all_context(self) -> Dict[str, Any]:
        return self._context

    def snapshot(self, step_id: Optional[str], status: str, details: Dict[str, Any] = None):
        """
        Record a snapshot of the current state to memory and DB
        """
        if details is None:
            details = {}
            
        # Calculate duration
        duration = 0.0
        if status in ["running", "executing", "started"]:
            self._step_start_times[step_id] = time.time()
        elif status in ["completed", "failed"] and step_id in self._step_start_times:
            start_time = self._step_start_times.pop(step_id)
            duration = time.time() - start_time
            
        state = ExecutionState(
            trace_id=self.trace_id,
            step_id=step_id,
            status=status,
            details=details,
            duration=duration
        )
        # Memory storage
        self._timeline.events.append(state)
        self._current_state = state
        self.logger.info(f"[{self.trace_id}] {state.timestamp} | Step: {step_id} | Status: {status} | Duration: {duration:.3f}s")

        # Persistent storage (Audit Log)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO audit_log (trace_id, timestamp, step_id, status, details, context_snapshot, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        state.trace_id,
                        state.timestamp.isoformat(), 
                        step_id, 
                        status, 
                        json.dumps(details, default=str),
                        json.dumps(self._context, default=str),
                        duration
                    )
                )
        except Exception as e:
            self.logger.error(f"Failed to persist snapshot: {e}")

    def get_timeline(self) -> ExecutionTimeline:
        return self._timeline

    def get_current_state(self) -> Optional[ExecutionState]:
        return self._current_state

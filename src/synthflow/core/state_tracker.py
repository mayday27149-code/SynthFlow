from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..utils.logger import get_logger

class ExecutionState(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    step_id: Optional[str] = None
    status: str # "running", "completed", "failed", "paused"
    details: Dict[str, Any] = Field(default_factory=dict)

class ExecutionTimeline(BaseModel):
    events: List[ExecutionState] = Field(default_factory=list)

class StateTracker:
    """
    负责维护流程执行状态和历史
    """
    
    def __init__(self):
        self._timeline = ExecutionTimeline()
        self._current_state: Optional[ExecutionState] = None
        self.logger = get_logger("StateTracker")

    def snapshot(self, step_id: Optional[str], status: str, details: Dict[str, Any] = None):
        """
        Record a snapshot of the current state
        """
        if details is None:
            details = {}
            
        state = ExecutionState(
            step_id=step_id,
            status=status,
            details=details
        )
        self._timeline.events.append(state)
        self._current_state = state
        self.logger.info(f"{state.timestamp} | Step: {step_id} | Status: {status}")

    def get_timeline(self) -> ExecutionTimeline:
        return self._timeline

    def get_current_state(self) -> Optional[ExecutionState]:
        return self._current_state

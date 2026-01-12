import time
from typing import Dict, Any, Optional
from enum import Enum

from .config_parser import ProcessModel, StepModel
from .component_manager import ComponentManager
from .strategy_manager import StrategyManager
from .state_tracker import StateTracker
from ..utils.logger import get_logger

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutionResult:
    def __init__(self, status: ExecutionStatus, data: Dict[str, Any] = None, error: str = None):
        self.status = status
        self.data = data or {}
        self.error = error

class ExecutionEngine:
    """
    负责协调流程执行，管理组件生命周期
    """
    
    def __init__(self, 
                 component_manager: ComponentManager,
                 strategy_manager: StrategyManager,
                 state_tracker: StateTracker):
        self.cm = component_manager
        self.sm = strategy_manager
        self.tracker = state_tracker
        self._status = ExecutionStatus.PENDING
        self._context: Dict[str, Any] = {} # Shared context for the process
        self.logger = get_logger("ExecutionEngine")

    def execute(self, process_model: ProcessModel) -> ExecutionResult:
        """
        Execute the given process model
        """
        self._status = ExecutionStatus.RUNNING
        self.tracker.snapshot(None, "started", {"process_name": process_model.name})
        
        current_step_idx = 0
        steps = process_model.steps
        
        # Simple pointer based execution to allow jumps
        # Map step IDs to indices for easier jumps
        step_map = {step.id: i for i, step in enumerate(steps)}
        
        current_step_id = steps[0].id if steps else None
        
        while current_step_id and self._status == ExecutionStatus.RUNNING:
            if current_step_id not in step_map:
                error_msg = f"Step ID {current_step_id} not found"
                self.tracker.snapshot(current_step_id, "error", {"error": error_msg})
                return ExecutionResult(ExecutionStatus.FAILED, error=error_msg)
            
            step = steps[step_map[current_step_id]]
            self.tracker.snapshot(step.id, "executing", {"type": step.type})
            
            try:
                # 1. Execute Strategy (Pre-step)
                # e.g., check if we need to pause or check conditions
                
                # 2. Execute Component
                # Find component handler for this step type
                # For simplicity, we assume component_type matches step.type or we map it
                component_type = step.type
                
                # Handle special "review" type or generic components
                if component_type == "review":
                     # Invoke review service
                     review_component = self.cm.get_component("review_service")
                     result = review_component.execute(self._context, step.params)
                     # Review might pause execution or return result immediately (if automated/mocked)
                     if result.get("status") == "rejected":
                         raise Exception(f"Review rejected: {result.get('reason')}")
                else:
                    # Generic component execution
                    try:
                        component = self.cm.get_component(component_type)
                        result = component.execute(self._context, step.params)
                        # Store result in context if needed
                        if result:
                            self._context[step.id] = result
                    except ValueError:
                         # Fallback or error if component not found
                         self.logger.warning(f"Warning: No component found for type '{component_type}'. simulating...")
                         time.sleep(0.5)
                
                self.tracker.snapshot(step.id, "completed")
                
                # Determine next step
                if step.next_step:
                    current_step_id = step.next_step
                else:
                    # Default to next in list
                    current_idx = step_map[current_step_id]
                    if current_idx + 1 < len(steps):
                        current_step_id = steps[current_idx + 1].id
                    else:
                        current_step_id = None # End of process

            except Exception as e:
                self.tracker.snapshot(step.id, "failed", {"error": str(e)})
                # Error handling strategy
                error_strategy = self.sm.get_current_strategy("error_handling")
                if error_strategy:
                     decision = error_strategy.apply({"error": e, "step": step, "context": self._context})
                     if decision == "retry":
                         continue # Retry same step
                     elif decision == "skip":
                         # Move to next
                         current_idx = step_map[current_step_id]
                         if current_idx + 1 < len(steps):
                             current_step_id = steps[current_idx + 1].id
                         else:
                             current_step_id = None
                         continue
                
                self._status = ExecutionStatus.FAILED
                return ExecutionResult(ExecutionStatus.FAILED, error=str(e))

        self._status = ExecutionStatus.COMPLETED
        self.tracker.snapshot(None, "completed")
        return ExecutionResult(ExecutionStatus.COMPLETED, self._context)

    def pause(self):
        self._status = ExecutionStatus.PAUSED
        self.tracker.snapshot(None, "paused")

    def resume(self):
        if self._status == ExecutionStatus.PAUSED:
            self._status = ExecutionStatus.RUNNING
            self.tracker.snapshot(None, "resumed")

    def cancel(self):
        self._status = ExecutionStatus.CANCELLED
        self.tracker.snapshot(None, "cancelled")

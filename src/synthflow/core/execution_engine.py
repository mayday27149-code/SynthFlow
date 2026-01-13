import time
from typing import Dict, Any, Optional, List
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
        # self._context removed, use tracker context
        self.logger = get_logger("ExecutionEngine")

    def _resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        if not params:
            return {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                key_path = v[2:-1] 
                val = self.tracker.get_context(key_path)
                # Simple fallback for step_id.output nesting if stored as flat keys or dicts
                # Assuming tracker.get_context handles exact keys. 
                # If not found, try to look into dicts
                if val is None and "." in key_path:
                    parts = key_path.split(".", 1)
                    base_obj = self.tracker.get_context(parts[0])
                    if isinstance(base_obj, dict):
                        val = base_obj.get(parts[1])
                
                resolved[k] = val if val is not None else v
            else:
                resolved[k] = v
        return resolved

    def execute(self, process_model: ProcessModel) -> ExecutionResult:
        """
        Execute the given process model
        """
        self._status = ExecutionStatus.RUNNING
        self.tracker.snapshot(None, "started", {"process_name": process_model.name})
        
        try:
            self._execute_sequence(process_model.steps)
        except Exception as e:
            self.logger.error(f"Process execution failed: {e}")
            return ExecutionResult(ExecutionStatus.FAILED, error=str(e))
                
        self._status = ExecutionStatus.COMPLETED
        self.tracker.snapshot(None, "completed")
        return ExecutionResult(ExecutionStatus.COMPLETED)

    def _execute_sequence(self, steps: List[StepModel]):
        """
        Execute a sequence of steps.
        Handles linear flow and explicit jumps within the sequence.
        """
        if not steps:
            return

        step_map = {step.id: i for i, step in enumerate(steps)}
        current_step_id = steps[0].id
        
        while current_step_id and self._status == ExecutionStatus.RUNNING:
            if current_step_id not in step_map:
                raise ValueError(f"Step ID {current_step_id} not found in current scope")
            
            step = steps[step_map[current_step_id]]
            
            try:
                if step.type == "loop":
                    self._execute_loop(step)
                elif step.type == "condition":
                    self._execute_condition(step)
                else:
                    result = self._execute_atomic_step(step)
                    # Check for Flow Control (Skip/Stop)
                    if isinstance(result, dict) and "action" in result:
                        action = result["action"]
                        if action == "skip":
                            self.logger.info("Flow Control: SKIP requested.")
                            break # Break sequence? No, skip means 'continue' in loop context.
                            # But _execute_sequence is the body of the loop.
                            # If we break here, we return to _execute_loop, which proceeds to next iteration.
                            # So 'break' is correct for 'continue loop'.
                            # Wait, what if this sequence is NOT a loop body but the main process?
                            # If main process, 'break' ends the process (completed).
                            # This seems acceptable.
                        elif action == "stop":
                            self.logger.info("Flow Control: STOP requested.")
                            self._status = ExecutionStatus.COMPLETED # Or cancelled?
                            return # Stop everything

                # Determine next step
                if step.next_step:
                    current_step_id = step.next_step
                else:
                    # Default: next in list
                    current_idx = step_map[step.id]
                    if current_idx + 1 < len(steps):
                        current_step_id = steps[current_idx + 1].id
                    else:
                        current_step_id = None
                        
            except Exception as e:
                self.logger.error(f"Step {step.id} failed: {e}")
                self.tracker.snapshot(step.id, "failed", {"error": str(e)})
                if step.on_error == "continue":
                    self.logger.info(f"Continuing after error in step {step.id}")
                    # Try to move next
                    current_idx = step_map[step.id]
                    if current_idx + 1 < len(steps):
                        current_step_id = steps[current_idx + 1].id
                    else:
                        current_step_id = None
                else:
                    raise e

    def _execute_loop(self, step: StepModel):
        """Execute a loop step"""
        self.tracker.snapshot(step.id, "loop_start", {"type": step.loop.type})
        loop_config = step.loop
        
        if loop_config.type == "count":
            count = loop_config.count
            if not count:
                raise ValueError("Loop count must be specified for 'count' type")
            
            for i in range(count):
                if self._status != ExecutionStatus.RUNNING: break
                self.tracker.set_context("loop_index", i)
                self.logger.info(f"Loop {step.id} iteration {i+1}/{count}")
                self._execute_sequence(loop_config.steps)
                
        elif loop_config.type == "while_element":
            selector = loop_config.condition
            try:
                # Get OperationExecutor to access browser
                # Assuming 'operation_executor' is registered
                op_exec = self.cm.get_component("operation_executor")
                # We need to access the underlying browser manager or page
                # Since op_exec has browser_manager as public attribute (based on my previous read)
                if hasattr(op_exec, 'browser_manager'):
                    page = op_exec.browser_manager.get_page()
                    
                    i = 0
                    while self._status == ExecutionStatus.RUNNING:
                        # Check if element is visible
                        if not page.is_visible(selector):
                            self.logger.info(f"Loop condition ended: {selector} not visible.")
                            break
                            
                        self.tracker.set_context("loop_index", i)
                        self.logger.info(f"Loop {step.id} iteration {i+1} (while {selector})")
                        self._execute_sequence(loop_config.steps)
                        i += 1
                else:
                    self.logger.warning("OperationExecutor does not expose browser_manager. Cannot execute while_element loop.")
                    
            except Exception as e:
                self.logger.error(f"Failed to execute while_element loop: {e}")
                raise e

    def _execute_condition(self, step: StepModel):
        """Execute a condition step"""
        self.tracker.snapshot(step.id, "condition_check", {"branches": len(step.branches) if step.branches else 0})
        
        if not step.branches:
            self.logger.warning(f"Condition step {step.id} has no branches.")
            return

        matched = False
        for branch in step.branches:
            if self._evaluate_condition(branch.condition):
                self.logger.info(f"Condition matched: {branch.condition}")
                self._execute_sequence(branch.steps)
                matched = True
                break # First match wins
        
        if not matched:
            self.logger.info(f"No branches matched in step {step.id}")

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Simple condition evaluator.
        Supports:
        - "${var} == 'value'"
        - "${var} != 'value'"
        - "${var}" (truthiness)
        """
        # Resolve variables in the condition string first? 
        # No, because string replacement might break quotes.
        # We should parse the condition logic first.
        
        # Simple parsing for ==
        if "==" in condition:
            parts = condition.split("==")
            left = parts[0].strip()
            right = parts[1].strip().strip("'").strip('"')
            
            # Resolve left side if it's a variable
            val_left = self._resolve_value(left)
            
            # Right side is usually a literal string in our simple parser, 
            # but could be a variable too.
            val_right = self._resolve_value(right) if "${" in right else right
            
            return str(val_left) == str(val_right)
            
        elif "!=" in condition:
            parts = condition.split("!=")
            left = parts[0].strip()
            right = parts[1].strip().strip("'").strip('"')
            
            val_left = self._resolve_value(left)
            val_right = self._resolve_value(right) if "${" in right else right
            
            return str(val_left) != str(val_right)
            
        else:
            # Truthiness check
            val = self._resolve_value(condition)
            return bool(val)

    def _resolve_value(self, value_str: str) -> Any:
        """Helper to resolve a single value string like '${var}'"""
        if isinstance(value_str, str) and value_str.startswith("${") and value_str.endswith("}"):
            key_path = value_str[2:-1]
            val = self.tracker.get_context(key_path)
            # Fallback for dict access dot notation if get_context doesn't support it natively
            if val is None and "." in key_path:
                parts = key_path.split(".", 1)
                base_obj = self.tracker.get_context(parts[0])
                if isinstance(base_obj, dict):
                    val = base_obj.get(parts[1])
            return val
        return value_str


    def _execute_atomic_step(self, step: StepModel):
        """Execute a single atomic step (L-A-V)"""
        self.tracker.snapshot(step.id, "executing", {"type": step.type})
        
        # Resolve params with context
        final_params = self._resolve_params(step.params)
        
        # If new L-A-V fields exist, dump them to dict and merge/pass them
        if step.locator or step.action:
                lav_params = {}
                if step.locator: lav_params["locator"] = step.locator.model_dump()
                if step.action: lav_params["action"] = step.action.model_dump()
                if step.verification: lav_params["verification"] = step.verification.model_dump()
                
                self._recursive_resolve(lav_params)
                final_params.update(lav_params)
        
        # Execute Component
        component_type = step.type
        if component_type == "interaction":
            component_type = "operation_executor"
        
        try:
            # Get component (with fallbacks)
            try:
                component = self.cm.get_component(component_type)
            except ValueError:
                component = self.cm.get_component("OperationExecutor")

            # Execute
            # INJECT TRACKER into context for HumanInteraction
            ctx = self.tracker.get_all_context().copy()
            ctx["_tracker"] = self.tracker
            
            result = component.execute(ctx, final_params)
            
            # Store result
            if result is not None:
                self.tracker.set_context(f"{step.id}.output", result)
                
                # Handle Data Binding
                if step.data and step.data.outputs:
                    for context_key, source_path in step.data.outputs.items():
                        val = self._get_value_by_path(result, source_path)
                        self.tracker.set_context(context_key, val)
                        self.logger.info(f"Data Bound: {context_key} = {val}")

            self.tracker.snapshot(step.id, "completed", {"result": result})
            return result
            
        except Exception as e:
            # Re-raise to be handled by _execute_sequence
            raise e


    def _recursive_resolve(self, obj: Any):
        """Helper to resolve ${var} in nested dicts/lists in-place"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    self._recursive_resolve(v)
                elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    key_path = v[2:-1]
                    val = self.tracker.get_context(key_path)
                    obj[k] = val if val is not None else v
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, (dict, list)):
                    self._recursive_resolve(v)
                elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    key_path = v[2:-1]
                    val = self.tracker.get_context(key_path)
                    obj[i] = val if val is not None else v

    def _get_value_by_path(self, data: Any, path: str) -> Any:
        """Extract value from nested dict using dot notation (e.g. 'user.name')"""
        if not path: return data
        
        # Special case: "return_value" might be the root of 'data' or a key inside it.
        # If result is {"status": "success", "text": "abc"}
        # path "text" -> "abc"
        # path "return_value.text" -> "abc" (allow optional root prefix)
        
        keys = path.split(".")
        curr = data
        
        if keys[0] == "return_value":
            keys.pop(0)
            
        for k in keys:
            if isinstance(curr, dict):
                curr = curr.get(k)
            else:
                return None
        return curr

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

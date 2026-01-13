import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.config_parser import ProcessModel, StepModel, LoopModel, ActionModel
from synthflow.core.component_manager import ComponentManager
from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker
from synthflow.components.operation_executor import OperationExecutor

def verify_loop_logic():
    print("--- Verifying Loop Logic ---")
    
    # Setup Engine
    tracker = StateTracker()
    cm = ComponentManager()
    sm = StrategyManager()
    
    # Register OperationExecutor manually for test
    # Pass the class, not instance
    cm.register_component("operation_executor", OperationExecutor)
    
    engine = ExecutionEngine(cm, sm, tracker)
    
    # Define Process with Loop
    # Loop 3 times
    # Inside: Wait 0.5s, Print index
    
    step_loop = StepModel(
        id="main_loop",
        type="loop",
        loop=LoopModel(
            type="count",
            count=3,
            steps=[
                StepModel(
                    id="loop_action",
                    type="interaction",
                    action=ActionModel(
                        type="wait",
                        value=0.1
                    ),
                    params={"log_msg": "Processing item ${loop_index}"}
                )
            ]
        )
    )
    
    process = ProcessModel(
        name="loop_verification",
        steps=[step_loop]
    )
    
    print("Executing Process...")
    result = engine.execute(process)
    
    if result.status.value == "completed":
        print("[PASS] Execution completed successfully.")
        # Verify loop context (loop_index should be 2 at the end)
        last_index = tracker.get_context("loop_index")
        print(f"Last Loop Index: {last_index}")
        if last_index == 2:
             print("[PASS] Loop count verified.")
        else:
             print(f"[FAIL] Loop count mismatch. Expected 2, got {last_index}")
    else:
        print(f"[FAIL] Execution failed: {result.error}")

if __name__ == "__main__":
    verify_loop_logic()

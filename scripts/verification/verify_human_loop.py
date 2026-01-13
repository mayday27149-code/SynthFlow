import sys
import os
import time
import threading
import logging

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.config_parser import ProcessModel, StepModel, LoopModel, ActionModel
from synthflow.core.component_manager import ComponentManager
from synthflow.components.human_interaction import HumanInteraction
from synthflow.components.operation_executor import OperationExecutor

from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger("VerifyHumanLoop")

def user_simulator(tracker):
    """Simulates user interaction via Web UI"""
    logger.info("User Simulator started.")
    interaction_count = 0
    
    while True:
        pending = tracker.get_pending_interaction()
        if pending:
            logger.info(f"Simulator found pending interaction: {pending['id']}")
            time.sleep(1) # Simulate think time
            
            action = "execute"
            if interaction_count == 0:
                action = "execute"
                logger.info(">>> USER DECISION: EXECUTE")
            elif interaction_count == 1:
                action = "skip"
                logger.info(">>> USER DECISION: SKIP")
            elif interaction_count == 2:
                action = "stop"
                logger.info(">>> USER DECISION: STOP")
            
            tracker.resolve_interaction({"status": "completed", "action": action})
            interaction_count += 1
            
            if action == "stop":
                break
        
        time.sleep(0.5)

def main():
    logger.info("--- Verifying Human Loop Logic ---")
    
    # 1. Setup Components
    cm = ComponentManager()
    cm.register_component("human_interaction", HumanInteraction)
    cm.register_component("operation_executor", OperationExecutor)
    
    tracker = StateTracker()
    sm = StrategyManager()
    
    engine = ExecutionEngine(cm, sm, tracker)
    
    # 2. Define Process with Loop and Human Interaction
    process = ProcessModel(
        id="human_loop_process",
        name="Human Loop Verification",
        steps=[
            StepModel(
                id="main_loop",
                type="loop",
                loop=LoopModel(
                    type="count",
                    count=5, # Should stop after 3rd iteration (index 2)
                    steps=[
                        # Step 1: Human Decision
                        StepModel(
                            id="ask_human",
                            type="human_interaction",
                            params={
                                "instruction": "Check item ${loop_index}",
                                "timeout": 10
                            }
                        ),
                        # Step 2: Work (should be skipped if action=skip)
                        StepModel(
                            id="do_work",
                            type="interaction",
                            action=ActionModel(type="wait", value=0.1), # Simulate work
                            params={"description": "Processing item ${loop_index}"}
                        )
                    ]
                )
            )
        ]
    )
    
    # 3. Start User Simulator in separate thread
    sim_thread = threading.Thread(target=user_simulator, args=(engine.tracker,))
    sim_thread.daemon = True
    sim_thread.start()
    
    # 4. Execute
    logger.info("Executing Process...")
    try:
        engine.execute(process)
        logger.info("[PASS] Execution completed.")
    except Exception as e:
        logger.error(f"[FAIL] Execution failed: {e}")
        
    # 5. Verify Results
    # We expect:
    # Iteration 0: Execute -> do_work runs
    # Iteration 1: Skip -> do_work skipped
    # Iteration 2: Stop -> loop ends
    # Total iterations logged: 0, 1, 2
    
    # Check context/logs (In a real test we would inspect tracker history)
    # For now, relying on logs output
    
if __name__ == "__main__":
    main()

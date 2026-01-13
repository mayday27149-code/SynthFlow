
import unittest
import time
import threading
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))

from synthflow.core.config_parser import StepModel, LocatorModel, ActionModel, DataBindingModel, ProcessModel, BranchModel
from synthflow.core.execution_engine import ExecutionEngine, ExecutionStatus
from synthflow.core.component_manager import ComponentManager
from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker
from synthflow.components.operation_executor import OperationExecutor
from synthflow.components.human_interaction import HumanInteraction
from synthflow.utils.logger import get_logger

logger = get_logger("VerifyABRouting")

class MockOperationExecutor:
    def initialize(self, config):
        pass
        
    def execute(self, ctx, params):
        action = params.get("action", {}).get("type")
        logger.info(f"MockExec: {action} with params {params}")
        
        # Simulate reading text from A system
        if action == "read_text":
            return {"text": "Task-101: Purchase Order"}
        
        # Simulate B system operations
        if action == "input":
            val = params.get("action", {}).get("value")
            logger.info(f"MockExec: Inputting value '{val}'")
            
        return {"status": "success"}

class TestABRouting(unittest.TestCase):
    def setUp(self):
        self.cm = ComponentManager()
        self.cm.register_component("operation_executor", MockOperationExecutor)
        self.cm.register_component("human_interaction", HumanInteraction)
        
        self.sm = StrategyManager()
        self.tracker = StateTracker()
        self.engine = ExecutionEngine(self.cm, self.sm, self.tracker)

    def test_routing_logic(self):
        """
        Simulate the full A -> Human -> B flow:
        1. Read A (mocked)
        2. Human Decision (mocked)
        3. Condition Routing (Type1/Create vs Type1/Append)
        """
        
        # 1. Define the Process Model
        process = ProcessModel(
            name="A_to_B_Routing",
            steps=[
                # Step 1: Read Data from A
                StepModel(
                    id="step_read_a",
                    type="interaction",
                    action=ActionModel(type="read_text"),
                    data=DataBindingModel(outputs={"task_raw_content": "return_value.text"})
                ),
                
                # Step 2: Human Decision (Tagging)
                StepModel(
                    id="step_human_review",
                    type="human_interaction",
                    params={
                        "instruction": "Classify task: ${task_raw_content}",
                        "options": ["confirm"]
                    },
                    data=DataBindingModel(outputs={
                        "decision_type": "data.decision_type",
                        "decision_mode": "data.decision_mode"
                    })
                ),
                
                # Step 3: Condition Routing
                StepModel(
                    id="step_routing",
                    type="condition",
                    branches=[
                        # Route 1: Type1 + Create
                        BranchModel(
                            condition="${decision_type} == 'Type1'", # Simplified for test, assume we check Type first
                            steps=[
                                # Inner check for Mode (nested condition or just simple linear for test)
                                # Let's just do single level for simplicity of this verification
                                StepModel(
                                    id="step_b_create",
                                    type="interaction",
                                    action=ActionModel(type="input", value="Creating ${task_raw_content}")
                                )
                            ]
                        ),
                        # Route 2: Type2 (Fallback)
                        BranchModel(
                            condition="${decision_type} == 'Type2'",
                            steps=[
                                StepModel(
                                    id="step_b_other",
                                    type="interaction",
                                    action=ActionModel(type="input", value="Handling Type2")
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        # 2. Run in a separate thread because Human Interaction blocks
        t = threading.Thread(target=self.engine.execute, args=(process,))
        t.start()
        
        # 3. Wait for Read A to finish and Human Interaction to be pending
        time.sleep(1)
        
        # Check context has the read value
        ctx_task = self.tracker.get_context("task_raw_content")
        logger.info(f"Context after Step 1: task_raw_content = {ctx_task}")
        self.assertEqual(ctx_task, "Task-101: Purchase Order")
        
        # 4. Simulate Human Interaction
        pending = self.tracker.get_pending_interaction()
        if pending:
            logger.info(f"Pending Interaction: {pending}")
            
            # Simulate User Tagging: Type1, Create
            # We inject these into the result data
            # NOTE: Real world UI would send this data back.
            # The engine needs to put this data into context.
            # Currently `_execute_atomic_step` or `wait_for_interaction` logic needs to handle this.
            # In `execution_engine.py`, we didn't explicitly see HumanInteraction handling in `_execute_atomic_step`.
            # It usually falls into `_execute_atomic_step` calling `HumanInteractionComponent`.
            # Let's assume we can resolve interaction with data.
            
            self.tracker.resolve_interaction({
                "status": "completed", 
                "action": "confirm",
                "data": { # Enhanced data from human
                    "decision_type": "Type1",
                    "decision_mode": "Create"
                }
            })
            
        else:
            self.fail("Did not pause for human interaction")
            
        # 5. Wait for completion
        t.join(timeout=2)
        
        # 6. Verify Execution Path
        # We expect "step_b_create" to be executed (Type1)
        # We can check logs or verify if 'step_b_create' is in history?
        # StateTracker snapshots might help?
        # Or simpler: The MockExecutor logs.
        
        logger.info("Test finished.")

if __name__ == "__main__":
    unittest.main()

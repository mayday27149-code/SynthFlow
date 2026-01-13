import sys
import os
import time

# Add src to path (adjusted for scripts/verification/ location)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from synthflow.core.config_parser import ProcessModel, StepModel, LocatorModel, ActionModel, VerificationModel, DataBindingModel
from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.component_manager import ComponentManager
from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker
from synthflow.components.operation_executor import OperationExecutor

def verify_lav_d_structure():
    print("--- Verifying L-A-V-D Structure & Execution ---")
    
    # 1. Define a Config with L-A-V-D structure (Simulating JSON/YAML load)
    # Scenario: 
    # Step 1: Open Bing (Action)
    # Step 2: Search for "SynthFlow" (Locator + Action + Verification) -> Bind Title to Context
    
    print("Creating Process Model with L-A-V-D...")
    
    process = ProcessModel(
        name="LAV_Verification_Flow",
        steps=[
            # Step 1: Open URL
            # Note: For "open" action, locator is not strictly required but we provide one to trigger L-A-V mode
            # We can use a dummy locator value like "body" or just ensure "locator" key exists.
            StepModel(
                id="step_open",
                type="interaction",
                locator=LocatorModel(type="css", value="body"), # Dummy locator
                action=ActionModel(type="open", value="https://www.bing.com"),
                next_step="step_search"
            ),
            # Step 2: Search & Verify & Extract
            StepModel(
                id="step_search",
                type="interaction",
                # L: Find search box
                locator=LocatorModel(type="css", value="#sb_form_q"),
                # A: Type "SynthFlow" human-like
                action=ActionModel(type="input", value="SynthFlow", human_like=True),
                # V: Verify search box has value (simple check)
                verification=VerificationModel(check="visible", selector="#sb_form_q"),
                # D: Bind result (simulated)
                data=DataBindingModel(outputs={"search_status": "status"}) 
            )
        ]
    )
    
    # 2. Setup Engine
    print("Initializing Engine...")
    cm = ComponentManager()
    cm.register_component("interaction", OperationExecutor) # Alias
    cm.register_component("operation_executor", OperationExecutor) # Fallback
    
    sm = StrategyManager()
    tracker = StateTracker() # In-memory tracker
    
    engine = ExecutionEngine(cm, sm, tracker)
    
    # 3. Execute
    print("Executing Process...")
    try:
        result = engine.execute(process)
        
        if result.status.value == "completed":
            print("[PASS] Execution completed successfully.")
        else:
            print(f"[FAIL] Execution failed with status: {result.status}")
            if result.error:
                print(f"Error: {result.error}")
            return

        # 4. Verify Context Binding
        status_val = tracker.get_context("search_status")
        print(f"Context 'search_status': {status_val}")
        
        if status_val == "success":
            print("[PASS] Data Binding verified.")
        else:
            print(f"[FAIL] Data Binding incorrect. Expected 'success', got '{status_val}'")

    except Exception as e:
        print(f"[FAIL] Exception during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_lav_d_structure()

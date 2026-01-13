import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from synthflow.core.component_manager import ComponentManager
from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker
from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.config_parser import ConfigParser
from synthflow.components.human_interaction import HumanInteraction
from synthflow.components.data_processing import DataExtractor, DataEntry
from synthflow.components.review_service import ReviewService

def test_flow():
    print("--- Initializing Engine ---")
    cm = ComponentManager()
    sm = StrategyManager()
    st = StateTracker()
    
    # Register components
    cm.register_component("human_interaction", HumanInteraction)
    cm.register_component("data_extractor", DataExtractor)
    cm.register_component("data_entry", DataEntry)
    cm.register_component("review_service", ReviewService)
    
    engine = ExecutionEngine(cm, sm, st)
    config_parser = ConfigParser()
    
    print("--- Loading Config ---")
    config_path = os.path.join("config", "cross_system_flow.yaml")
    process_model = config_parser.load_config(config_path)
    
    print(f"--- Executing Process: {process_model.name} ---")
    result = engine.execute(process_model)
    
    print(f"--- Execution Status: {result.status} ---")
    if result.error:
        print(f"Error: {result.error}")
        
    print("--- Verifying Context Data ---")
    # Check if step_extract_data.output is in context
    extracted_data = st.get_context("step_extract_data.output")
    print(f"Context [step_extract_data.output]: {extracted_data}")
    
    # Check if data_entry received the data (we can check logs or just assume if no error)
    # Since we don't capture component internal state, we rely on the fact that 
    # if ${...} resolution failed, it would pass the literal string or None.
    
    print("--- Timeline ---")
    for event in st.get_timeline().events:
        print(f"[{event.timestamp.strftime('%H:%M:%S')}] {event.step_id}: {event.status}")

if __name__ == "__main__":
    test_flow()

import sys
import os

# Add src to the beginning of sys.path to ensure local imports override any installed package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from synthflow.core.config_parser import ConfigParser
from synthflow.core.component_manager import ComponentManager
from synthflow.core.strategy_manager import StrategyManager
from synthflow.core.state_tracker import StateTracker
from synthflow.core.execution_engine import ExecutionEngine
from synthflow.utils.logger import setup_logger

# Import Components
from synthflow.components.element_locator import ElementLocator
from synthflow.components.operation_executor import OperationExecutor
from synthflow.components.review_service import ReviewService
from synthflow.components.human_interaction import HumanInteraction
from synthflow.components.data_processing import DataExtractor, DataEntry

def main():
    # Initialize Logger
    logger = setup_logger()
    logger.info("Initializing SynthFlow Engine...")
    
    # 1. Initialize Core Managers
    component_manager = ComponentManager()

    strategy_manager = StrategyManager()
    state_tracker = StateTracker()
    config_parser = ConfigParser()
    
    # 2. Register Components
    logger.info("Registering Components...")
    component_manager.register_component("element_locator", ElementLocator)
    component_manager.register_component("operation_executor", OperationExecutor)
    component_manager.register_component("review_service", ReviewService)
    component_manager.register_component("human_interaction", HumanInteraction)
    component_manager.register_component("data_extractor", DataExtractor)
    component_manager.register_component("data_entry", DataEntry)
    
    # 3. Initialize Engine
    engine = ExecutionEngine(component_manager, strategy_manager, state_tracker)
    
    # 4. Load Configuration
    config_path = os.path.join("config", "sample_process.yaml")
    logger.info(f"Loading configuration from {config_path}...")
    try:
        process_model = config_parser.load_config(config_path)
        logger.info(f"Process Loaded: {process_model.name} (v{process_model.version})")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return

    # 5. Execute Process
    logger.info("--- Starting Execution ---")
    result = engine.execute(process_model)
    
    # 6. Output Results
    logger.info("--- Execution Finished ---")
    logger.info(f"Status: {result.status.value}")
    if result.error:
        logger.error(f"Error: {result.error}")
    
    logger.info("--- Execution Timeline ---")
    timeline = state_tracker.get_timeline()
    for event in timeline.events:
        logger.info(f"[{event.timestamp.strftime('%H:%M:%S')}] Step: {event.step_id or 'System'} | Status: {event.status}")
        if event.details:
            logger.info(f"   Details: {event.details}")

if __name__ == "__main__":
    main()

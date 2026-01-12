import os
import sys
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from synthflow.components.element_locator import ElementLocator
from synthflow.components.operation_executor import OperationExecutor
from synthflow.components.review_service import ReviewService
from synthflow.core.component_manager import ComponentManager
from synthflow.core.config_parser import ConfigParser
from synthflow.core.execution_engine import ExecutionEngine, ExecutionStatus
from synthflow.core.state_tracker import StateTracker
from synthflow.core.strategy_manager import StrategyManager


class ExecutionEngineTests(unittest.TestCase):
    def setUp(self):
        self.component_manager = ComponentManager()
        self.strategy_manager = StrategyManager()
        self.state_tracker = StateTracker()
        self.parser = ConfigParser()
        self.component_manager.register_component("element_locator", ElementLocator)
        self.component_manager.register_component("operation_executor", OperationExecutor)
        self.component_manager.register_component("review_service", ReviewService)

    def test_execute_sample_process(self):
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
        path = os.path.join(config_dir, "sample_process.yaml")
        model = self.parser.load_config(path)
        engine = ExecutionEngine(self.component_manager, self.strategy_manager, self.state_tracker)
        result = engine.execute(model)
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        timeline = self.state_tracker.get_timeline()
        self.assertGreater(len(timeline.events), 0)


if __name__ == "__main__":
    unittest.main()


import time
from typing import Any, Dict
from .base import Component
from ..utils.logger import get_logger

class HumanInteraction(Component):
    def __init__(self):
        self.logger = get_logger("HumanInteraction")

    @property
    def name(self) -> str:
        return "human_interaction"
        
    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        pass
        
    def execute(self, context: Any, params: Dict[str, Any]) -> Any:
        instruction = params.get("instruction", "Waiting for user action...")
        timeout = params.get("timeout", 300) # Default 5 minutes
        options = params.get("options", ["execute", "skip", "stop"])
        
        tracker = context.get("_tracker")
        if not tracker:
            self.logger.warning("No StateTracker found in context. Using simulation mode.")
            time.sleep(2)
            return {"status": "completed", "action": "execute"} # Default action

        self.logger.info(f"=== HUMAN INTERACTION REQUIRED ===")
        self.logger.info(f"Instruction: {instruction}")
        
        # 1. Register pending interaction
        interaction_id = str(time.time())
        tracker.set_pending_interaction({
            "id": interaction_id,
            "instruction": instruction,
            "options": options,
            "timestamp": time.time()
        })
        
        # 2. Wait for result
        self.logger.info(f"Waiting for user input (timeout={timeout}s)...")
        result = tracker.wait_for_interaction_result(timeout=int(timeout))
        
        if result:
            self.logger.info(f"User responded: {result}")
            return result
        else:
            self.logger.error("Interaction timed out")
            raise TimeoutError("Human interaction timed out")

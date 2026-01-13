from typing import Any, Dict, List
import time
from .base import Component
from ..utils.logger import get_logger

class DataExtractor(Component):
    def __init__(self):
        self.logger = get_logger("DataExtractor")

    @property
    def name(self) -> str:
        return "data_extractor"
        
    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        pass
        
    def execute(self, context: Any, params: Dict[str, Any]) -> Any:
        source = params.get("source", "unknown")
        
        self.logger.info(f"Extracting data from {source}")
        
        # Mock data based on source
        data = {
            "task_id": "TASK-" + str(int(time.time())),
            "evidence_status": "valid",
            "extracted_fields": {
                "name": "John Doe",
                "id_number": "123456789",
                "risk_score": 10
            }
        }
        
        self.logger.info(f"Extracted data: {data}")
        return data

class DataEntry(Component):
    def __init__(self):
        self.logger = get_logger("DataEntry")

    @property
    def name(self) -> str:
        return "data_entry"
        
    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        pass
        
    def execute(self, context: Any, params: Dict[str, Any]) -> Any:
        target = params.get("target")
        input_data = params.get("data")
        
        self.logger.info(f"Entering data into {target}")
        self.logger.info(f"Data content: {input_data}")
        
        return {"status": "success", "target": target}

import yaml
import json
import os
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError

class StepModel(BaseModel):
    id: str
    type: str  # e.g., "click", "input", "review", "ai_process"
    name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    next_step: Optional[str] = None
    on_error: Optional[str] = None # Strategy for error handling

class ProcessModel(BaseModel):
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    steps: List[StepModel]
    
    def get_step(self, step_id: str) -> Optional[StepModel]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

class ValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)

class ConfigParser:
    """
    负责解析YAML/JSON配置，生成可执行的流程模型
    """
    
    def load_config(self, config_path: str) -> ProcessModel:
        """
        Load configuration from a file (YAML or JSON)
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                data = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                data = json.load(f)
            else:
                raise ValueError("Unsupported configuration format. Use .yaml or .json")
        
        validation = self.validate_config(data)
        if not validation.valid:
            raise ValueError(f"Invalid configuration: {'; '.join(validation.errors)}")
            
        return ProcessModel(**data)

    def validate_config(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration data structure
        """
        try:
            ProcessModel(**config_data)
            return ValidationResult(valid=True)
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return ValidationResult(valid=False, errors=errors)

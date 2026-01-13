import yaml
import json
import os
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError

# --- L-A-V-D Data Structures ---

class LocatorModel(BaseModel):
    type: str = Field(..., description="e.g., css, xpath, text, image")
    value: str
    frame: Optional[str] = None
    timeout: Optional[int] = 5000

class ActionModel(BaseModel):
    type: str = Field(..., description="e.g., click, input, wait, screenshot")
    human_like: bool = True
    delay_before: float = 0.0
    delay_after: float = 0.0
    # For input/type actions
    value: Optional[Union[str, float, int]] = None 

class VerificationModel(BaseModel):
    check: str = Field(..., description="e.g., visible, text_contains, url_contains")
    selector: Optional[str] = None # Simple selector string for verification target
    value: Optional[str] = None
    timeout: int = 5000
    on_fail: Optional[str] = "error" # error, retry, ignore

class DataBindingModel(BaseModel):
    # Extract output from this step to context
    # Key = Context Variable Name, Value = Source Path (e.g. "return_value.url")
    outputs: Dict[str, str] = Field(default_factory=dict)

class LoopModel(BaseModel):
    type: str = Field(..., description="e.g., count, while_selector, for_each")
    count: Optional[int] = None
    condition: Optional[str] = None
    items: Optional[str] = None # For for_each, e.g., "${list_variable}"
    steps: List['StepModel'] = Field(default_factory=list)

class BranchModel(BaseModel):
    condition: str
    steps: List['StepModel'] = Field(default_factory=list)

class StepModel(BaseModel):
    id: str
    type: str  # e.g., "interaction", "logic", "review", "loop", "condition"
    name: Optional[str] = None
    
    # Legacy params support (for backward compatibility)
    params: Dict[str, Any] = Field(default_factory=dict)
    
    # New L-A-V-D structures (Optional for now to allow mixed use)
    locator: Optional[LocatorModel] = None
    action: Optional[ActionModel] = None
    verification: Optional[VerificationModel] = None
    data: Optional[DataBindingModel] = None

    # Logic structures
    loop: Optional[LoopModel] = None
    branches: Optional[List[BranchModel]] = None

    next_step: Optional[str] = None
    on_error: Optional[str] = None

# Resolve forward references
StepModel.update_forward_refs()
LoopModel.update_forward_refs()
BranchModel.update_forward_refs()

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

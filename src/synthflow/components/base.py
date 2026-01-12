from abc import ABC, abstractmethod
from typing import Any, Dict

class Component(ABC):
    """
    Base class for all pluggable components
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass
        
    @abstractmethod
    def execute(self, context: Any, params: Dict[str, Any]) -> Any:
        pass

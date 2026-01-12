from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

class Strategy(ABC):
    @abstractmethod
    def apply(self, context: Any, **kwargs) -> Any:
        pass

class StrategyManager:
    """
    负责管理各环节的可替换策略
    """
    
    def __init__(self):
        self._strategies: Dict[str, Strategy] = {}
        self.logger = get_logger("StrategyManager")

    def set_strategy(self, context_key: str, strategy: Strategy):
        """
        Set a strategy for a specific context
        """
        self.logger.info(f"Setting strategy for '{context_key}': {strategy.__class__.__name__}")
        self._strategies[context_key] = strategy

    def get_current_strategy(self, context_key: str) -> Optional[Strategy]:
        """
        Get the strategy for the given context
        """
        return self._strategies.get(context_key)
        
    def execute_strategy(self, context_key: str, context_data: Any, **kwargs) -> Any:
        strategy = self.get_current_strategy(context_key)
        if strategy:
            return strategy.apply(context_data, **kwargs)
        return None

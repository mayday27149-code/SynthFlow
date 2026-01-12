from typing import Dict, Type, Optional, Any
from ..components.base import Component
from ..utils.logger import get_logger

class ComponentManager:
    """
    负责动态加载和管理功能组件
    """
    
    def __init__(self):
        self._components: Dict[str, Type[Component]] = {}
        self._instances: Dict[str, Component] = {}
        self.logger = get_logger("ComponentManager")

    def register_component(self, component_type: str, component_cls: Type[Component]):
        """
        Register a component class for a specific type
        """
        self.logger.info(f"Registering component: {component_type} -> {component_cls.__name__}")
        self._components[component_type] = component_cls

    def get_component(self, component_type: str, config: Optional[Dict[str, Any]] = None) -> Component:
        """
        Get or create an instance of a component
        """
        if component_type not in self._components:
            raise ValueError(f"Component type '{component_type}' not registered")
            
        # For simplicity, we'll create a new instance or return a singleton if we wanted.
        # Here let's cache instances by type (singleton per type for now, or per request if needed)
        # The design implies "getComponent" might return an instance.
        
        if component_type not in self._instances:
            cls = self._components[component_type]
            instance = cls()
            if config:
                instance.initialize(config)
            else:
                instance.initialize({})
            self._instances[component_type] = instance
            
        return self._instances[component_type]

    def load_plugin(self, plugin_path: str):
        """
        Dynamic loading of plugins (Placeholder for future implementation)
        """
        pass

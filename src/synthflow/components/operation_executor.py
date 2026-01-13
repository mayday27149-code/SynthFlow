from typing import Any, Dict
from .base import Component
from ..utils.logger import get_logger
from ..core.browser_manager import BrowserContextManager
from ..core.human_simulator import HumanSimulator

class OperationExecutor(Component):
    def __init__(self):
        self.logger = get_logger("OperationExecutor")
        self.browser_manager = BrowserContextManager()

    @property
    def name(self) -> str:
        return "OperationExecutor"
        
    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = config

    def execute(self, context: Any, params: Dict[str, Any]) -> Any:
        # Check if we are using the new L-A-V structure
        # If 'action' is a dict, it definitely comes from L-A-V model_dump
        # Or if 'locator' is present.
        
        if isinstance(params.get("action"), dict) or "locator" in params:
            return self._execute_lav(context, params)
        
        # Fallback to legacy mode
        return self._execute_legacy(context, params)

    def _execute_lav(self, context: Any, config: Dict[str, Any]) -> Any:
        """
        Execute using the new L-A-V-D structure
        """
        locator_conf = config.get("locator", {})
        action_conf = config.get("action", {})
        verify_conf = config.get("verification", {})
        
        # 1. Locate
        selector = locator_conf.get("value")
        if not selector and action_conf.get("type") not in ["open", "wait"]:
             raise ValueError("Locator value required")
             
        # 2. Action
        action_type = action_conf.get("type")
        human_like = action_conf.get("human_like", True)
        value = action_conf.get("value")
        
        self.logger.info(f"[LAV] Action: {action_type} on {selector}")
        
        page = self.browser_manager.get_page()
        simulator = HumanSimulator(page) if human_like else None
        
        result = {}
        
        try:
            # Pre-action delay
            if action_conf.get("delay_before"):
                page.wait_for_timeout(action_conf["delay_before"] * 1000)
            
            # Execute Action
            if action_type == "open":
                if not value: raise ValueError("URL required for open")
                page.goto(str(value))
                
            elif action_type == "click":
                if human_like:
                    simulator.click(selector)
                else:
                    page.click(selector)
                    
            elif action_type == "input" or action_type == "type":
                if human_like:
                    simulator.type(selector, str(value))
                else:
                    page.fill(selector, str(value))
                    
            elif action_type == "wait":
                delay = float(value) if value else 1.0
                page.wait_for_timeout(delay * 1000)
                
            elif action_type == "screenshot":
                path = str(value) if value else "screenshot.png"
                page.screenshot(path=path)
                result["path"] = path
                
            elif action_type == "read_text":
                # New action: Extract text
                content = page.text_content(selector)
                result["text"] = content
                
            else:
                self.logger.warning(f"Unknown action: {action_type}")
            
            # Post-action delay
            if action_conf.get("delay_after"):
                page.wait_for_timeout(action_conf["delay_after"] * 1000)
                
            # 3. Verification
            if verify_conf:
                self._verify(page, verify_conf)
                
            result["status"] = "success"
            return result
            
        except Exception as e:
            self.logger.error(f"[LAV] Failed: {e}")
            raise e

    def _verify(self, page, conf: Dict[str, Any]):
        check = conf.get("check")
        selector = conf.get("selector")
        timeout = conf.get("timeout", 5000)
        
        try:
            if check == "visible":
                page.wait_for_selector(selector, state="visible", timeout=timeout)
            elif check == "url_contains":
                # Simple check, might need retry logic
                if conf.get("value") not in page.url:
                    raise Exception(f"URL mismatch: expected {conf.get('value')} in {page.url}")
        except Exception as e:
            if conf.get("on_fail") == "ignore":
                self.logger.warning(f"Verification failed (ignored): {e}")
            else:
                raise e

    def _execute_legacy(self, context: Any, params: Dict[str, Any]) -> Any:
        action = params.get("action")
        target = params.get("target") # selector
        value = params.get("value")
        human_like = params.get("human_like", True) # Default to True for this use case
        
        self.logger.info(f"Performing '{action}' on '{target}' with value '{value}' (human_like={human_like})")
        
        try:
            page = self.browser_manager.get_page()
            simulator = HumanSimulator(page) if human_like else None
            
            if action == "open":
                if not value:
                    raise ValueError("URL value is required for 'open' action")
                page.goto(value)
                return {"status": "success", "url": page.url}
                
            elif action == "click":
                if not target:
                    raise ValueError("Target selector is required for 'click' action")
                
                if human_like:
                    simulator.click(target)
                else:
                    page.click(target)
                return {"status": "success"}
                
            elif action == "type" or action == "input":
                if not target:
                    raise ValueError("Target selector is required for 'type' action")
                
                if human_like:
                    simulator.type(target, str(value) if value is not None else "")
                else:
                    page.fill(target, str(value) if value is not None else "")
                return {"status": "success"}
                
            elif action == "screenshot":
                path = value or "screenshot.png"
                page.screenshot(path=path)
                return {"status": "success", "path": path}
                
            elif action == "wait":
                time_ms = float(value) * 1000 if value else 1000
                page.wait_for_timeout(time_ms)
                return {"status": "success"}
            
            else:
                self.logger.warning(f"Unknown action: {action}")
                return {"status": "skipped", "reason": "unknown_action"}
                
        except Exception as e:
            self.logger.error(f"Operation failed: {e}")
            raise e

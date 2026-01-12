from abc import ABC, abstractmethod

class AIAgentInterface(ABC):
    @abstractmethod
    def execute_instruction(self, instruction: str, context: dict):
        pass

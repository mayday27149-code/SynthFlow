from abc import ABC, abstractmethod

class ProcessMiningInterface(ABC):
    @abstractmethod
    def log_event(self, event_data):
        pass

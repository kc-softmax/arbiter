from abc import ABC, abstractmethod

class AbstractService(ABC):
    @abstractmethod
    def launch(self):
        pass
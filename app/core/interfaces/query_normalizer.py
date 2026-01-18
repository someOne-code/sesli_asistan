from abc import ABC, abstractmethod

class QueryNormalizer(ABC):
    """
    Interface for query normalization logic.
    Decouples the assistant service from specific normalization implementations.
    """
    
    @abstractmethod
    def normalize(self, query: str) -> str:
        """
        Normalizes the input query string (e.g. typos, filler words).
        Returns the clean, search-ready query string.
        """
        pass

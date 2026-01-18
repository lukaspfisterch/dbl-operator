from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence

class Projection(ABC):
    """Base class for all discrete projections over the event ledger."""
    
    @abstractmethod
    def feed(self, event: dict[str, Any]) -> None:
        """Process a single event to update internal state."""
        pass

    @abstractmethod
    def render(self) -> str:
        """Return a human-readable representation of the projection result."""
        pass

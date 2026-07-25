from typing import List, Protocol
from ..stream import Stream

class EquipmentCalculator(Protocol):
    """Protocol defining the interface for all equipment simulation modules.

    Every equipment calculator must implement the `calculate` method.
    """
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        """
        Performs thermodynamic calculations based on equipment specifications
        and input streams, returning a list of output streams.

        Args:
            specs: A dictionary of equipment-specific parameters.
            input_streams: A list of streams entering the equipment.

        Returns:
            A list of streams leaving the equipment.
        """
        ...

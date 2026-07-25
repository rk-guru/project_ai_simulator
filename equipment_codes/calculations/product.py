from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class ProductCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        # Just update enthalpy and pass through
        for s in input_streams:
            s.enthalpy = calculate_ideal_enthalpy(s)
        return input_streams

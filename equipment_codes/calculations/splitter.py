from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class SplitterCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        # For multiple outlets, we'll assume specs provides a list of fractions
        fractions = specs.get("splitFractions", [0.5, 0.5])

        out_streams = []
        for frac in fractions:
            s = Stream(
                temperature=in_stream.temperature,
                pressure=in_stream.pressure,
                flow_rate=in_stream.flow_rate * frac,
                compositions=in_stream.compositions.copy(),
                vapor_fraction=in_stream.vapor_fraction
            )
            s.enthalpy = calculate_ideal_enthalpy(s)
            out_streams.append(s)

        return out_streams

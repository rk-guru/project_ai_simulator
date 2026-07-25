from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class TankCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[-1]
        out_pres = specs.get("pressure", in_stream.pressure)

        out_stream = Stream(
            temperature=in_stream.temperature,
            pressure=out_pres,
            flow_rate=in_stream.flow_rate,
            compositions=in_stream.compositions.copy(),
            vapor_fraction=in_stream.vapor_fraction
        )
        out_stream.enthalpy = calculate_ideal_enthalpy(out_stream)
        return [out_stream]

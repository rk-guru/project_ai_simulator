from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class CoolerCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        out_temp = specs.get("outletTemperature", in_stream.temperature)

        out_stream = Stream(
            temperature=out_temp,
            pressure=in_stream.pressure,
            flow_rate=in_stream.flow_rate,
            compositions=in_stream.compositions.copy(),
            vapor_fraction=in_stream.vapor_fraction
        )
        out_stream.enthalpy = calculate_ideal_enthalpy(out_stream)
        return [out_stream]

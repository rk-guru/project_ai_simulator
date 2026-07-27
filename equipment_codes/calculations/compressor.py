from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class CompressorCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        out_pres = specs.get("outletPressure", in_stream.pressure)

        p_ratio = out_pres / in_stream.pressure if in_stream.pressure != 0 else 1.0
        out_temp = in_stream.temperature * (p_ratio ** 0.28)

        out_stream = Stream(
            temperature=out_temp,
            pressure=out_pres,
            flow_rate=in_stream.flow_rate,
            compositions=in_stream.compositions.copy(),
            vapor_fraction=in_stream.vapor_fraction
        )
        out_stream.enthalpy = calculate_ideal_enthalpy(out_stream)
        return [out_stream]

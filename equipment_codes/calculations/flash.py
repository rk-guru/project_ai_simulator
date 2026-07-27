from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class FlashCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        t_flash = specs.get("temperature", in_stream.temperature)
        p_flash = specs.get("pressure", in_stream.pressure)
        psi = specs.get("vaporFraction", 0.5)

        v_comp = {}
        l_comp = {}
        for comp, x in in_stream.compositions.items():
            # Simple K=1.5
            k = 1.5
            v_comp[comp] = x * k / (1 + psi * (k - 1))
            l_comp[comp] = x / (1 + psi * (k - 1))

        v_stream = Stream(temperature=t_flash, pressure=p_flash,
                            flow_rate=in_stream.flow_rate * psi,
                            compositions=v_comp, vapor_fraction=1.0)
        l_stream = Stream(temperature=t_flash, pressure=p_flash,
                            flow_rate=in_stream.flow_rate * (1 - psi),
                            compositions=l_comp, vapor_fraction=0.0)

        v_stream.enthalpy = calculate_ideal_enthalpy(v_stream)
        l_stream.enthalpy = calculate_ideal_enthalpy(l_stream)

        return [v_stream, l_stream]

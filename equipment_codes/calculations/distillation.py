from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class DistillationCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        recovery = specs.get("recovery", 0.95)
        overhead_comps = specs.get("overhead_components", [])

        v_comp, l_comp = {}, {}
        v_flow = 0

        for comp, x in in_stream.compositions.items():
            if comp in overhead_comps:
                v_comp[comp] = x * recovery
                l_comp[comp] = x * (1 - recovery)
                v_flow += x * recovery
            else:
                v_comp[comp] = x * (1 - recovery)
                l_comp[comp] = x * recovery
                v_flow += x * (1 - recovery)

        # Normalize
        tv = sum(v_comp.values())
        tl = sum(l_comp.values())
        if tv > 0: v_comp = {k: v/tv for k, v in v_comp.items()}
        if tl > 0: l_comp = {k: v/tl for k, v in l_comp.items()}

        v_stream = Stream(temperature=in_stream.temperature, pressure=in_stream.pressure,
                          flow_rate=in_stream.flow_rate * (v_flow if tv > 0 else 0),
                          compositions=v_comp, vapor_fraction=1.0)
        l_stream = Stream(temperature=in_stream.temperature, pressure=in_stream.pressure,
                          flow_rate=in_stream.flow_rate * (1 - v_flow if tv > 0 else 1),
                          compositions=l_comp, vapor_fraction=0.0)

        v_stream.enthalpy = calculate_ideal_enthalpy(v_stream)
        l_stream.enthalpy = calculate_ideal_enthalpy(l_stream)

        return [v_stream, l_stream]

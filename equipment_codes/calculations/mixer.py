from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class MixerCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        total_flow = sum(s.flow_rate for s in input_streams)
        if total_flow == 0:
            return input_streams

        weighted_temp = sum(s.temperature * s.flow_rate for s in input_streams) / total_flow

        final_comp = {}
        all_components = set()
        for s in input_streams:
            all_components.update(s.compositions.keys())

        for comp in all_components:
            total_molar_flow_comp = sum(s.flow_rate * s.compositions.get(comp, 0) for s in input_streams)
            final_comp[comp] = total_molar_flow_comp / total_flow

        pressure = specs.get("pressure", max(s.pressure for s in input_streams))
        vf = sum(s.vapor_fraction * s.flow_rate for s in input_streams) / total_flow

        out_stream = Stream(
            temperature=weighted_temp,
            pressure=pressure,
            flow_rate=total_flow,
            compositions=final_comp,
            vapor_fraction=vf
        )
        out_stream.enthalpy = calculate_ideal_enthalpy(out_stream)
        return [out_stream]

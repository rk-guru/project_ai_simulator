from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class HeatExchangerCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if len(input_streams) < 2:
            return input_streams

        eff = specs.get("efficiency", 0.9)
        s1, s2 = input_streams[0], input_streams[1]

        t1_final = s1.temperature + eff * (s2.temperature - s1.temperature)
        t2_final = s2.temperature + eff * (s1.temperature - s2.temperature)

        out1 = Stream(temperature=t1_final, pressure=s1.pressure, flow_rate=s1.flow_rate,
                      compositions=s1.compositions.copy(), vapor_fraction=s1.vapor_fraction)
        out2 = Stream(temperature=t2_final, pressure=s2.pressure, flow_rate=s2.flow_rate,
                      compositions=s2.compositions.copy(), vapor_fraction=s2.vapor_fraction)

        out1.enthalpy = calculate_ideal_enthalpy(out1)
        out2.enthalpy = calculate_ideal_enthalpy(out2)

        return [out1, out2]

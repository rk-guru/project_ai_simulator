from typing import List
from ..stream import Stream
from ..utils.thermo import calculate_ideal_enthalpy

class ReactorCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        if not input_streams:
            return []

        in_stream = input_streams[0]
        conversion = specs.get("conversion", 0.0)

        comp = in_stream.compositions.copy()
        if comp:
            reagents = list(comp.keys())
            reagent = reagents[0]
            amount = comp[reagent]
            comp[reagent] = amount * (1 - conversion)
            prod_name = f"Product_{reagent}"
            comp[prod_name] = comp.get(prod_name, 0) + (amount * conversion)
            total = sum(comp.values())
            comp = {k: v/total for k, v in comp.items()}

        out_stream = Stream(
            temperature=specs.get("outletTemperature", in_stream.temperature),
            pressure=in_stream.pressure,
            flow_rate=in_stream.flow_rate,
            compositions=comp,
            vapor_fraction=in_stream.vapor_fraction
        )
        out_stream.enthalpy = calculate_ideal_enthalpy(out_stream)
        return [out_stream]

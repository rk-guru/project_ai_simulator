from typing import List
from ..stream import Stream
from .base import EquipmentCalculator
from ..utils.thermo import calculate_ideal_enthalpy

class FeedCalculator:
    def calculate(self, specs: dict, input_streams: List[Stream]) -> List[Stream]:
        temp = specs.get("temperature", 298.15)
        pres = specs.get("pressure", 101325.0)
        flow = specs.get("flowRate", 0.0)

        compositions = {}
        compounds = specs.get("compounds", [])
        if compounds:
            for comp in compounds:
                compositions[comp["name"]] = comp["moleFraction"]
        else:
            compositions = {"GenericComponent": 1.0}

        s = Stream(
            temperature=temp,
            pressure=pres,
            flow_rate=flow,
            compositions=compositions,
            vapor_fraction=0.0
        )
        s.enthalpy = calculate_ideal_enthalpy(s)
        return [s]

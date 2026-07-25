from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Stream:
    """Represents a chemical process stream in a simulation.

    Attributes:
        temperature (float): Temperature in Kelvin (K).
        pressure (float): Pressure in Pascal (Pa).
        flow_rate (float): Molar flow rate in kmol/h.
        compositions (Dict[str, float]): Map of component name to mole fraction.
        vapor_fraction (float): Overall vapor fraction (0 to 1).
        enthalpy (float): Molar enthalpy in kJ/kmol.
        mass_flow_rate (Optional[float]): Mass flow rate in kg/h (calculated).
    """
    temperature: float
    pressure: float
    flow_rate: float
    compositions: Dict[str, float] = field(default_factory=dict)
    vapor_fraction: float = 0.0
    enthalpy: float = 0.0
    mass_flow_rate: Optional[float] = None

    def __repr__(self):
        return (f"Stream(T={self.temperature:.2f}K, P={self.pressure:.2f}Pa, "
                f"Flow={self.flow_rate:.2f}kmol/h, VF={self.vapor_fraction:.2f})")

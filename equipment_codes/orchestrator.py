import importlib
from typing import List, Dict, Any
from .stream import Stream
from .calculations.base import EquipmentCalculator
from .utils.thermo import calculate_molar_mass, mole_to_mass_fraction

class SimulationOrchestrator:
    """Orchestrates the chemical process simulation and generates a detailed results table."""

    def __init__(self):
        self.registry: Dict[str, List[Stream]] = {}

    def _get_calculator(self, equipment_type: str):
        module_name = equipment_type.lower().replace(" ", "_")
        mapping = {
            "distillationcolumn": "distillation",
            "heatexchanger": "heat_exchanger"
        }
        module_name = mapping.get(module_name, module_name)

        try:
            module = importlib.import_module(f".calculations.{module_name}", package="equipment_codes")
            for attr_name in dir(module):
                if attr_name.endswith("Calculator") and attr_name != "EquipmentCalculator":
                    return getattr(module, attr_name)()
        except (ImportError, AttributeError):
            return None

    def _get_stream_names(self, eq, outputs: List[Stream]) -> List[str]:
        if not outputs: return []

        eq_type = eq.type.lower()
        # Use name instead of id, replacing spaces with underscores
        name = eq.name.lower().replace(" ", "_") if eq.name else eq.id.lower()

        if "flash" in eq_type:
            return [f"{name}_vapor", f"{name}_liquid"]
        elif "distillation" in eq_type:
            return [f"{name}_distillate", f"{name}_bottom"]
        elif "splitter" in eq_type:
            return [f"{name}_{i+1}" for i in range(len(outputs))]
        else:
            return [f"{name}_outlet"] if len(outputs) == 1 else [f"{name}_outlet_{i+1}" for i in range(len(outputs))]

    def execute_simulation(self, ordered_equipment: List[Any], connections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        self.registry = {}
        table_results = []

        for eq in ordered_equipment:
            # 1. Resolve Inputs
            input_streams = []
            for conn in connections:
                if conn.get("target_id") == eq.id:
                    source_id = conn.get("source_id")
                    if source_id in self.registry:
                        input_streams.extend(self.registry[source_id])

            # 2. Calculate
            calc = self._get_calculator(eq.type)
            outputs = []
            energy_change = None

            if calc:
                try:
                    outputs = calc.calculate(eq.specs, input_streams)

                    # Calculate Energy Change (H_out - H_in)
                    h_in = sum(s.flow_rate * s.enthalpy for s in input_streams)
                    h_out = sum(s.flow_rate * s.enthalpy for s in outputs)
                    energy_change = h_out - h_in
                except Exception as e:
                    print(f"Error in {eq.id}: {e}")
                    outputs = input_streams
            else:
                outputs = input_streams

            self.registry[eq.id] = outputs

            # 3. Populate Table Rows
            stream_names = self._get_stream_names(eq, outputs)

            # Add Energy Row ONLY if there is a significant energy change
            if energy_change is not None and abs(energy_change) > 1e-6:
                name = eq.name.lower().replace(" ", "_") if eq.name else eq.id.lower()
                energy_name = f"{name}_energy"
                if "distillation" in eq.type.lower():
                    energy_name = f"{name}_condenser_energy" # Simplified

                table_results.append({
                    "Stream Name": energy_name,
                    "Equipment Name": eq.name if eq.name else eq.id,
                    "Equipment": eq.type,
                    "Temperature": None,
                    "Pressure": None,
                    "Molar Flowrate": None,
                    "Mass Flowrate": None,
                    "Vapor Fraction": None,
                    "Total Molar Composition (Mass Fraction)": None,
                    "Liquid Molar Composition": None,
                    "Vapor Molar Composition": None,
                    "Enthalpy": None,
                    "Energy Change": energy_change,
                })

            for i, s in enumerate(outputs):
                name = stream_names[i] if i < len(stream_names) else f"{eq.id}_outlet_{i+1}"

                # Mass calculations
                mw = calculate_molar_mass(s.compositions)
                mass_flow = s.flow_rate * mw
                mass_frac = mole_to_mass_fraction(s.compositions)

                # Composition splits
                l_comp = {k: v * (1 - s.vapor_fraction) for k, v in s.compositions.items()}
                v_comp = {k: v * s.vapor_fraction for k, v in s.compositions.items()}

                table_results.append({
                    "Stream Name": name,
                    "Equipment Name": eq.name if eq.name else eq.id,
                    "Equipment": eq.type,
                    "Temperature": s.temperature,
                    "Pressure": s.pressure,
                    "Molar Flowrate": s.flow_rate,
                    "Mass Flowrate": mass_flow,
                    "Vapor Fraction": s.vapor_fraction,
                    "Total Molar Composition (Mass Fraction)": mass_frac,
                    "Liquid Molar Composition": l_comp,
                    "Vapor Molar Composition": v_comp,
                    "Enthalpy": s.enthalpy,
                    "Energy Change": None,
                })

        return table_results

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
        eid = eq.id

        if "flash" in eq_type:
            return [f"{eid}_vapor", f"{eid}_liquid"]
        elif "distillation" in eq_type:
            return [f"{eid}_distillate", f"{eid}_bottom"]
        elif "splitter" in eq_type:
            return [f"{eid}_{i+1}" for i in range(len(outputs))]
        else:
            return [f"{eid}_outlet"] if len(outputs) == 1 else [f"{eid}_outlet_{i+1}" for i in range(len(outputs))]

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
                    # simplified: sum(out_flow * h_out) - sum(in_flow * h_in)
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

            # Add Energy Row if applicable
            if energy_change is not None:
                energy_name = f"{eq.id}_energy"
                if "distillation" in eq.type.lower():
                    # simplified: split between condenser and boiler
                    energy_name = f"{eq.id}_condenser_energy" # In real world we'd have separate calcs

                table_results.append({
                    "Stream Name": energy_name,
                    "Equipment ID": eq.id,
                    "Equipment": eq.type,
                    "Energy Change": energy_change,
                    # Other columns empty for energy rows
                })

            for i, s in enumerate(outputs):
                name = stream_names[i] if i < len(stream_names) else f"{eq.id}_outlet_{i+1}"

                # Mass calculations
                mw = calculate_molar_mass(s.compositions)
                mass_flow = s.flow_rate * mw
                mass_frac = mole_to_mass_fraction(s.compositions)

                # Composition splits (Liquid/Vapor)
                # For simple ideal simulation: we treat the stream as a single phase
                # or split by vapor fraction.
                l_comp = {k: v * (1 - s.vapor_fraction) for k, v in s.compositions.items()}
                v_comp = {k: v * s.vapor_fraction for k, v in s.compositions.items()}

                table_results.append({
                    "Stream Name": name,
                    "Equipment ID": eq.id,
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
                })

        return table_results

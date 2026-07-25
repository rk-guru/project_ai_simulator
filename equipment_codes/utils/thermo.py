# Molecular weights of common components (g/mol)
MOLECULAR_WEIGHTS = {
    "Benzene": 78.11,
    "Toluene": 92.14,
    "Ethylbenzene": 106.16,
    "Xylene": 106.16,
    "Water": 18.02,
    "GenericComponent": 100.0,
}

def get_mw(component: str) -> float:
    """Return molecular weight of a component."""
    return MOLECULAR_WEIGHTS.get(component, 100.0)

def mole_to_mass_fraction(compositions: dict) -> dict:
    """Convert mole fractions to mass fractions."""
    total_mass = sum(x * get_mw(comp) for comp, x in compositions.items())
    if total_mass == 0:
        return {comp: 0.0 for comp in compositions}
    return {comp: (x * get_mw(comp)) / total_mass for comp, x in compositions.items()}

def calculate_molar_mass(compositions: dict) -> float:
    """Calculate average molar mass of a mixture."""
    return sum(x * get_mw(comp) for comp, x in compositions.items())

def calculate_ideal_enthalpy(stream, reference_temp=298.15):
    """
    Calculate simplified ideal enthalpy (kJ/kmol).
    H = Cp * (T - Tref)
    Using an average Cp = 150 J/(mol*K) = 150 kJ/(kmol*K)
    """
    cp_avg = 150.0
    return cp_avg * (stream.temperature - reference_temp)

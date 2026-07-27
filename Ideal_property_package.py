import pandas as pd
import numpy as np
from scipy.optimize import brentq


# ==========================================
# Empirical Equation Definitions
# ==========================================
def eq_polynomial(T, A, B, C, D, E=0.0):
    return A + B * T + C * (T ** 2) + D * (T ** 3) + E * (T ** 4)


def eq_dippr101(T, A, B, C, D, E):
    # Used for Vapor Pressure and Liquid Viscosity
    # Note: np.clip prevents overflow errors in log/exp if T is extreme
    T = np.clip(T, 1e-10, None)
    return np.exp(A + B / T + C * np.log(T) + D * (T ** E))


def eq_dippr105(T, A, B, C, D):
    # Used for Liquid Density
    # Ensure no negative bases for non-integer exponents
    if np.any(1 - T / C < 0):
        return 0.0  # Above critical temp, liquid density approaches undefined/gas state
    return A / (B ** (1 + (1 - T / C) ** D))


def eq_heat_of_vap(T, Tc, A, B, C, D, E):
    # Heat of vaporization scaled by 1000
    Tr = T / Tc
    # Return 0 if above critical temperature
    if Tr >= 1.0:
        return 0.0
    exponent = B + C * Tr + D * (Tr ** 2) + E * (Tr ** 3)
    return (A * (1 - Tr) ** exponent) / 1000.0


# ==========================================
# Main Flash and Property Calculation
# ==========================================
def ideal_flash_with_properties(input_data, db_path="Open_source_db2.csv"):
    """
    Performs an isothermal VLE flash calculation and evaluates thermodynamic
    and transport properties for pure components and mixtures.
    """
    # 1. Parse Input
    comp_dict = input_data.get("composition", {})
    T = input_data.get("Temperature")
    P = input_data.get("pressure")
    F = input_data.get("Flow rate", 1.0)

    compounds = list(comp_dict.keys())
    z = np.array(list(comp_dict.values()))
    z = z / np.sum(z)  # Normalize

    # 2. Load DB & Extract Coefficients
    try:
        db = pd.read_csv(db_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Database file '{db_path}' not found.")

    props = {
        "Tc": [], "Vap": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "GasCp": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "LiqDen": {"A": [], "B": [], "C": [], "D": []},
        "LiqVis": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "LiqCp": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "LiqThCond": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "Hvap": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "SolDen": {"A": [], "B": [], "C": [], "D": [], "E": []},
        "SolCp": {"A": [], "B": [], "C": [], "D": [], "E": []}
    }

    for comp in compounds:
        row = db[db["Name"] == comp]
        if row.empty:
            raise ValueError(f"Compound '{comp}' not found in DB.")
        row = row.iloc[0]

        props["Tc"].append(row["Critical_Temperature"])

        # Vapor Pressure
        props["Vap"]["A"].append(row["Vap_P_A"]);
        props["Vap"]["B"].append(row["Vap_P_B"])
        props["Vap"]["C"].append(row["Vap_P_C"]);
        props["Vap"]["D"].append(row["Vap_P_D"]);
        props["Vap"]["E"].append(row["Vap_P_E"])
        # Ideal Gas Cp
        props["GasCp"]["A"].append(row["Gas_Cp_A"]);
        props["GasCp"]["B"].append(row["Gas_Cp_B"])
        props["GasCp"]["C"].append(row["Gas_Cp_C"]);
        props["GasCp"]["D"].append(row["Gas_Cp_D"]);
        props["GasCp"]["E"].append(row["Gas_Cp_E"])
        # Liquid Density
        props["LiqDen"]["A"].append(row["Lq_Den_A"]);
        props["LiqDen"]["B"].append(row["Lq_Den_B"])
        props["LiqDen"]["C"].append(row["Lq_Den_C"]);
        props["LiqDen"]["D"].append(row["Lq_Den_D"])
        # Liquid Viscosity
        props["LiqVis"]["A"].append(row["Liq_vis_A"]);
        props["LiqVis"]["B"].append(row["Liq_vis_B"])
        props["LiqVis"]["C"].append(row["Liq_vis_C"]);
        props["LiqVis"]["D"].append(row["Liq_vis_D"]);
        props["LiqVis"]["E"].append(row["Liq_vis_E"])
        # Liquid Cp
        props["LiqCp"]["A"].append(row["Liq_Cp_A"]);
        props["LiqCp"]["B"].append(row["Liq_Cp_B"])
        props["LiqCp"]["C"].append(row["Liq_Cp_C"]);
        props["LiqCp"]["D"].append(row["Liq_Cp_D"]);
        props["LiqCp"]["E"].append(row["Liq_Cp_E"])
        # Liquid Thermal Conductivity
        props["LiqThCond"]["A"].append(row["Liq_Therm_con_A"]);
        props["LiqThCond"]["B"].append(row["Liq_Therm_con_B"])
        props["LiqThCond"]["C"].append(row["Liq_Therm_con_C"]);
        props["LiqThCond"]["D"].append(row["Liq_Therm_con_D"]);
        props["LiqThCond"]["E"].append(row["Liq_Therm_con_E"])
        # Heat of Vaporization
        props["Hvap"]["A"].append(row["Heat_of_vap_A"]);
        props["Hvap"]["B"].append(row["Heat_of_vap_B"])
        props["Hvap"]["C"].append(row["Heat_of_vap_C"]);
        props["Hvap"]["D"].append(row["Heat_of_vap_D"]);
        props["Hvap"]["E"].append(row["Heat_of_vap_E"])

        # Solid Properties (Fallback to 0 if not present in DB)
        props["SolDen"]["A"].append(row.get("Solid_Den_A", 0));
        props["SolDen"]["B"].append(row.get("Solid_Den_B", 0))
        props["SolDen"]["C"].append(row.get("Solid_Den_C", 0));
        props["SolDen"]["D"].append(row.get("Solid_Den_D", 0));
        props["SolDen"]["E"].append(row.get("Solid_Den_E", 0))
        props["SolCp"]["A"].append(row.get("Solid_Cp_A", 0));
        props["SolCp"]["B"].append(row.get("Solid_Cp_B", 0))
        props["SolCp"]["C"].append(row.get("Solid_Cp_C", 0));
        props["SolCp"]["D"].append(row.get("Solid_Cp_D", 0));
        props["SolCp"]["E"].append(row.get("Solid_Cp_E", 0))

    # Convert lists to numpy arrays for vectorized math
    for category in props.keys():
        if isinstance(props[category], dict):
            for param in props[category].keys():
                props[category][param] = np.array(props[category][param], dtype=float)
        else:
            props[category] = np.array(props[category], dtype=float)

    # 3. Calculate Phase Equilibrium (VLE)
    P_sat = eq_dippr101(T, props["Vap"]["A"], props["Vap"]["B"], props["Vap"]["C"], props["Vap"]["D"],
                        props["Vap"]["E"])
    K = P_sat / P

    def rachford_rice(V):
        return np.sum((z * (K - 1)) / (1 + V * (K - 1)))

    f0 = rachford_rice(0.0)
    f1 = rachford_rice(1.0)

    if f0 <= 0:
        V = 0.0;
        x = z;
        y = z * K / np.sum(z * K)
    elif f1 >= 0:
        V = 1.0;
        y = z;
        x = (z / K) / np.sum(z / K)
    else:
        V = brentq(rachford_rice, 0.0, 1.0)
        x = z / (1 + V * (K - 1))
        y = K * x

    # 4. Calculate Pure Component Properties
    gas_cp_pure = eq_polynomial(T, props["GasCp"]["A"], props["GasCp"]["B"], props["GasCp"]["C"], props["GasCp"]["D"],
                                props["GasCp"]["E"])
    liq_den_pure = eq_dippr105(T, props["LiqDen"]["A"], props["LiqDen"]["B"], props["LiqDen"]["C"],
                               props["LiqDen"]["D"])
    liq_vis_pure = eq_dippr101(T, props["LiqVis"]["A"], props["LiqVis"]["B"], props["LiqVis"]["C"],
                               props["LiqVis"]["D"], props["LiqVis"]["E"])
    liq_cp_pure = eq_polynomial(T, props["LiqCp"]["A"], props["LiqCp"]["B"], props["LiqCp"]["C"], props["LiqCp"]["D"],
                                props["LiqCp"]["E"])
    liq_thcond_pure = eq_polynomial(T, props["LiqThCond"]["A"], props["LiqThCond"]["B"], props["LiqThCond"]["C"],
                                    props["LiqThCond"]["D"], props["LiqThCond"]["E"])
    sol_den_pure = eq_polynomial(T, props["SolDen"]["A"], props["SolDen"]["B"], props["SolDen"]["C"],
                                 props["SolDen"]["D"], props["SolDen"]["E"])
    sol_cp_pure = eq_polynomial(T, props["SolCp"]["A"], props["SolCp"]["B"], props["SolCp"]["C"], props["SolCp"]["D"],
                                props["SolCp"]["E"])

    # Vectorized loop for Hvap due to branching logic (Tc dependency)
    hvap_pure = np.array([
        eq_heat_of_vap(T, props["Tc"][i], props["Hvap"]["A"][i], props["Hvap"]["B"][i], props["Hvap"]["C"][i],
                       props["Hvap"]["D"][i], props["Hvap"]["E"][i])
        for i in range(len(compounds))
    ])

    # 5. Ideal Mixture Properties (Simple Mixing Rules)
    # Gas Cp = sum(y_i * Gas_Cp_i)
    gas_cp_mix = np.sum(y * gas_cp_pure)
    # Liquid Cp = sum(x_i * Liq_Cp_i)
    liq_cp_mix = np.sum(x * liq_cp_pure)
    # Liquid Thermal Cond = sum(x_i * ThCond_i)
    liq_thcond_mix = np.sum(x * liq_thcond_pure)
    # Liquid Density = 1 / sum(x_i / rho_i) -- Amagat's law / Ideal solution
    liq_den_mix = 1.0 / np.sum(x / np.clip(liq_den_pure, 1e-10, None))
    # Liquid Viscosity = exp(sum(x_i * ln(vis_i))) -- Arrhenius logarithmic mixing
    liq_vis_mix = np.exp(np.sum(x * np.log(np.clip(liq_vis_pure, 1e-20, None))))

    # Fugacity for Ideal Model
    fugacity_L = x * P_sat
    fugacity_V = y * P

    # 6. Format Final Results
    return {
        "Vapor_Fraction": round(V, 4),
        "Liquid_Fraction": round(1 - V, 4),
        "Liquid_Composition": dict(zip(compounds, np.round(x, 6))),
        "Vapor_Composition": dict(zip(compounds, np.round(y, 6))),
        "Mixture_Properties": {
            "Ideal_Gas_Cp": round(gas_cp_mix, 4),
            "Liquid_Cp": round(liq_cp_mix, 4),
            "Liquid_Density": round(liq_den_mix, 4),
            "Liquid_Viscosity": "{:.4e}".format(liq_vis_mix),
            "Liquid_Thermal_Conductivity": round(liq_thcond_mix, 4)
        },
        "Pure_Component_Properties": {
            "Vapor_Pressure_Pa": dict(zip(compounds, np.round(P_sat, 2))),
            "Heat_of_Vap": dict(zip(compounds, np.round(hvap_pure, 2))),
            "Solid_Density": dict(zip(compounds, np.round(sol_den_pure, 2))),
            "Solid_Cp": dict(zip(compounds, np.round(sol_cp_pure, 2))),
            "Fugacity_Liquid_Pa": dict(zip(compounds, np.round(fugacity_L, 2))),
            "Fugacity_Vapor_Pa": dict(zip(compounds, np.round(fugacity_V, 2)))
        }
    }


# ==========================================
# Example usage:
# ==========================================
if __name__ == "__main__":
    input_data = {
        "composition": {
            "Methane": 0.4,
            "Ethane": 0.6
        },
        "Temperature": 180,  # Kelvin
        "pressure": 500000,  # Pascals (5 bar)
        "Flow rate": 100  # mol/s
    }

    # Ensure 'Open_source_db2.csv' exists in the working directory
    results = ideal_flash_with_properties(input_data)
    import pprint

    pprint.pprint(results)
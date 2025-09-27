from typing import TypedDict ,List ,Union
from langchain_core.messages import HumanMessage ,AIMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph ,START ,END
from dotenv import load_dotenv
from typing import Annotated , Sequence ,TypedDict
from langchain_core.messages import BaseMessage ,ToolMessage ,SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph  ,END ,START
from langgraph.prebuilt import ToolNode
from langchain.chat_models import init_chat_model
import os
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

import csv
import io
import math
import pandas as pd


class PropertyPackage:
    """
    A class to calculate a wide range of properties for a stream of chemicals.

    This class loads chemical data from a database and provides methods to
    calculate individual and mixture properties for a given stream at a
    specific temperature and pressure, including phase determination.
    """

    # R: Ideal Gas Constant in J/(mol*K)
    R = 8.314

    def __init__(self, stream_name, chemicals_with_fractions, temperature_K, pressure_Pa, molar_flowrate_mol_s):
        """
        Initializes the property package with a dictionary of chemicals, T, P, and flow rate.

        Args:
            chemicals_with_fractions (dict): A dictionary of chemical names and their
                                             mole fractions (e.g., {'Methane': 0.8, 'Water': 0.2}).
            temperature_K (float): The stream temperature in Kelvin.
            pressure_Pa (float): The stream pressure in Pascals.
            molar_flowrate_mol_s (float): The total molar flow rate of the stream in mol/s.
        """
        # Store the chemical names and mole fractions
        self.stream_name = stream_name
        self.chemicals = list(chemicals_with_fractions.keys())
        total_sum=sum(chemicals_with_fractions.values())

        self.mole_fractions = {key: value / total_sum for key, value in chemicals_with_fractions.items()}
        self.temperature_K = temperature_K
        self.pressure_Pa = pressure_Pa
        self.molar_flowrate_mol_s = molar_flowrate_mol_s

        # Load data from the database using pandas as requested
        # Note: You'll need an 'Open_soruce_db.csv' file in the same directory
        # In a real application, you might use a more robust database connection
        # try:
        self.data = pd.read_csv('Open_soruce_db.csv')
        # except FileNotFoundError:
        #     print("Warning: 'Open_soruce_db.csv' not found. Using a simulated database.")
        #     # Use the in-memory data if the file is not found
        #     self.data = self._load_simulated_database()

        # Initialize phase-specific properties to None
        self.phase = None
        self.vapor_fraction = None
        self.liquid_mole_fractions = None
        self.vapor_mole_fractions = None
        self.properties=None

#     def _load_simulated_database(self):
#         """
#         Loads the simulated chemical data from the internal CSV string into a pandas DataFrame.
#         This is a fallback if the external CSV is not present.
#         """
#         CHEMICAL_DATABASE_CSV = """
# Name,Critical_Temperature,Critical_Temp_unit,Critical_Pressure,Critical_pressure_unit,Critical_Volume,Critical_vol_unit,Critical_Compressibility,Boiling_point,Boiling_point_unit,Mol_wt,Liquid_volume_at_BP,Liquid_vol_unit_at_BP,AcentricityFactor,Heat_of_Formation,Heat_of_Formation_unit,Gibbs_Energy_Of_Formation,Gibbs_Energy_Of_Formation_unit,Heat_of_combustion,Heat_of_combustion_unit,Lq_Den_A,Lq_Den_B,Lq_Den_C,Lq_Den_D,Lq_Den_Tmin,Lq_Den_Tmax,Lq_Den_unit,Vap_P_A,Vap_P_B,Vap_P_C,Vap_P_D,Vap_P_E,Vap_P_Tmin,Vap_P_Tmax,Vap_P_unit,Liq_Cp_A,Liq_Cp_B,Liq_Cp_C,Liq_Cp_D,Liq_Cp_E,Liq_Cp_Tmin,Liq_Cp_Tmax,Liq_Cp_unit,Gas_Cp_A,Gas_Cp_B,Gas_Cp_C,Gas_Cp_D,Gas_Cp_E,Gas_Cp_Tmin,Gas_Cp_Tmax,Gas_Cp_unit,Liq_vis_A,Liq_vis_B,Liq_vis_C,Liq_vis_D,Liq_vis_E,Liq_vis_Tmin,Liq_vis_Tmax,Liq_vis_unit,Liq_Therm_con_A,Liq_Therm_con_B,Liq_Therm_con_C,Liq_Therm_con_D,Liq_Therm_con_E,Liq_Therm_con_Tmin,Liq_Therm_con_Tmax,Liq_Therm_con_unit,Vap_Therm_con_A,Vap_Therm_con_B,Vap_Therm_con_C,Vap_Therm_con_D,Vap_Therm_con_Tmin,Vap_Therm_con_Tmax,Vap_Therm_con_unit,Heat_of_vap_A,Heat_of_vap_B,Heat_of_vap_C,Heat_of_vap_D,Heat_of_vap_E,Heat_of_vap_Tmin,Heat_of_vap_Tmax,Heat_of_vap_unit
# Methane,190.56,K,4.599,MPa,,,,,111.66,K,16.042,,,-0.011,-74.85,kJ/mol,,,,,145.42,1.385,258.96,,111.7,190.56,kg/m3,6.61113,-641.527,1.2584e-09,2,0.0,,,,,5.539,0.0305,0.0001,,298.15,1000,J/(mol K),34.331,-5.465e-02,3.159e-04,-1.491e-07,,298.15,1500,J/(mol K),,,,,,,,,,,0.005574,0.01633,0.000032,0.0,,,,0.00396,0.000045,0.0000000003,,200,600,W/m.K,242.0,-2.36,0.0,0.0,0.0,111.66,190.56,J/mol
# Water,647.1,K,22.06,MPa,,,,,373.15,K,18.015,,,-0.344,-285.83,kJ/mol,,,,,999.0,0.000,273.15,373.15,kg/m3,8.07131,1730.63,233.426,0.0,0.0,,,,,61.43,3.023E-02,0.0,0.0,0.0,273.15,373.15,J/(mol K),33.32,-0.2526e-02,-0.201e-05,0.002e-08,,298.15,1000,J/(mol K),33.32,-0.2526e-02,-0.201e-05,0.002e-08,,298.15,1000,J/(mol K),0.0005,0.000033,-0.0000000003,,273.15,647.1,W/m.K,45000.0,-50.0,0.0,0.0,0.0,273.15,647.1,J/mol
# """
#         return pd.read_csv(io.StringIO(CHEMICAL_DATABASE_CSV))

    def _get_data(self, chemical_name):
        """
        Helper method to retrieve data for a specific chemical from the DataFrame.
        Returns a pandas Series for the specified chemical's row.
        """
        try:
            return self.data.loc[self.data['Name'] == chemical_name].iloc[0]
        except IndexError:
            raise ValueError(f"Chemical '{chemical_name}' not found in database.")

    # --- Individual Property Calculation Methods ---

    def _calculate_ideal_gas_cp(self, chemical_name, temperature_K):
        """
        Calculates the ideal gas molar heat capacity (Cp) for a chemical using a polynomial.
        Formula: Cp = A + B*T + C*T^2 + D*T^3 + E*T^4

        Returns:
            float: Molar heat capacity in J/(mol*K).
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Gas_Cp_A'])
            B = float(chem_data['Gas_Cp_B'])
            C = float(chem_data['Gas_Cp_C'])
            D = float(chem_data['Gas_Cp_D'])
            E = float(chem_data.get('Gas_Cp_E', 0.0))

            cp = A + B * T + C * (T ** 2) + D * (T ** 3) + E * (T ** 4)
            return cp
        except (ValueError, KeyError) as e:
            return None

    def _calculate_ideal_enthalpy(self, chemical_name, temperature_K, T_ref=298.15):
        """
        Calculates the ideal gas molar enthalpy (H) for a chemical relative to a
        reference temperature (T_ref) and the heat of formation.

        Returns:
            float: Molar enthalpy in J/mol.
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            H_form = float(chem_data['Heat_of_Formation']) * 1000
            A = float(chem_data['Gas_Cp_A'])
            B = float(chem_data['Gas_Cp_B'])
            C = float(chem_data['Gas_Cp_C'])
            D = float(chem_data['Gas_Cp_D'])
            E = float(chem_data.get('Gas_Cp_E', 0.0))

            sensible_heat = (
                    A * (T - T_ref) +
                    (B / 2) * (T ** 2 - T_ref ** 2) +
                    (C / 3) * (T ** 3 - T_ref ** 3) +
                    (D / 4) * (T ** 4 - T_ref ** 4) +
                    (E / 5) * (T ** 5 - T_ref ** 5)
            )

            total_enthalpy = H_form + sensible_heat
            return total_enthalpy

        except (ValueError, KeyError) as e:
            return None

    def _calculate_liquid_enthalpy(self, chemical_name, temperature_K, T_ref=298.15):
        """
        Calculates the liquid molar enthalpy (H) for a chemical relative to a
        reference temperature (T_ref) and the heat of formation.

        Returns:
            float: Molar enthalpy in J/mol.
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            H_form = float(chem_data['Heat_of_Formation']) * 1000
            A = float(chem_data['Liq_Cp_A'])
            B = float(chem_data['Liq_Cp_B'])
            C = float(chem_data['Liq_Cp_C'])
            D = float(chem_data.get('Liq_Cp_D', 0.0))
            E = float(chem_data.get('Liq_Cp_E', 0.0))

            sensible_heat = (
                    A * (T - T_ref) +
                    (B / 2) * (T ** 2 - T_ref ** 2) +
                    (C / 3) * (T ** 3 - T_ref ** 3) +
                    (D / 4) * (T ** 4 - T_ref ** 4) +
                    (E / 5) * (T ** 5 - T_ref ** 5)
            )

            total_enthalpy = H_form + sensible_heat
            return total_enthalpy

        except (ValueError, KeyError) as e:
            return None

    def _calculate_vapor_pressure(self, chemical_name, temperature_K):
        """
        Calculates the vapor pressure (P_sat) for a chemical using an Antoine-like equation.

        Returns:
            float: Vapor pressure in Pascals.
        """
        chem_data = self._get_data(chemical_name)

        try:
            A = float(chem_data['Vap_P_A'])
            B = float(chem_data['Vap_P_B'])
            C = float(chem_data.get('Vap_P_C', 0.0))
            D = float(chem_data.get('Vap_P_D', 0.0))
            E = float(chem_data.get('Vap_P_E', 1.0))

            log_P_sat = A + B / temperature_K + C * math.log(temperature_K) + D * (temperature_K ** E)
            P_sat_Pa = math.exp(log_P_sat)
            return P_sat_Pa

        except (ValueError, KeyError) as e:
            raise ValueError(f"Error calculating vapor pressure for {chemical_name}: {e}")

    def _calculate_liquid_density(self, chemical_name, temperature_K):
        """
        Calculates the liquid density (rho) for a chemical using a polynomial.
        Formula: rho = A + B*T + C*T^2 + D*T^3

        Returns:
            float: Liquid density in kg/m^3.
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Lq_Den_A'])
            B = float(chem_data['Lq_Den_B'])
            C = float(chem_data.get('Lq_Den_C', 0.0))
            D = float(chem_data.get('Lq_Den_D', 0.0))

            density = A + B * T + C * (T ** 2) + D * (T ** 3)
            return density
        except (ValueError, KeyError) as e:
            return None

    def _calculate_vapor_density(self, chemical_name):
        """
        Calculates the vapor density (rho) for a chemical using ideal gas law.
        Formula: rho = P*MW/(R*T)

        Returns:
            float: Vapor density in kg/m^3.
        """
        chem_data = self._get_data(chemical_name)
        T = self.temperature_K
        P = self.pressure_Pa

        try:
            mol_wt = float(chem_data['Mol_wt'])
            density = (P * (mol_wt / 1000)) / (self.R * T)
            return density
        except (ValueError, KeyError) as e:
            return None

    def _calculate_liquid_cp(self, chemical_name, temperature_K):
        """
        Calculates the liquid molar heat capacity (Cp) for a chemical using a polynomial.

        Returns:
            float: Liquid molar heat capacity in J/(mol*K).
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Liq_Cp_A'])
            B = float(chem_data['Liq_Cp_B'])
            C = float(chem_data['Liq_Cp_C'])
            D = float(chem_data.get('Liq_Cp_D', 0.0))
            E = float(chem_data.get('Liq_Cp_E', 0.0))

            cp = A + B * T + C * (T ** 2) + D * (T ** 3) + E * (T ** 4)
            return cp
        except (ValueError, KeyError) as e:
            return None

    def _calculate_molar_heat_of_vaporization(self, chemical_name, temperature_K):
        """
        Calculates the molar heat of vaporization (H_vap) for a chemical using a polynomial.

        Returns:
            float: Molar heat of vaporization in J/mol.
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Heat_of_vap_A'])
            B = float(chem_data['Heat_of_vap_B'])
            C = float(chem_data.get('Heat_of_vap_C', 0.0))
            D = float(chem_data.get('Heat_of_vap_D', 0.0))
            E = float(chem_data.get('Heat_of_vap_E', 0.0))

            h_vap = A + B * T + C * (T ** 2) + D * (T ** 3) + E * (T ** 4)
            return h_vap
        except (ValueError, KeyError) as e:
            return None

    def _calculate_liquid_thermal_conductivity(self, chemical_name, temperature_K):
        """
        Calculates the liquid thermal conductivity (k) for a chemical using a polynomial.
        Formula: k = A + B*T + C*T^2 + D*T^3 + E*T^4

        Returns:
            float: Thermal conductivity in W/(m*K).
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Liq_Therm_con_A'])
            B = float(chem_data['Liq_Therm_con_B'])
            C = float(chem_data['Liq_Therm_con_C'])
            D = float(chem_data.get('Liq_Therm_con_D', 0.0))
            E = float(chem_data.get('Liq_Therm_con_E', 0.0))

            k_liq = A + B * T + C * (T ** 2) + D * (T ** 3) + E * (T ** 4)
            return k_liq
        except (ValueError, KeyError) as e:
            return None

    def _calculate_vapor_thermal_conductivity(self, chemical_name, temperature_K):
        """
        Calculates the vapor thermal conductivity (k) for a chemical using a polynomial.
        Formula: k = A + B*T + C*T^2 + D*T^3

        Returns:
            float: Thermal conductivity in W/(m*K).
        """
        chem_data = self._get_data(chemical_name)
        T = temperature_K

        try:
            A = float(chem_data['Vap_Therm_con_A'])
            B = float(chem_data['Vap_Therm_con_B'])
            C = float(chem_data['Vap_Therm_con_C'])
            D = float(chem_data.get('Vap_Therm_con_D', 0.0))

            k_vap = A + B * T + C * (T ** 2) + D * (T ** 3)
            return k_vap
        except (ValueError, KeyError) as e:
            return None

    # --- Mixture Property Calculation Methods ---

    def _calculate_mixture_molar_weight(self, mole_fractions):
        """
        Calculates the mixture's molar weight based on a weighted average of components.

        Returns:
            float: The molar weight of the mixture in g/mol.
        """
        mixture_mw = 0.0
        for chem, x in mole_fractions.items():
            chem_data = self._get_data(chem)
            mw = float(chem_data['Mol_wt'])
            mixture_mw += x * mw
        return mixture_mw

    def _calculate_mixture_liquid_cp(self, mole_fractions):
        """
        Calculates the mixture's liquid heat capacity based on a weighted average.

        Returns:
            float: The mixture's liquid heat capacity in J/(mol*K).
        """
        mixture_cp = 0.0
        for chem, x in mole_fractions.items():
            individual_cp = self._calculate_liquid_cp(chem, self.temperature_K)
            if individual_cp is not None:
                mixture_cp += x * individual_cp
        return mixture_cp

    def _calculate_mixture_gas_cp(self, mole_fractions):
        """
        Calculates the mixture's ideal gas heat capacity based on a weighted average.

        Returns:
            float: The mixture's ideal gas heat capacity in J/(mol*K).
        """
        mixture_cp = 0.0
        for chem, x in mole_fractions.items():
            individual_cp = self._calculate_ideal_gas_cp(chem, self.temperature_K)
            if individual_cp is not None:
                mixture_cp += x * individual_cp
        return mixture_cp

    def _calculate_mixture_liquid_enthalpy(self, mole_fractions):
        """
        Calculates the mixture's total liquid enthalpy based on a weighted average.

        Returns:
            float: The total enthalpy of the liquid mixture in J/mol.
        """
        mixture_h = 0.0
        for chem, x in mole_fractions.items():
            individual_h = self._calculate_liquid_enthalpy(chem, self.temperature_K)
            if individual_h is not None:
                mixture_h += x * individual_h
        return mixture_h

    def _calculate_mixture_gas_enthalpy(self, mole_fractions):
        """
        Calculates the mixture's total gas enthalpy based on a weighted average.

        Returns:
            float: The total enthalpy of the gas mixture in J/mol.
        """
        mixture_h = 0.0
        for chem, x in mole_fractions.items():
            individual_h = self._calculate_ideal_enthalpy(chem, self.temperature_K)
            if individual_h is not None:
                mixture_h += x * individual_h
        return mixture_h

    def _calculate_mixture_heat_of_vaporization(self, mole_fractions):
        """
        Calculates the mixture's molar heat of vaporization based on a weighted average.

        Returns:
            float: The mixture's heat of vaporization in J/mol.
        """
        mixture_h_vap = 0.0
        for chem, x in mole_fractions.items():
            individual_h_vap = self._calculate_molar_heat_of_vaporization(chem, self.temperature_K)
            if individual_h_vap is not None:
                mixture_h_vap += x * individual_h_vap
        return mixture_h_vap

    def _calculate_mixture_liquid_density(self, mole_fractions):
        """
        Calculates the mixture's liquid density based on a weighted average of volumes.

        Returns:
            float: The mixture's liquid density in kg/m^3.
        """
        total_molar_volume = 0.0
        mixture_mol_wt = self._calculate_mixture_molar_weight(mole_fractions)
        for chem, x in mole_fractions.items():
            individual_density = self._calculate_liquid_density(chem, self.temperature_K)
            if individual_density is not None and individual_density > 0:
                individual_molar_volume = (float(self._get_data(chem)['Mol_wt']) / 1000) / individual_density
                total_molar_volume += x * individual_molar_volume

        if total_molar_volume > 0:
            return (mixture_mol_wt / 1000) / total_molar_volume
        return None

    def _calculate_mixture_liquid_thermal_conductivity(self, mole_fractions):
        """
        Calculates the mixture's liquid thermal conductivity based on a weighted average.

        Returns:
            float: The mixture's liquid thermal conductivity in W/(m*K).
        """
        mixture_k = 0.0
        for chem, x in mole_fractions.items():
            individual_k = self._calculate_liquid_thermal_conductivity(chem, self.temperature_K)
            if individual_k is not None:
                mixture_k += x * individual_k
        return mixture_k

    def _calculate_mixture_vapor_thermal_conductivity(self, mole_fractions):
        """
        Calculates the mixture's vapor thermal conductivity based on a weighted average.

        Returns:
            float: The mixture's vapor thermal conductivity in W/(m*K).
        """
        mixture_k = 0.0
        for chem, x in mole_fractions.items():
            individual_k = self._calculate_vapor_thermal_conductivity(chem, self.temperature_K)
            if individual_k is not None:
                mixture_k += x * individual_k
        return mixture_k

    def calculate_ideal_molar_volume(self):
        """
        Calculates the ideal gas molar volume using the ideal gas law (V = RT/P).

        Returns:
            float: Molar volume in m^3/mol.
        """
        if self.pressure_Pa == 0:
            raise ValueError("Pressure cannot be zero for ideal gas law calculation.")
        return (self.R * self.temperature_K) / self.pressure_Pa

    def _calculate_bubble_point_temp(self):
        """
        Calculates the bubble point temperature using Raoult's Law and a bisection method.

        Returns:
            float: The bubble point temperature in Kelvin.
        """

        def bubble_point_function(T):
            sum_partial_pressures = 0
            for chem, x in self.mole_fractions.items():
                if x > 0:
                    P_sat = self._calculate_vapor_pressure(chem, T)
                    sum_partial_pressures += x * P_sat
            return self.pressure_Pa - sum_partial_pressures

        T_low = 100.0
        T_high = 1000.0
        tolerance = 1e-6
        max_iterations = 100

        for i in range(max_iterations):
            T_mid = (T_low + T_high) / 2
            f_mid = bubble_point_function(T_mid)

            if abs(f_mid) < tolerance:
                return T_mid

            f_low = bubble_point_function(T_low)
            if f_low * f_mid < 0:
                T_high = T_mid
            else:
                T_low = T_mid

        raise RuntimeError("Bisection method failed to converge for bubble point.")

    def _calculate_dew_point_temp(self):
        """
        Calculates the dew point temperature using Raoult's Law and a bisection method.

        Returns:
            float: The dew point temperature in Kelvin.
        """

        def dew_point_function(T):
            sum_of_inverse_pressures = 0
            for chem, y in self.mole_fractions.items():
                if y > 0:
                    P_sat = self._calculate_vapor_pressure(chem, T)
                    sum_of_inverse_pressures += y / P_sat
            return (1 / self.pressure_Pa) - sum_of_inverse_pressures

        T_low = 100.0
        T_high = 1000.0
        tolerance = 1e-6
        max_iterations = 100

        for i in range(max_iterations):
            T_mid = (T_low + T_high) / 2
            f_mid = dew_point_function(T_mid)

            if abs(f_mid) < tolerance:
                return T_mid

            f_low = dew_point_function(T_low)
            if f_low * f_mid < 0:
                T_high = T_mid
            else:
                T_low = T_mid

        raise RuntimeError("Bisection method failed to converge for dew point.")

    def _determine_phase(self):
        """
        Determines the phase of the mixture based on T, P, and composition.

        Returns:
            str: 'liquid', 'vapor', or 'two-phase'.
        """
        try:
            T_bubble = self._calculate_bubble_point_temp()
            T_dew = self._calculate_dew_point_temp()
        except Exception as e:
            print(f"Error in phase determination: {e}")
            return "Error"

        if self.temperature_K <= T_bubble:
            return 'liquid'
        elif self.temperature_K >= T_dew:
            return 'vapor'
        else:
            return 'two-phase'

    def _calculate_vapor_fraction(self):
        """
        Performs a simple flash calculation to determine the vapor fraction (beta)
        using the Rachford-Rice equation.

        Returns:
            float: The vapor fraction (beta) of the total flow.
        """

        def rachford_rice(beta, K_values, z):
            return sum([z[i] * (K_values[i] - 1) / (1 + beta * (K_values[i] - 1)) for i in range(len(K_values))])

        z = list(self.mole_fractions.values())
        K_values = [self._calculate_vapor_pressure(chem, self.temperature_K) / self.pressure_Pa for chem in
                    self.chemicals]

        # Bisection method to solve for beta
        beta_low = 0.0
        beta_high = 1.0
        tolerance = 1e-6

        for _ in range(100):
            beta_mid = (beta_low + beta_high) / 2
            if beta_mid == 0 or beta_mid == 1:
                return beta_mid

            f_mid = rachford_rice(beta_mid, K_values, z)

            if abs(f_mid) < tolerance:
                return beta_mid

            f_low = rachford_rice(beta_low, K_values, z)
            if f_low * f_mid < 0:
                beta_high = beta_mid
            else:
                beta_low = beta_mid

        return beta_mid

    def _calculate_phase_compositions(self):
        """
        Calculates the mole fractions of the liquid and vapor phases in a two-phase mixture.

        Returns:
            tuple: A tuple containing two dictionaries, (liquid_mole_fractions, vapor_mole_fractions).
        """
        if self.phase != 'two-phase' or self.vapor_fraction is None:
            return {}, {}

        liquid_mole_fractions = {}
        vapor_mole_fractions = {}

        K_values = {chem: self._calculate_vapor_pressure(chem, self.temperature_K) / self.pressure_Pa for chem in
                    self.chemicals}

        for chem in self.chemicals:
            z_i = self.mole_fractions[chem]
            K_i = K_values[chem]
            beta = self.vapor_fraction

            # Rachford-Rice derived equations for phase compositions
            x_i = z_i / (1 + beta * (K_i - 1))
            y_i = z_i * K_i / (1 + beta * (K_i - 1))

            liquid_mole_fractions[chem] = x_i
            vapor_mole_fractions[chem] = y_i

        # Normalize the mole fractions to ensure they sum to 1
        sum_x = sum(liquid_mole_fractions.values())
        sum_y = sum(vapor_mole_fractions.values())

        liquid_mole_fractions = {k: v / sum_x for k, v in liquid_mole_fractions.items()}
        vapor_mole_fractions = {k: v / sum_y for k, v in vapor_mole_fractions.items()}

        return liquid_mole_fractions, vapor_mole_fractions

    def calculate_all_mixture_properties(self):
        """
        Calculates all combined properties for the mixture based on its determined phase.

        Returns:
            dict: A dictionary of calculated mixture properties.
        """
        # Overall stream properties (independent of phase)

        self.properties = {
            'Name':self.stream_name,
            'Temperature (K)': self.temperature_K,
            'Pressure (Pa)': self.pressure_Pa,
            'Molar Flowrate (mol/s)': self.molar_flowrate_mol_s,
            'Mixture Molar Weight (g/mol)': self._calculate_mixture_molar_weight(self.mole_fractions)
        }

        # Determine the phase
        self.phase = self._determine_phase()
        self.properties['Phase'] = self.phase

        if self.phase == 'liquid':
            self.molar_cp=self._calculate_mixture_liquid_cp(self.mole_fractions)
            self.molar_enthalpy=self._calculate_mixture_liquid_enthalpy(self.mole_fractions)
            self.total_enthalpy=self.molar_flowrate_mol_s * self.molar_enthalpy
            self.density=self._calculate_mixture_liquid_density(self.mole_fractions)
            self.thermal_cond=self._calculate_mixture_liquid_thermal_conductivity(self.mole_fractions)
            self.heat_of_vap=self._calculate_mixture_heat_of_vaporization(self.mole_fractions)


            self.properties['Mixture Molar Cp (J/mol.K)'] = self.molar_cp
            self.properties['Mixture Molar Enthalpy (J/mol)'] = self.molar_enthalpy
            self.properties['Total Enthalpy Flow (W)'] = self.total_enthalpy
            self.properties['Mixture Density (kg/m^3)'] = self.density
            self.properties['Mixture Thermal Conductivity (W/m.K)'] = self.thermal_cond
            self.properties['Mixture Molar Heat of Vaporization (J/mol)'] = self.heat_of_vap


        elif self.phase == 'vapor':
            self.molar_cp = self._calculate_mixture_gas_cp(self.mole_fractions)
            self.molar_enthalpy = self._calculate_mixture_gas_enthalpy(self.mole_fractions)
            self.total_enthalpy = self.molar_flowrate_mol_s * self.molar_enthalpy
            self.density = self._calculate_vapor_density(self.mole_fractions)
            self.thermal_cond = self._calculate_mixture_vapor_thermal_conductivity(self.mole_fractions)
            self.heat_of_vap = self._calculate_mixture_heat_of_vaporization(self.mole_fractions)


            self.properties['Mixture Molar Cp (J/mol.K)'] = self.molar_cp
            self.properties['Mixture Molar Enthalpy (J/mol)'] = self.molar_enthalpy
            self.properties['Total Enthalpy Flow (W)'] = self.total_enthalpy
            self.properties['Vapor Density']=self.density
            self.properties['Mixture Thermal Conductivity (W/m.K)'] = self.thermal_cond
            self.properties['Mixture Molar Heat of Vaporization (J/mol)'] = self.heat_of_vap


        elif self.phase == 'two-phase':
            self.vapor_fraction = self._calculate_vapor_fraction()
            self.properties['Vapor Fraction'] = self.vapor_fraction

            # Calculate phase-specific compositions
            self.liquid_mole_fractions, self.vapor_mole_fractions = self._calculate_phase_compositions()

            # Liquid Phase Properties
            liq_enthalpy = self._calculate_mixture_liquid_enthalpy(self.liquid_mole_fractions)
            liq_cp = self._calculate_mixture_liquid_cp(self.liquid_mole_fractions)
            liq_density = self._calculate_mixture_liquid_density(self.liquid_mole_fractions)
            liq_thermal_k = self._calculate_mixture_liquid_thermal_conductivity(self.liquid_mole_fractions)

            # Vapor Phase Properties
            vap_enthalpy = self._calculate_mixture_gas_enthalpy(self.vapor_mole_fractions)
            vap_cp = self._calculate_mixture_gas_cp(self.vapor_mole_fractions)
            vap_thermal_k = self._calculate_mixture_vapor_thermal_conductivity(self.vapor_mole_fractions)

            # Combined Stream Properties (weighted by vapor fraction)



            self.molar_cp = (1 - self.vapor_fraction) * liq_cp + self.vapor_fraction * vap_cp
            self.molar_enthalpy =(1 - self.vapor_fraction) * liq_enthalpy + self.vapor_fraction * vap_enthalpy
            self.total_enthalpy = self.molar_flowrate_mol_s *self.molar_enthalpy
            # self.density = self._calculate_vapor_density(self.mole_fractions)
            self.thermal_cond =(1 - self.vapor_fraction) *liq_thermal_k + self.vapor_fraction * vap_thermal_k   #self._calculate_mixture_vapor_thermal_conductivity(self.mole_fractions)
            self.heat_of_vap = self._calculate_mixture_heat_of_vaporization(self.mole_fractions)

            self.properties['Mixture Molar Cp (J/mol.K)'] =self.molar_cp
            self.properties['Mixture Molar Enthalpy (J/mol)'] =self.molar_enthalpy
            self.properties['Total Enthalpy Flow (W)'] =self.total_enthalpy
            self.properties['Mixture Molar Heat of Vaporization (J/mol)'] =self.heat_of_vap



            # Add phase-specific compositions and self.properties to the output dictionary
            self.properties['Liquid Phase Mole Fractions'] = self.liquid_mole_fractions
            self.properties['Liquid Phase Molar Cp (J/mol.K)'] = liq_cp
            self.properties['Liquid Phase Molar Enthalpy (J/mol)'] = liq_enthalpy
            self.properties['Liquid Phase Density (kg/m^3)'] = liq_density
            self.properties['Liquid Phase Thermal Conductivity (W/m.K)'] = liq_thermal_k
            self.properties['Vapor Phase Mole Fractions'] = self.vapor_mole_fractions
            self.properties['Vapor Phase Molar Cp (J/mol.K)'] = vap_cp
            self.properties['Vapor Phase Molar Enthalpy (J/mol)'] = vap_enthalpy
            self.properties['Vapor Phase Thermal Conductivity (W/m.K)'] = vap_thermal_k

        # return properties

    def stream_result(self):
        print(self.properties)
#
# # --- Example Usage ---
# if __name__ == "__main__":
#     # Define the stream conditions and components with mole fractions
#     # This temperature should result in a two-phase mixture
#     chemicals_in_stream = {'Water': 0.8, 'Methane': 0.2}
#     temperature = 200.0  # K
#     pressure = 101325.0  # Pa (1 atm)
#     molar_flowrate = 10.0  # mol/s
#
#     # Create an instance of the property package
#     stream_package = PropertyPackage('Two-Phase Stream', chemicals_in_stream, temperature, pressure, molar_flowrate)
#
#     # Calculate all combined properties for the mixture
#     mixture_properties = stream_package.calculate_all_mixture_properties()
#
#     # Print the results
#     print("--- Combined Mixture Properties Calculation ---")
#     for key, value in mixture_properties.items():
#         if isinstance(value, float):
#             print(f"  {key}: {value:.4f}")
#         elif isinstance(value, dict):
#             print(f"  {key}:")
#             for sub_key, sub_value in value.items():
#                 print(f"    - {sub_key}: {sub_value:.4f}")
#         else:
#             print(f"  {key}: {value}")
#
#     print("\n-------------------------------------")

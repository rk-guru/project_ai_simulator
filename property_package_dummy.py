# from typing import TypedDict ,List ,Union
# from langchain_core.messages import HumanMessage ,AIMessage
# from langchain.chat_models import init_chat_model
# from langgraph.graph import StateGraph ,START ,END
# from dotenv import load_dotenv
# from typing import Annotated , Sequence ,TypedDict
# from langchain_core.messages import BaseMessage ,ToolMessage ,SystemMessage
# from langgraph.graph.message import add_messages
# from langgraph.graph import StateGraph  ,END ,START
# from langgraph.prebuilt import ToolNode
# from langchain.chat_models import init_chat_model
# import os
# import pandas as pd
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_community.embeddings import OllamaEmbeddings
# from langchain_community.llms import Ollama
# from langchain_chroma import Chroma
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from langchain_text_splitters import RecursiveCharacterTextSplitter
#
# import csv
# import io
# import math
# import pandas as pd
#
#
# class PropertyPackage:
#     """
#     A class to calculate a wide range of properties for a stream of chemicals.
#
#     This class loads chemical data from a database and provides methods to
#     calculate individual and mixture properties for a given stream at a
#     specific temperature and pressure, including phase determination.
#     """
#
#     # R: Ideal Gas Constant in J/(mol*K)
#     R = 8.314
#
#     def __init__(self, stream_name, chemicals_with_fractions, temperature_K, pressure_Pa, molar_flowrate_mol_s):
#         """
#         Initializes the property package with a dictionary of chemicals, T, P, and flow rate.
#
#         Args:
#             chemicals_with_fractions (dict): A dictionary of chemical names and their
#                                              mole fractions (e.g., {'Methane': 0.8, 'Water': 0.2}).
#             temperature_K (float): The stream temperature in Kelvin.
#             pressure_Pa (float): The stream pressure in Pascals.
#             molar_flowrate_mol_s (float): The total molar flow rate of the stream in mol/s.
#         """
#         # Store the chemical names and mole fractions
#         self.stream_name = stream_name
#         self.chemicals = list(chemicals_with_fractions.keys())
#         total_sum=sum(chemicals_with_fractions.values())
#
#         self.mole_fractions = {key: value / total_sum for key, value in chemicals_with_fractions.items()}
#         self.temperature_K = temperature_K
#         self.pressure_Pa = pressure_Pa
#         self.molar_flowrate_mol_s = molar_flowrate_mol_s
#
#         # Initialize phase-specific properties to None
#         self.phase = None
#         self.vapor_fraction = None
#         self.liquid_mole_fractions = None
#         self.vapor_mole_fractions = None
#         self.properties=None
#
#
#
#     def calculate_all_mixture_properties(self):
#         """
#         Calculates all combined properties for the mixture based on its determined phase.
#
#         Returns:
#             dict: A dictionary of calculated mixture properties.
#         """
#         # Overall stream properties (independent of phase)
#
#         self.properties = {
#             'Name':self.stream_name,
#             'Temperature (K)': self.temperature_K,
#             'Pressure (Pa)': self.pressure_Pa,
#             'Molar Flowrate (mol/s)': self.molar_flowrate_mol_s,
#             'Mixture Molar Weight (g/mol)': self._calculate_mixture_molar_weight(self.mole_fractions)
#         }
#
#         # Determine the phase
#         self.phase = self._determine_phase()
#         self.properties['Phase'] = self.phase
#
#         if self.phase == 'liquid':
#             self.molar_cp=self._calculate_mixture_liquid_cp(self.mole_fractions)
#             self.molar_enthalpy=self._calculate_mixture_liquid_enthalpy(self.mole_fractions)
#             self.total_enthalpy=self.molar_flowrate_mol_s * self.molar_enthalpy
#             self.density=self._calculate_mixture_liquid_density(self.mole_fractions)
#             self.thermal_cond=self._calculate_mixture_liquid_thermal_conductivity(self.mole_fractions)
#             self.heat_of_vap=self._calculate_mixture_heat_of_vaporization(self.mole_fractions)
#
#
#             self.properties['Mixture Molar Cp (J/mol.K)'] = self.molar_cp
#             self.properties['Mixture Molar Enthalpy (J/mol)'] = self.molar_enthalpy
#             self.properties['Total Enthalpy Flow (W)'] = self.total_enthalpy
#             self.properties['Mixture Density (kg/m^3)'] = self.density
#             self.properties['Mixture Thermal Conductivity (W/m.K)'] = self.thermal_cond
#             self.properties['Mixture Molar Heat of Vaporization (J/mol)'] = self.heat_of_vap
#
#
#         elif self.phase == 'vapor':
#             self.molar_cp = self._calculate_mixture_gas_cp(self.mole_fractions)
#             self.molar_enthalpy = self._calculate_mixture_gas_enthalpy(self.mole_fractions)
#             self.total_enthalpy = self.molar_flowrate_mol_s * self.molar_enthalpy
#             self.density = self._calculate_vapor_density(self.mole_fractions)
#             self.thermal_cond = self._calculate_mixture_vapor_thermal_conductivity(self.mole_fractions)
#             self.heat_of_vap = self._calculate_mixture_heat_of_vaporization(self.mole_fractions)
#
#
#             self.properties['Mixture Molar Cp (J/mol.K)'] = self.molar_cp
#             self.properties['Mixture Molar Enthalpy (J/mol)'] = self.molar_enthalpy
#             self.properties['Total Enthalpy Flow (W)'] = self.total_enthalpy
#             self.properties['Vapor Density']=self.density
#             self.properties['Mixture Thermal Conductivity (W/m.K)'] = self.thermal_cond
#             self.properties['Mixture Molar Heat of Vaporization (J/mol)'] = self.heat_of_vap
#
#
#         elif self.phase == 'two-phase':
#             self.vapor_fraction = self._calculate_vapor_fraction()
#             self.properties['Vapor Fraction'] = self.vapor_fraction
#
#             # Calculate phase-specific compositions
#             self.liquid_mole_fractions, self.vapor_mole_fractions = self._calculate_phase_compositions()
#
#             # Liquid Phase Properties
#             liq_enthalpy = self._calculate_mixture_liquid_enthalpy(self.liquid_mole_fractions)
#             liq_cp = self._calculate_mixture_liquid_cp(self.liquid_mole_fractions)
#             liq_density = self._calculate_mixture_liquid_density(self.liquid_mole_fractions)
#             liq_thermal_k = self._calculate_mixture_liquid_thermal_conductivity(self.liquid_mole_fractions)
#
#             # Vapor Phase Properties
#             vap_enthalpy = self._calculate_mixture_gas_enthalpy(self.vapor_mole_fractions)
#             vap_cp = self._calculate_mixture_gas_cp(self.vapor_mole_fractions)
#             vap_thermal_k = self._calculate_mixture_vapor_thermal_conductivity(self.vapor_mole_fractions)
#
#             # Combined Stream Properties (weighted by vapor fraction)
#
#
#
#             self.molar_cp = (1 - self.vapor_fraction) * liq_cp + self.vapor_fraction * vap_cp
#             self.molar_enthalpy =(1 - self.vapor_fraction) * liq_enthalpy + self.vapor_fraction * vap_enthalpy
#             self.total_enthalpy = self.molar_flowrate_mol_s *self.molar_enthalpy
#             # self.density = self._calculate_vapor_density(self.mole_fractions)
#             self.thermal_cond =(1 - self.vapor_fraction) *liq_thermal_k + self.vapor_fraction * vap_thermal_k   #self._calculate_mixture_vapor_thermal_conductivity(self.mole_fractions)
#             self.heat_of_vap = self._calculate_mixture_heat_of_vaporization(self.mole_fractions)
#
#             self.properties['Mixture Molar Cp (J/mol.K)'] =self.molar_cp
#             self.properties['Mixture Molar Enthalpy (J/mol)'] =self.molar_enthalpy
#             self.properties['Total Enthalpy Flow (W)'] =self.total_enthalpy
#             self.properties['Mixture Molar Heat of Vaporization (J/mol)'] =self.heat_of_vap
#
#
#
#             # Add phase-specific compositions and self.properties to the output dictionary
#             self.properties['Liquid Phase Mole Fractions'] = self.liquid_mole_fractions
#             self.properties['Liquid Phase Molar Cp (J/mol.K)'] = liq_cp
#             self.properties['Liquid Phase Molar Enthalpy (J/mol)'] = liq_enthalpy
#             self.properties['Liquid Phase Density (kg/m^3)'] = liq_density
#             self.properties['Liquid Phase Thermal Conductivity (W/m.K)'] = liq_thermal_k
#             self.properties['Vapor Phase Mole Fractions'] = self.vapor_mole_fractions
#             self.properties['Vapor Phase Molar Cp (J/mol.K)'] = vap_cp
#             self.properties['Vapor Phase Molar Enthalpy (J/mol)'] = vap_enthalpy
#             self.properties['Vapor Phase Thermal Conductivity (W/m.K)'] = vap_thermal_k
#
#         # return properties
#
#     def stream_result(self):
#         print(self.properties)
# #
# # # --- Example Usage ---
# # if __name__ == "__main__":
# #     # Define the stream conditions and components with mole fractions
# #     # This temperature should result in a two-phase mixture
# #     chemicals_in_stream = {'Water': 0.8, 'Methane': 0.2}
# #     temperature = 200.0  # K
# #     pressure = 101325.0  # Pa (1 atm)
# #     molar_flowrate = 10.0  # mol/s
# #
# #     # Create an instance of the property package
# #     stream_package = PropertyPackage('Two-Phase Stream', chemicals_in_stream, temperature, pressure, molar_flowrate)
# #
# #     # Calculate all combined properties for the mixture
# #     mixture_properties = stream_package.calculate_all_mixture_properties()
# #
# #     # Print the results
# #     print("--- Combined Mixture Properties Calculation ---")
# #     for key, value in mixture_properties.items():
# #         if isinstance(value, float):
# #             print(f"  {key}: {value:.4f}")
# #         elif isinstance(value, dict):
# #             print(f"  {key}:")
# #             for sub_key, sub_value in value.items():
# #                 print(f"    - {sub_key}: {sub_value:.4f}")
# #         else:
# #             print(f"  {key}: {value}")
# #
# #     print("\n-------------------------------------")



import pandas as pd
import numpy as np

def create_prediction_dataframe(input_df, metrics_dict):
    """
    Creates a new DataFrame with an 'input' column and a 'predicted' column.

    The 'input' column is populated with the values from the 'smiles' column
    of the input DataFrame. The 'predicted' column is populated with random
    values between 0 and 1, simulating predictions.

    Args:
        input_df (pd.DataFrame): A DataFrame containing a column named 'smiles'.
        metrics_dict (dict): A dictionary (not used in this function but included
                             to match the prompt's signature).

    Returns:
        pd.DataFrame: A new DataFrame with 'smiles' and 'predicted' columns.
                      Returns an empty DataFrame if 'smiles' column is not found.
    """
    # Check if the 'smiles' column exists in the input DataFrame
    if 'smiles' not in input_df.columns:
        print("Error: The input DataFrame must contain a 'smiles' column.")
        return pd.DataFrame() # Return an empty DataFrame on error

    # Get the number of rows from the input DataFrame
    num_rows = len(input_df)

    # Create a new DataFrame with the same 'smiles' column
    output_df = pd.DataFrame()
    output_df['smiles'] = input_df['smiles']

    # Generate a column of random values between 0 and 1
    # The size of this column is the same as the number of rows in the input DataFrame
    output_df['predicted'] = np.random.rand(num_rows)

    return output_df

# --- Example Usage ---
if __name__ == "__main__":
    # Create a dummy input DataFrame with a 'smiles' column
    dummy_smiles_data = {
        'smiles': ['CCO', 'CCC', 'C(C(C(=O)O)O)O', 'O=C1NC(=O)C2(N1C(=O)CC2)C'],
    }
    dummy_df = pd.DataFrame(dummy_smiles_data)

    # Create a dummy dictionary (as specified in the prompt)
    dummy_dict = {
        "model_name": "SVM",
        "accuracy": 0.95
    }

    print("Original Input DataFrame:")
    print(dummy_df)
    print("-" * 30)

    # Call the function to create the new DataFrame
    predicted_df = create_prediction_dataframe(dummy_df, dummy_dict)

    if not predicted_df.empty:
        print("\nGenerated Output DataFrame:")
        print(predicted_df)
    else:
        print("DataFrame generation failed.")
# import pandas as pd
# import numpy as np
#
# class pred_result():
#     def __init__(self,csv_file_path):
#         self.csv_file_path=csv_file_path
#         self.pred_data=None
#         self.result=None
#         self.performance_metrics=None
#
#     def analyze_model_performance(self):
#         """
#         Simulates reading a CSV and returns model performance metrics,
#         dummy predicted values, and additional experimental details.
#
#         Args:
#             csv_file_path (str): The path to the dummy CSV file.
#             num_dummy_predictions (int): The number of dummy predicted values to generate for each model.
#
#         Returns:
#             dict: A dictionary containing model performance metrics,
#                   dummy predicted values, and additional information.
#         """
#         # In a real scenario, you would load and process the CSV here.
#         # For this dummy script, we'll directly use the values from the image.
#
#         # Model performance metrics from the provided image
#         self.performance_metrics = {
#             "SVM": {"R^2": 0.85, "MSE": 0.12, "MAE": 0.25, "Accuracy": 0.92},
#             "Random Forest": {"R^2": 0.91, "MSE": 0.08, "MAE": 0.21, "Accuracy": 0.95},
#             "XGBoost": {"R^2": 0.93, "MSE": 0.06, "MAE": 0.19, "Accuracy": 0.96},
#             "Neural Network": {"R^2": 0.88, "MSE": 0.10, "MAE": 0.23, "Accuracy": 0.94},
#             "K-Neighbors": {"R^2": 0.79, "MSE": 0.18, "MAE": 0.32, "Accuracy": 0.88}
#         }
#
#         # Dummy predicted values for each model
#         # Generate 'num_dummy_predictions' random values between 0 and 1
#         leng=len(self.csv_file_path)
#         self.pred_data = {}
#         for model_name in self.performance_metrics.keys():
#             self.pred_data[model_name] = np.round(np.random.rand(leng), 2).tolist()
#
#         # Additional experimental details
#
#         self.result = {
#             "Fingerprint Used": "Morgan",
#             "Normalization": "Min-Max",
#             "Descriptor Used": "RDKit 2D",
#             "Outlier Ranges": "3-Sigma"
#         }
#
#
#
#
# # --- How to use the dummy script ---
# if __name__ == "__main__":
#     # Create a dummy CSV file for demonstration purposes
#     dummy_data = {'feature1': [1, 2, 3, 4, 5],
#                   'feature2': [10, 20, 30, 40, 50],
#                   'target': [0, 1, 0, 1, 0]}
#     dummy_df = pd.DataFrame(dummy_data)
#     # dummy_csv_path = "dummy_input.csv"
#     # dummy_df.to_csv(dummy_csv_path, index=False)
#     # print(f"Dummy CSV file '{dummy_csv_path}' created for demonstration.\n")
#
#     # Call the function with the dummy CSV file path and specify the number of dummy predictions
#     # Let's say we want 10 dummy predictions for each model this time.
#     dataframe_input=pd.DataFrame()
#     prediction=pred_result(dataframe_input)
#     prediction.analyze_model_performance()
#     print(prediction.pred_data)
#     print(prediction.performance_metrics)
#     print(prediction.result)
#
#
#     # results = analyze_model_performance(dummy_df)
#
#     # print("--- Model Performance Metrics (from image) ---")
#     # for model, metrics in results["performance_metrics"].items():
#     #     print(f"Model: {model}")
#     #     for metric, value in metrics.items():
#     #         print(f"  {metric}: {value}")
#     #     print("-" * 30)
#     #
#     # print("\n--- Dummy Predicted Values ---")
#     # for model, predictions in results["dummy_predictions"].items():
#     #     print(f"Model: {model}")
#     #     print(f"  Number of dummy predictions: {len(predictions)}")  # Displaying the count
#     #     print(f"  Predictions: {predictions}")
#     #     print("-" * 30)
#     #
#     # print("\n--- Additional Experimental Information ---")
#     # for key, value in results["additional_info"].items():
#     #     print(f"{key}: {value}")
#     # print("-" * 30)
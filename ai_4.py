# import re
# import json
# import os
# import ast
# import uuid
# from typing import TypedDict, Sequence, Annotated, Union, List, Dict
# from pydantic import BaseModel, Field
# from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
# from langchain_core.tools import tool
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.runnables import RunnablePassthrough
# from langchain_core.output_parsers import StrOutputParser
# from operator import itemgetter
# from langgraph.graph import StateGraph, END, START
# from langgraph.prebuilt import ToolNode
#
# # NOTE: API_KEY is a placeholder and should be securely handled in a real application.
# API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
#
# # Define constants for RAG
# PDF_PATH = 'The styrene production2.pdf'
# gemini_model = "gemini-2.5-flash-lite"
#
# # Initialize Google Generative AI components
# embeddings = GoogleGenerativeAIEmbeddings(
#     model="models/gemini-embedding-001",
#     google_api_key=API_KEY
# )
# llm = ChatGoogleGenerativeAI(
#     model=gemini_model,
#     google_api_key=API_KEY,
#     temperature=0.7,
#     max_tokens=None,
#     timeout=None,
#     max_retries=2, )
#
#
# # --- State Management ---
# def add_messages(left: list, right: list):
#     """Function to add messages for state management"""
#     return left + right
#
#
# class AgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], add_messages]
#
#
# def clean_string(input_string):
#     """
#     Removes '```json', '\n', and '```' from a string and strips whitespace.
#     """
#     cleaned_string = input_string.replace('```json', '')
#     cleaned_string = cleaned_string.replace('\n', '')
#     cleaned_string = cleaned_string.replace('```', '')
#     return cleaned_string.strip()
#
#
# def setup_rag_chain(pdf_path: str):
#     """
#     Sets up a RAG chain by loading a PDF, creating a ChromaDB vector store,
#     and initializing the LangChain components.
#     """
#     db_name = os.path.splitext(os.path.basename(pdf_path))[0]
#     persist_directory = f"./{db_name}_rag_db"
#
#     if not os.path.exists(pdf_path):
#         print(f"Error: The PDF file '{pdf_path}' was not found.")
#         return None
#
#     if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
#         print(f"Creating a new RAG vector store for '{db_name}'...")
#         try:
#             loader = PyPDFLoader(pdf_path)
#             docs = loader.load()
#             text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
#             splits = text_splitter.split_documents(docs)
#
#             vector_store = Chroma.from_documents(
#                 documents=splits,
#                 embedding=embeddings,
#                 persist_directory=persist_directory
#             )
#             print(f"Vector store created at '{persist_directory}'.")
#         except Exception as e:
#             print(f"Error creating vector store: {e}")
#             return None
#     else:
#         print(f"Loading existing RAG vector store for '{db_name}' from '{persist_directory}'.")
#         vector_store = Chroma(
#             persist_directory=persist_directory,
#             embedding_function=embeddings
#         )
#
#     retriever = vector_store.as_retriever(search_kwargs={"k": 3})
#
#     prompt = ChatPromptTemplate.from_template("""
#     You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
#     If you don't know the answer, just say that you don't know.
#
#     Question: {question}
#     Context: {context}
#     Answer:
#     """)
#
#     def format_docs(docs):
#         return "\n\n".join(doc.page_content for doc in docs)
#
#     rag_chain = (
#             {"context": retriever | format_docs, "question": RunnablePassthrough()}
#             | prompt
#             | llm
#             | StrOutputParser()
#     )
#
#     return rag_chain
#
#
# # Initialize the RAG chain globally
# RAG_CHAIN = setup_rag_chain(PDF_PATH)
#
#
# # --- Helper Functions for Simulation (Acting as internal "tools" for the simulation tool) ---
# def stream(name: str, temperature: float, pressure: float, chemical_fraction: dict, flow: float):
#     """Helper function to define the stream."""
#     # Simplified calculation for total moles
#     total_moles_dict = {
#         chem: flow * frac for chem, frac in chemical_fraction.items()
#     }
#
#     stream_dict = {
#         'Name': name,
#         'Temperature (C)': temperature,
#         'Pressure (bar)': pressure,
#         'Molar Flowrate (mol/s)': flow,
#         'Mole Fraction': chemical_fraction,
#         'Total Moles (mol/s)': total_moles_dict,  # Added for reactor consistency
#     }
#     return stream_dict
#
#
# def get_inlet_stream_tool(feed_condition: str, feed_composition: str) -> dict:
#     """Creates the initial feed stream dictionary based on LLM-extracted data."""
#     # Safety parsing
#     try:
#         feed_condition_list = ast.literal_eval(feed_condition)
#         feed_composition_dict = json.loads(feed_composition)
#     except Exception as e:
#         print(f"Error parsing feed data: {e}")
#         # Default to a safe stream if parsing fails
#         return stream('Feed', 25.0, 1.0, {'Benzene': 0.5, 'Ethylene': 0.5}, 100.0)
#
#     feed_temp = feed_condition_list[0]
#     feed_pressure = feed_condition_list[1]
#     inlet_flowrate = feed_condition_list[2]
#
#     list_of_chemicals = list(feed_composition_dict.keys())
#     mole_flow_dict = {}
#
#     for i in list_of_chemicals:
#         val = feed_composition_dict[i]["value"]
#         # Use Mole Fraction with total flowrate to get Mole Flowrate
#         if feed_composition_dict[i]["type"] == 'Mole_Fraction':
#             mole_flow_dict[i] = val * inlet_flowrate
#         else:  # Mole_Flow
#             mole_flow_dict[i] = val
#
#     current_total_flow = sum(mole_flow_dict.values())
#     if current_total_flow == 0:
#         current_total_flow = inlet_flowrate  # Fallback
#
#     mole_frac_dict = {}
#     for i in list_of_chemicals:
#         mole_frac_dict[i] = mole_flow_dict[i] / current_total_flow if current_total_flow > 0 else 0.0
#
#     return stream(
#         name='Feed',
#         temperature=feed_temp,
#         pressure=feed_pressure,
#         chemical_fraction=mole_frac_dict,
#         flow=current_total_flow
#     )
#
#
# @tool
# def heater_tool(inlet_stream: dict, outlet_temp_C: float, name: str) -> dict:
#     """A tool for a heating unit where the temperature of the inlet stream is increased.
#     Args:
#         inlet_stream: The stream dictionary to be heated.
#         outlet_temp_C: The desired outlet temperature in C.
#         name: The name of the outlet stream.
#     Returns:
#         The updated stream dictionary.
#     """
#     outlet_stream = inlet_stream.copy()
#     outlet_stream['Name'] = name
#     outlet_stream['Temperature (C)'] = outlet_temp_C
#     return outlet_stream
#
#
# @tool
# def pump_tool(inlet_stream: dict, outlet_pressure_bar: float, name: str) -> dict:
#     """A tool for a pumping unit where the pressure of the inlet stream is increased.
#     Args:
#         inlet_stream: The stream dictionary to be pumped.
#         outlet_pressure_bar: The desired outlet pressure in bar.
#         name: The name of the outlet stream.
#     Returns:
#         The updated stream dictionary.
#     """
#     outlet_stream = inlet_stream.copy()
#     outlet_stream['Name'] = name
#     outlet_stream['Pressure (bar)'] = outlet_pressure_bar
#     return outlet_stream
#
#
# @tool
# def reactor_tool(inlet_stream: dict, conversion: float, name: str) -> dict:
#     """A tool for a conversion reactor. Reaction: Benzene + Ethylene -> Ethyl Benzene
#     Args:
#         inlet_stream: The reactor inlet stream dictionary.
#         conversion: The conversion percentage of the reaction based on Benzene.
#         name: The name of the outlet stream.
#     Returns:
#         The updated stream dictionary.
#     """
#     outlet_stream = inlet_stream.copy()
#     # Use the consistent key 'Total Moles (mol/s)'
#     inlet_moles = inlet_stream.get('Total Moles (mol/s)', {})
#
#     # Ensure all required reaction species are present, defaulting to 0.0 if not.
#     benzene_in = inlet_moles.get('Benzene', 0.0)
#     ethylene_in = inlet_moles.get('Ethylene', 0.0)
#     ethylbenzene_in = inlet_moles.get('Ethyl Benzene', 0.0)
#
#     # Calculate reaction based on Benzene conversion (max extent)
#     moles_benzene_reacted_target = benzene_in * (conversion / 100.0)
#
#     # Stoichiometry is 1:1, reaction is limited by the minimum reactant available
#     moles_to_react = min(moles_benzene_reacted_target, ethylene_in, benzene_in)
#
#     if moles_to_react < 0:
#         moles_to_react = 0.0
#
#     # Calculate outlet moles
#     benzene_out = benzene_in - moles_to_react
#     ethylene_out = ethylene_in - moles_to_react
#     ethylbenzene_out = ethylbenzene_in + moles_to_react
#
#     # Copy and update moles for all species
#     new_moles = inlet_moles.copy()
#     new_moles['Benzene'] = benzene_out
#     new_moles['Ethylene'] = ethylene_out
#     # Only add Ethyl Benzene if it was present or if reaction occurred
#     if ethylbenzene_out > 0 or 'Ethyl Benzene' in inlet_moles:
#         new_moles['Ethyl Benzene'] = ethylbenzene_out
#
#     total_flow_out = sum(new_moles.values())
#
#     outlet_stream['Total Moles (mol/s)'] = new_moles
#     outlet_stream['Molar Flowrate (mol/s)'] = total_flow_out
#     outlet_stream['Mole Fraction'] = {
#         chem: moles / total_flow_out for chem, moles in new_moles.items() if total_flow_out > 0
#     }
#     outlet_stream['Name'] = name
#     return outlet_stream
#
#
# @tool
# def cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str) -> dict:
#     """A tool for a cooling unit.
#     Args:
#         inlet_stream: The stream dictionary to be cooled.
#         outlet_temp_C: The desired outlet temperature in C.
#         name: The name of the outlet stream.
#     Returns:
#         The updated stream dictionary.
#     """
#     outlet_stream = inlet_stream.copy()
#     outlet_stream['Name'] = name
#     outlet_stream['Temperature (C)'] = outlet_temp_C
#     return outlet_stream
#
#
# @tool
# def flash_tool(inlet_stream: dict, name: str) -> list[dict]:
#     """A tool for a stream separator that splits a stream into liquid and vapor.
#     This is a simplified model that performs a 50/50 split.
#     Args:
#         inlet_stream: The stream dictionary to be split.
#         name: The base name of the outlet stream.
#     Returns:
#         A list containing the vapor and liquid stream dictionaries.
#     """
#     outlet_stream1 = inlet_stream.copy()
#     outlet_stream2 = inlet_stream.copy()
#
#     flow_split = 0.5
#
#     outlet_stream1['Molar Flowrate (mol/s)'] *= flow_split
#     outlet_stream2['Molar Flowrate (mol/s)'] *= flow_split
#
#     if 'Total Moles (mol/s)' in inlet_stream:
#         outlet_stream1['Total Moles (mol/s)'] = {k: v * flow_split for k, v in
#                                                  inlet_stream['Total Moles (mol/s)'].items()}
#         outlet_stream2['Total Moles (mol/s)'] = {k: v * flow_split for k, v in
#                                                  inlet_stream['Total Moles (mol/s)'].items()}
#
#     outlet_stream1['Name'] = f'{name}_Vapor'
#     outlet_stream2['Name'] = f'{name}_Liquid'
#
#     return [outlet_stream1, outlet_stream2]
#
#
# # --- Top-Level Tools (for the Main Agent) ---
# @tool
# def rag_enquiry(content: str) -> str:
#     """This tool is for answering questions about the styrene production process as described in the paper.
#     It retrieves information from the loaded document."""
#     if RAG_CHAIN:
#         return RAG_CHAIN.invoke(content)
#     return "Error: RAG chain is not configured. Please check the PDF file path."
#
#
# def get_tool_from_name(tool_name: str):
#     """Maps a tool name (e.g., Heater_1) to its corresponding tool function."""
#     tool_map = {
#         'Heater': heater_tool,
#         'Pump': pump_tool,
#         'Reactor': reactor_tool,
#         'Cooler': cooler_tool,
#         'Flash': flash_tool,
#         'Distillation': flash_tool,  # Use Flash for a simple split
#     }
#     # Clean up the name to get the base type (e.g., 'Heater_1' -> 'Heater')
#     base_name = tool_name.split('_')[0]
#     return tool_map.get(base_name)
#
#
# def extract_equipment_parameter(
#         equipment_name: str,
#         stream_name: str,
#         process_description: str,
#         llm: ChatGoogleGenerativeAI
# ) -> dict:
#     """Extracts parameters for a single equipment tool using the LLM."""
#
#     tool_func = get_tool_from_name(equipment_name)
#     if not tool_func:
#         return {}
#
#     # StructuredTool instances use .name, not .__name__
#     tool_name = tool_func.name
#
#     # Map tool name to its required variable parameter (excluding inlet_stream and name)
#     required_args_map = {
#         'heater_tool': ('outlet_temp_C', 150.0),
#         'pump_tool': ('outlet_pressure_bar', 5.0),
#         'reactor_tool': ('conversion', 90.0),
#         'cooler_tool': ('outlet_temp_C', 40.0),
#     }
#
#     if tool_name not in required_args_map:
#         return {'name': stream_name.split(',')[0].strip()}  # Flash/Distillation only needs the base name
#
#     variable_arg_name, default_value = required_args_map[tool_name]
#
#     # The prompt guides the LLM to extract the parameter
#     prompt = f"""
#     You are a data extraction expert. Based on the process description for the equipment '{equipment_name}',
#     extract the required numerical value for the parameter '{variable_arg_name}'.
#     The process description is: "{process_description}"
#     Return ONLY the numerical value as a float. For conversion, return the percentage (e.g., 90.0).
#     If the value is not found, use the default value: {default_value}.
#     **Return ONLY the number.**
#     """
#     param_value_llm = llm.invoke(prompt).content
#
#     try:
#         # Use regex to find a single float or integer and convert it
#         match = re.search(r"[-+]?\d*\.\d+|\d+", param_value_llm)
#         param_value = float(match.group(0)) if match else default_value
#     except Exception:
#         param_value = default_value  # Fallback to default if extraction fails
#
#     return {
#         variable_arg_name: param_value,
#         'name': stream_name.split(',')[0].strip()  # Use the first name as the primary outlet name
#     }
#
#
# @tool
# def simulation(content: str) -> str:
#     """This tool is for simulating the styrene production process step-by-step.
#     It orchestrates calls to internal helper functions based on a detailed process description from RAG."""
#     print('---Simulation Tool: Starting Dynamic Process Simulation---')
#     simulation_output = "---Dynamic Simulation Results---\n\n"
#     current_stream = None
#     equipment_and_stream_dict = {}
#     updated_response_content = ""
#
#     try:
#         # Step 1: LLM-based extraction of process description and equipment order
#         process_info = RAG_CHAIN.invoke(
#             "Consider you are a chemical enginner and you are planning to simulate the styrene process. Collect all the information about the process with all the chemicals and equipment.")
#
#         updated_response = llm.invoke([
#             SystemMessage(content=f'''you are a chemical expert, review the following process information and the user's request. Return a step-by-step description of the process, ensuring each step corresponds to one equipment unit. If a stream needs to be heated from a standard inlet (e.g., 20C) or pressurized from 1 bar, explicitly add a 'Heater' or 'Pump' step at the start.
#             Example: Step 1: Pump_1, Step 2: Heater_1, Step 3: Reactor_1, etc.'''),
#             HumanMessage(content=f'process information={process_info}. and user conversation is={content}')
#         ])
#         updated_response_content = updated_response.content
#
#         # Extract structured equipment and stream names
#         equipment_and_stream_dict_llm = llm.invoke([SystemMessage(content=f'''consider you are a chemical engineer and you need to name the equipment and the outlet streams in sequence.
#         The equipment names should be in the following order (e.g., Heater_1, Pump_1, Reactor_1, etc.).
#         For the outlet stream, the name should be equipment name followed by 'outlet' (e.g., Heater_1_outlet).
#         For separators like Distillation Column and Flash, they have two outlets, name them 'Flash_1_vapor' and 'Flash_1_liquid'.
#
#         The final response MUST be a raw JSON dictionary where the equipment name is the key and a list of outlet streams is the value.
#         Example: {{"Pump_1" : ["Pump_1_outlet"], "Heater_1" : ["Heater_1_outlet"], "Flash_1": ["Flash_1_vapor", "Flash_1_liquid"]}}
#         **Crucially, your entire response MUST be the raw JSON text. DO NOT wrap the output in markdown code fences (```json) or include any surrounding text.**
#         '''), HumanMessage(content=updated_response_content)]).content
#
#         equipment_and_stream_dict = json.loads(clean_string(equipment_and_stream_dict_llm))
#
#         # Step 2: Extract initial feed conditions
#         feed_temp_pres_flow = llm.invoke([SystemMessage(content='''consider you are a chemical engineer and collect the inlet stream temperature in C,
#          pressure in bar or atm and flowrate in kmol/s. and pass the values in list like [275 , 5 , 100]. return only the list'''),
#                                           HumanMessage(content=updated_response_content)]).content
#
#         feed_comp = llm.invoke([SystemMessage(content=f'''You are a chemical data extraction expert. Collect all chemicals used in the initial feed stream and create a JSON object.
#         The chemical name is the key. The value is an object with two fields: **type** ('Mole_Fraction' or 'Mole_Flow') and **value** (a number).
#         If a chemical is not specified in the input stream, its value should be 0.
#         Example: {{"Benzene": {{"type": "Mole_Fraction", "value": 0.1}}, "Water": {{"type": "Mole_Flow", "value": 0.0}}}}
#         **Your entire output MUST be the raw JSON object and NOTHING else.**'''),
#                                 HumanMessage(content=updated_response_content)]).content
#
#         # Clean and call the inlet stream tool
#         feed_comp_cleaned = clean_string(feed_comp)
#         feed_temp_pres_flow_cleaned = clean_string(feed_temp_pres_flow)
#
#         current_stream = get_inlet_stream_tool(feed_temp_pres_flow_cleaned, feed_comp_cleaned)
#         simulation_output += f"Initial Feed Stream Created:\n{json.dumps(current_stream, indent=2)}\n\n"
#
#     except Exception as e:
#         return f"Error setting up initial simulation state or parsing LLM output. Error: {e}"
#
#     # Step 3: Simulation Loop (FIXED CALLING STRUCTURE)
#     print("Step 3: Starting sequential simulation loop...")
#
#     # Sort equipment keys to ensure sequential processing (e.g., Heater_1, Heater_2)
#     equipment_order = sorted(equipment_and_stream_dict.keys(), key=lambda x: (
#         x.split('_')[0], int(re.search(r'\d+', x).group(0)) if re.search(r'\d+', x) else 0))
#
#     active_stream = current_stream
#
#     for i, equipment_name in enumerate(equipment_order):
#         if not active_stream:
#             simulation_output += f"Skipping {equipment_name}: No active inlet stream available.\n"
#             break
#
#         tool_func = get_tool_from_name(equipment_name)
#         if not tool_func:
#             simulation_output += f"Skipping {equipment_name}: No matching simulation tool found.\n"
#             continue
#
#         outlet_names = equipment_and_stream_dict.get(equipment_name, [])
#         if not outlet_names:
#             simulation_output += f"Warning: No outlet stream defined for {equipment_name}. Skipping.\n"
#             continue
#
#         tool_name = tool_func.name
#
#         # 1. Extract parameters specific to the tool
#         tool_args_specific = extract_equipment_parameter(
#             equipment_name=equipment_name,
#             stream_name=', '.join(outlet_names),
#             process_description=updated_response_content,
#             llm=llm
#         )
#
#         # Identify the variable parameter (the one that isn't 'name')
#         variable_arg_name = next((k for k in tool_args_specific if k != 'name'), None)
#         variable_arg_value = tool_args_specific.get(variable_arg_name)
#         name_value = tool_args_specific.get('name')
#
#         # 2. Execute the tool using the safest call signature (strictly keyword arguments)
#         try:
#             # Prepare all arguments as keyword arguments
#             tool_kwargs = {
#                 'inlet_stream': active_stream,
#                 'name': name_value
#             }
#             # Add the variable argument if it exists (e.g., outlet_temp_C, conversion, pressure)
#             if variable_arg_name:
#                 tool_kwargs[variable_arg_name] = variable_arg_value
#
#             # Call the tool function using keyword arguments
#             # This is the most reliable way to interact with LangChain's StructuredTool
#             new_stream_data = tool_func(**tool_kwargs)
#
#         except Exception as e:
#             simulation_output += f"Error during tool execution for {equipment_name}: {e}\n"
#             break
#
#         # Update the active stream and log the result
#         simulation_output += f"--- {i + 1}: {equipment_name} Results ---\n"
#
#         if isinstance(new_stream_data, list):  # Separator (Flash/Distillation)
#             # Assumption: The first output stream (Vapor/Liquid) is the primary stream for the next sequential step
#             active_stream = new_stream_data[0]
#
#             for stream_data in new_stream_data:
#                 simulation_output += f"Outlet Stream '{stream_data['Name']}':\n{json.dumps(stream_data, indent=2)}\n"
#             simulation_output += f"Active Stream for next step set to: {active_stream['Name']}\n\n"
#
#         elif isinstance(new_stream_data, dict):  # Single stream output
#             active_stream = new_stream_data
#             simulation_output += f"Outlet Stream '{active_stream['Name']}':\n{json.dumps(active_stream, indent=2)}\n\n"
#
#         current_stream = active_stream
#
#     print('---Simulation Tool: Simulation Complete---')
#     return simulation_output
#
#
# @tool
# def other_discussion(content: str) -> str:
#     """This function is run when the user enquires anything not related to chemical engineering, process used in the paper or simulation."""
#     print('Other chat')
#     return 'sorry i can support only to chemical questions'
#
#
# @tool
# def chemical_discussion(content: str) -> str:
#     """This is a chemical discussion function if the user wants to enquire anything about chemicals and chemical engineering other than the details in the paper or related to the simulation."""
#     discussion_llm = llm
#     print("Chemical discussion mode activated.")
#     messages = [
#         SystemMessage(content="You are a helpful and knowledgeable assistant specializing in chemical engineering."),
#         HumanMessage(content=content)
#     ]
#     response = discussion_llm.invoke(messages)
#     print(f"🤖 Assistant: {response.content}")
#     return response.content
#
#
# @tool
# def process_enquiry_and_simulation(content: str) -> str:
#     """This tool is for all questions related to the styrene process, including simulation and paper-based enquiries."""
#     sub_llm = llm
#     sub_tool_descriptions = """
# TOOLS:
# - rag_enquiry: This tool is for answering questions about the styrene production process as described in the paper.
# - simulation: This tool is for simulating the styrene production process.
#
# RESPONSE FORMAT:
# To use a tool, you must respond with ONLY the tool name in angle brackets, like <tool_name>. Do not add any other text or explanation. If a tool is relevant, DO NOT provide a direct answer.
# """
#     sub_system_prompt = SystemMessage(content=f'''
# You are a specialized assistant for the styrene production process. Your task is to correctly route the user's request to one of the available tools.
# {sub_tool_descriptions}
# ''')
#     supported_messages = [sub_system_prompt, HumanMessage(content=content)]
#     sub_response = sub_llm.invoke(supported_messages)
#     sub_tool_call_match = re.search(r'<(\w+)>', sub_response.content)
#
#     if sub_tool_call_match:
#         tool_name = sub_tool_call_match.group(1)
#         if tool_name == 'rag_enquiry':
#             return rag_enquiry(content)
#         elif tool_name == 'simulation':
#             return simulation(content)
#         else:
#             return f"Error: {tool_name} is not a valid tool for this sub-agent."
#     else:
#         return sub_response.content
#
#
# print(process_enquiry_and_simulation('Simulate Styrene Production process'))
import re
import json
import os
import ast
from typing import TypedDict, Sequence, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from graphviz import Digraph

API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
PDF_PATH = 'The styrene production2.pdf'
gemini_model ="gemini-2.5-flash-lite"

# Initialize Google Generative AI components
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=API_KEY
)
llm = ChatGoogleGenerativeAI(
    model=gemini_model,
    google_api_key=API_KEY,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


# --- State Management ---
def add_messages(left: list, right: list):
    """Function to add messages for state management"""
    return left + right


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def clean_string(input_string):
    """
    Removes '```json', '\n', and '```' from a string.
    """
    cleaned_string = input_string.replace('```json', '')
    cleaned_string = cleaned_string.replace('\n', '')
    cleaned_string = cleaned_string.replace('```', '')
    return cleaned_string



def setup_rag_chain(pdf_path: str):
    """Sets up a RAG chain by loading a PDF and creating a ChromaDB vector store."""
    db_name = os.path.splitext(os.path.basename(pdf_path))
    persist_directory = f"./{db_name}_rag_db"

    if not os.path.exists(pdf_path):
        print(f"Error: The PDF file '{pdf_path}' was not found.")
        return None

    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"Creating a new RAG vector store for '{db_name}'...")
        try:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)

            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"Vector store created at '{persist_directory}'.")
        except Exception as e:
            print(f"Error creating vector store: {e}")
            return None
    else:
        print(f"Loading existing RAG vector store for '{db_name}'.")
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template("""
    You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know.

    Question: {question}
    Context: {context}
    Answer:
    """)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )

    return rag_chain


# Initialize the RAG chain globally
RAG_CHAIN = setup_rag_chain(PDF_PATH)


# --- Helper Functions for Simulation ---
def stream(name: str, temperature: float, pressure: float, chemical_fraction: dict, flow: float):
    """Helper function to define the stream."""
    # Calculate total moles for each component
    total_moles = {chem: frac * flow for chem, frac in chemical_fraction.items()}

    stream_dict = {
        'Name': name,
        'Temperature (C)': temperature,
        'Pressure (bar)': pressure,
        'Molar Flowrate (mol/s)': flow,
        'Mole Fraction': chemical_fraction,
        # 'Total Moles': total_moles,  # Added for reactor tool
    }
    print('***' * 100)
    print('Stream Data', json.dumps(stream_dict, indent=2))
    return stream_dict



def get_inlet_stream_tool(feed_condition, feed_composition) -> dict:
    feed_condition = ast.literal_eval(feed_condition)
    feed_composition = json.loads(feed_composition)
    feed_temp = feed_condition[0]
    feed_pressure = feed_condition[1]
    inlet_flowrate = feed_condition[2]
    list_of_chemicals = list(feed_composition.keys())
    mole_comp_dict = {}
    for i in list_of_chemicals:
        if feed_composition[i]["type"] == 'Mole_Fraction':
            mole_comp_dict[i] = feed_composition[i]["value"] * inlet_flowrate
        else:
            mole_comp_dict[i] = feed_composition[i]["value"]
    mole_frac_dict = {}

    for i in list_of_chemicals:
        mole_frac_dict[i] = mole_comp_dict[i] / inlet_flowrate

    # print(feed_composition[i]["value"])
    inlet_strem = stream(
        name='Feed',
        temperature=feed_temp,
        pressure=feed_pressure,
        chemical_fraction=mole_frac_dict,
        flow=inlet_flowrate
    )
    return inlet_strem

# --- Equipment Tools (do NOT use @tool decorator for internal helpers) ---
def heater_tool_func(inlet_stream: dict, outlet_temp_C: float, eq_name,stream_name) -> dict:
    """Heats a stream to a specified temperature."""
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Temperature (C)'] = outlet_temp_C
    print(f"Heater: {inlet_stream['Name']} -> {stream_name}, T: {outlet_temp_C}C")
    return outlet_stream


def pump_tool_func(inlet_stream: dict, outlet_pressure_bar: float,eq_name, stream_name) -> dict:
    """Pumps a stream to a specified pressure."""
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Pressure (bar)'] = outlet_pressure_bar
    print(f"Pump: {inlet_stream['Name']} -> {stream_name}, P: {outlet_pressure_bar} bar")
    return outlet_stream


def reactor_tool_func(inlet_stream: dict, conversion: float,eq_name, stream_name) -> dict: #reaction_stochio:dict
    """Conversion reactor for benzene + ethylene -> ethylbenzene."""
    # print('reaction Stochiometry',reaction_stochio)
    outlet_stream = inlet_stream.copy()
    inlet_moles = inlet_stream["Mole Fraction"]

    benzene_in = inlet_moles.get('benzene', 0)
    ethylene_in = inlet_moles.get('ethylene', 0)

    moles_benzene_reacted = benzene_in * (conversion / 100)
    moles_ethylene_reacted = moles_benzene_reacted
    moles_ethylbenzene_produced = moles_benzene_reacted

    benzene_out = benzene_in - moles_benzene_reacted
    ethylene_out = ethylene_in - moles_ethylene_reacted
    ethylbenzene_out = inlet_moles.get('ethyl benzene', 0) + moles_ethylbenzene_produced

    new_moles = {
        'benzene': benzene_out,
        'ethylene': ethylene_out,
        'ethyl benzene': ethylbenzene_out
    }

    total_flow_out = sum(new_moles.values())

    # outlet_stream['Total Moles'] = new_moles
    outlet_stream['Molar Flowrate (mol/s)'] = total_flow_out
    outlet_stream['Mole Fraction'] = {
        chem: moles / total_flow_out for chem, moles in new_moles.items() if total_flow_out > 0
    }
    outlet_stream['Name'] = stream_name[0]
    print(f"Reactor: Conversion = {conversion}%, Benzene reacted = {moles_benzene_reacted:.2f} mol/s")
    return outlet_stream


def cooler_tool_func(inlet_stream: dict, outlet_temp_C: float,eq_name, stream_name) -> dict:
    """Cools a stream to a specified temperature."""
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Temperature (C)'] = outlet_temp_C
    print(f"Cooler: {inlet_stream['Name']} -> {stream_name}, T: {outlet_temp_C}C")
    return outlet_stream


def flash_tool_func(inlet_stream: dict,eq_name,stream_name) -> list: #outlet_temp_C :float,
    """Flash separator (50/50 split for simplification)."""
    outlet_stream1 = inlet_stream.copy()
    outlet_stream2 = inlet_stream.copy()

    outlet_stream1['Molar Flowrate (mol/s)'] *= 0.5
    outlet_stream2['Molar Flowrate (mol/s)'] *= 0.5

    # # Update Total Moles for both streams
    # outlet_stream1['Total Moles'] = {k: v * 0.5 for k, v in inlet_stream['Total Moles'].items()}
    # outlet_stream2['Total Moles'] = {k: v * 0.5 for k, v in inlet_stream['Total Moles'].items()}

    outlet_stream1['Name'] = stream_name[0]
    outlet_stream2['Name'] = stream_name[1]

    print(f"Flash: {inlet_stream['Name']} -> Vapor + Liquid")
    return [outlet_stream1, outlet_stream2]

def dist_tool_func(inlet_stream: dict,outlet_temp_C:float,eq_name, stream_name) -> list: #
    """Flash separator (50/50 split for simplification)."""
    outlet_stream1 = inlet_stream.copy()
    outlet_stream2 = inlet_stream.copy()

    outlet_stream1['Molar Flowrate (mol/s)'] *= 0.5
    outlet_stream2['Molar Flowrate (mol/s)'] *= 0.5

    # Update Total Moles for both streams
    # outlet_stream1['Total Moles'] = {k: v * 0.5 for k, v in inlet_stream['Total Moles'].items()}
    # outlet_stream2['Total Moles'] = {k: v * 0.5 for k, v in inlet_stream['Total Moles'].items()}

    outlet_stream1['Name'] = stream_name[0]
    outlet_stream2['Name'] = stream_name[1]

    print(f"Flash: {inlet_stream['Name']} -> Vapor + Liquid")
    return [outlet_stream1, outlet_stream2]


# --- Top-Level Tools ---
@tool
def rag_enquiry(content: str) -> str:
    """Answers questions about the styrene production process from the paper."""
    if RAG_CHAIN:
        return RAG_CHAIN.invoke(content)
    return "Error: RAG chain is not configured."


@tool
def simulation(content: str) -> str:
    """Simulates the styrene production process step-by-step."""
    print('---Simulation Tool: Starting Dynamic Process Simulation---')

    simulation_output = "---Dynamic Simulation Results---\n\n"
    dot = Digraph(comment='Flow Diagram')
    node_dict={'heater':'trapezium',
            'pump': 'pentagon',
            'reactor': 'house',
            'cooler':'trapezium',
            'flash': 'cylinder',
            'distillation':'box3d',
            'Feed_stream':'rarrow'}
    # Step 1: Get process information and feed conditions
    try:
        print("Step 1: Retrieving process information...")

        process_info = RAG_CHAIN.invoke(
            "Consider you are a chemical enginner and you are planning to simulate the styrene process . collect all the information about the process with all the chemicals and equipment")
        updated_response = llm.invoke([
            SystemMessage(content=f'''you are a chemical expert , check and make any changes needed in the process by user and return the process in steps where 
each equipment is sent as one step like step 1, step 2 and goes on ,
Follow the conditions like if a stream is preheated then consider that the stream is at 20C and a heater is used for heating and add a step for Heater not as preheater   ,
similary when a stream is pre pressurised or pre prd consider the inlet pressure is 1 bar and a pump is used to pressure the stream and add a step Pump'''),
            HumanMessage(content=f'process information  ={process_info}. and conversations is = {content}')
        ])

        feed_temp_pres_flow = llm.invoke([SystemMessage(content='''consider you are a chemical engineer and collect the inlet stream temperature in C,
                 pressure in bar or atm and flowrate in kmol/s. and pass the values in list like [275 , 5 , 100]. return only the list'''),
                                          HumanMessage(content=updated_response.content)])

        feed_comp = llm.invoke([SystemMessage(content=f'''You are a chemical data extraction expert. Your task is to collect all chemicals used in the process and create a JSON object
**Your entire output MUST be the raw JSON object and NOTHING else.** DO NOT include any introductory text, explanation, or markdown code fences (```json, ```) around the output.
The JSON structure MUST adhere exactly to this format:
The chemical name is the key.
The value is an object with two fields:
1. **type**: Must be 'Mole_Fraction' or 'Mole_Flow'.
2. **value**: The quantity (a number).
If a chemical is not specified in the input stream, its value should be **0**.
**Target JSON Structure Example:**
{{"Benzene": {{"type": "Mole_Fraction", "value": 0.1}}, "Toluene": {{"type": "Mole_Fraction", "value": 0.9}}, "Water": {{"type": "Mole_Flow", "value": 0.0}}}}
'''), HumanMessage(content=updated_response.content)])


        print('Feed conditions:', feed_temp_pres_flow.content)
        print('Feed composition:', feed_comp.content)

        # Clean and create inlet stream
        feed_comp_clean = clean_string(feed_comp.content)
        feed_cond_clean = feed_temp_pres_flow.content.strip()

        current_stream = get_inlet_stream_tool(feed_cond_clean, feed_comp_clean)
        print('inlet Feed stream',current_stream)
        simulation_output += f"Initial Feed Stream:\n{json.dumps(current_stream, indent=2)}\n\n"
        currennt_stream_object='Feed_stream'
        dot.node(currennt_stream_object, currennt_stream_object, shape='rarrow')



    except Exception as e:
        return f"Error creating inlet stream: {e}\n\nDebug info:\nFeed conditions: {feed_temp_pres_flow.content}\nFeed comp: {feed_comp.content}"

    # Step 2: Get process steps
    try:
        print("Step 2: Extracting process steps...")

        steps_response = llm.invoke([
            SystemMessage(content='''List each equipment unit in the process as separate numbered steps.
if preheater is used consider it as Heater equipment is used to heat
Format: 
Step 1: Heater - heat feed to 200C
Step 2: Reactor - convert benzene at 95% conversion
Step 3: Cooler - cool to 50C
etc.  '''),
            HumanMessage(content=f'Process: {process_info}\nUser query: {content}')
        ])

        equipment_and_stream_dict = llm.invoke([SystemMessage(content='''consider you are a chemical engineer and you need to name the equipment and the outlet streams
        the equipment names are in the followinf order with number for like for multiple heater name should be Heater_1, Heater_2 . similarly for other equyipments
        for the outlet stream the the name should be equipment name followed by outlet like Heater_1_outlet , pump_1_outlet.
        for distillation column and Flash it have two outlets the name should be Distillation_1_liquid ,Distillation_1_vapor and Flash_1_liquid and Flash_1_vapor 

        the final response should be in the dictionary structure with equipment name as key and list of the outlet stream as value like {
        'Heater_1' : [Heater_1_outlet],
        'Distillation_1':[Distillation_1_liquid ,Distillation_1_vapor]
        }'''), HumanMessage(content=steps_response.content)])

        # print('Process steps:', steps_response.content)
        # print('equipment_and_stream_dict',equipment_and_stream_dict.content)
        equipment_and_stream_dict=json.loads(clean_string(equipment_and_stream_dict.content))

        # Parse steps
        step_lines = [line.strip() for line in steps_response.content.split('\n') if line.strip() and 'Step' in line]
        # print('steps',step_lines)

        if not step_lines:
            return f"Could not extract process steps. Response was:\n{steps_response.content}"

        # Map tool names to functions
        tools_map = {
            'heater': heater_tool_func,
            'pump': pump_tool_func,
            'reactor': reactor_tool_func,
            'cooler': cooler_tool_func,
            'flash': flash_tool_func,
            'distillation':dist_tool_func,
        }

        # Process each step
        for i, step_desc in enumerate(step_lines, 1):
            print(f"\n{'=' * 80}\nProcessing: {step_desc}\n{'=' * 80}")

            try:
                # Determine tool and extract parameters
                tool_selection = llm.invoke([
                    SystemMessage(content=f'''Based on this process step, select ONE tool and extract parameters.
Available tools: ['heater', 'pump', 'reactor', 'cooler', 'flash' ,'distillation']
select the tool_name from the availabe tools list. select the tool which suits the best 

specify only the tool_name in the tool section in json

Return ONLY valid JSON (no markdown):
{{"tool": "tool_name", "params": {{"outlet_temp_C": 200}} }}

Parameter requirements:
- heater: outlet_temp_C (float)
- pump: outlet_pressure_bar (float)
- reactor: conversion (float, percentage)
- cooler: outlet_temp_C (float)
- flash: outlet_temp_C (float)
- distillation :outlet_temp_C (float)

IMPORTANT: The name should describe the output, like "Heated_Feed" or "Reactor_Outlet".'''),
                    HumanMessage(content=step_desc)
                ])

                # print(f"Tool selection response: {tool_selection.content}")


                # Parse tool call
                tool_call = json.loads(clean_string(tool_selection.content))
                tool_name = tool_call['tool'].lower()
                tool_params = tool_call['params']
                # print('tool params = ',tool_params)
                print('EQ data = ',equipment_and_stream_dict)
                # print(list(equipment_and_stream_dict.keys())[i-1])
                # print( equipment_and_stream_dict[list(equipment_and_stream_dict.keys())[i-1]])
                tool_params['eq_name']=list(equipment_and_stream_dict.keys())[i-1]
                tool_params['stream_name']= equipment_and_stream_dict[list(equipment_and_stream_dict.keys())[i-1]]
                # print('tool params = ', tool_params)
                node_name=list(equipment_and_stream_dict.keys())[i-1]
                dot.node(node_name, node_name, shape=node_dict[tool_name], labelloc='b', fontsize='10',
                         lp='100, -200')  # Added width and height attributes  image=node_dict[tool_name],
                dot.edge(currennt_stream_object, node_name)
                currennt_stream_object=node_name

                # print('''
                #
                # ''')
                # print('nodes',list(equipment_and_stream_dict.keys())[i-1],list(equipment_and_stream_dict.keys())[i-1] ,node_dict[tool_name])
                # dot.node(list(equipment_and_stream_dict.keys())[i-1],list(equipment_and_stream_dict.keys())[i-1],shape=node_dict[tool_name])
                # for j in equipment_and_stream_dict[list(equipment_and_stream_dict.keys())[i-1]]:
                #     dot.edge(currennt_stream_object, list(equipment_and_stream_dict.keys())[i-1], label=j)
                #
                # currennt_stream_object=list(equipment_and_stream_dict.keys())[i-1]

                # if tool_name not in tools_map:
                #     simulation_output += f"Step {i} ERROR: Unknown tool '{tool_name}'\n\n"
                #     continue

                # Execute tool
                print('tool_name',tool_name)
                tool_func = tools_map[tool_name]
                print('tool_func',tool_func)
                tool_params['inlet_stream'] = current_stream
                print('tool_params',tool_params)
                result = tool_func(**tool_params)
                print('result',result)


                # Handle flash tool (returns list)
                if isinstance(result, list):
                    simulation_output += f"Step {i}: {step_desc}\n"
                    for stream in result:
                        simulation_output += f"  {stream['Name']}:\n{json.dumps(stream, indent=4)}\n"
                    current_stream = result  # Continue with liquid stream[1]
                else:
                    simulation_output += f"Step {i}: {step_desc}\n"
                    simulation_output += f"Output Stream:\n{json.dumps(result, indent=2)}\n\n"
                    current_stream = result

            except Exception as e:
                error_msg = f"Step {i} ERROR: {e}\nTool response: {tool_selection.content}\n"
                print(error_msg)
                simulation_output += error_msg + "\n"


    except Exception as e:
        return f"Error during simulation: {e}"


    # Set some attributes for better visualization
    dot.graph_attr['rankdir'] = 'LR'  # Changed rankdir to LR for horizontal layout
    dot.graph_attr['splines'] = 'polyline'  # Added splines='ortho' for orthogonal lines

    # Display the flow diagram directly
    # display(dot)
    dot.render('flow_diagram_with_images', format='png',
               view=False)  # Set view=False to not automatically open the file
    print('\n---Simulation Complete---')
    return simulation_output


@tool
def other_discussion(content: str) -> str:
    """For non-chemical engineering questions."""
    return 'Sorry, I can only support chemical engineering questions.'


@tool
def chemical_discussion(content: str) -> str:
    """For general chemical engineering discussion."""
    messages = [
        SystemMessage(content="You are a knowledgeable chemical engineering assistant."),
        HumanMessage(content=content)
    ]
    response = llm.invoke(messages)
    return response.content


@tool
def process_enquiry_and_simulation(content: str) -> str:
    """Routes questions about styrene process to appropriate sub-tools."""
    sub_response = llm.invoke([
        SystemMessage(content='''You are routing user queries about styrene production.
Respond with ONLY ONE of these: <rag_enquiry> or <simulation>

Use <rag_enquiry> for: questions about the process, theory, equipment details
Use <simulation> for: "simulate", "run simulation", "calculate", "model the process"'''),
        HumanMessage(content=content)
    ])

    if '<simulation>' in sub_response.content:
        return simulation.invoke({"content": content})
    elif '<rag_enquiry>' in sub_response.content:
        return rag_enquiry.invoke({"content": content})
    else:
        return sub_response.content


# Test the simulation
if __name__ == "__main__":
    result = process_enquiry_and_simulation.invoke({"content": "Simulate the Styrene Production process"})
    print("\n" + "=" * 100)
    print("FINAL RESULT:")
    print("=" * 100)
    print(result)




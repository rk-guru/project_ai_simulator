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
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from graphviz import Digraph
import uuid
import pandas as pd



API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
PDF_PATH = 'The ethylbenzene production.pdf'
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
            # print(f"Error creating vector store: {e}")
            return None
    else:
        # print(f"Loading existing RAG vector store for '{db_name}'.")
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


def process_stream_data(data):
    """Processes stream data dictionary into a DataFrame."""
    data_list = []
    for key, value in data.items():
        if key == "Mole Fraction":
            data_list.append({"Attribute": key, data["Name"]: ""})
            for sub_key, sub_value in value.items():
                data_list.append({"Attribute": sub_key, data["Name"]: sub_value})
        elif key != "Name":
            data_list.append({"Attribute": key, data["Name"]: value})
    df = pd.DataFrame(data_list)
    df = df.set_index('Attribute')
    return df

def process_energy_stream_data(data):
    """Processes energy stream data dictionary into a DataFrame."""
    data_list = []
    for key, value in data.items():
        if key != "Name":
            data_list.append({"Attribute": key, data["Name"]: value})
    df = pd.DataFrame(data_list)
    df = df.set_index('Attribute')
    return df

# --- Helper Functions for Simulation ---
def stream(name: str,equipment:str, temperature: float, pressure: float, chemical_fraction: dict, flow: float):
    """Helper function to define the stream."""
    # Calculate total moles for each component
    total_moles = {chem: frac * flow for chem, frac in chemical_fraction.items()}
    # print('process',name,'chemical_fraction',chemical_fraction)

    stream_dict = {
        'Name': name,
        'Equipment':equipment,
        'Temperature (C)': temperature,
        'Pressure (bar)': pressure,
        'Molar Flowrate (mol/s)': flow,
        'Mole Fraction': chemical_fraction,
        # 'Total Moles': total_moles,  # Added for reactor tool
    }
    # print('***' * 100)
    # print('Stream Data', json.dumps(stream_dict, indent=2))
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
        equipment= 'Feed_stream',
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
    outlet_stream['Equipment'] = eq_name
    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 125}
    # df_stream = process_stream_data(outlet_stream)
    # df_energy = process_energy_stream_data(energy_dict)
    # df = pd.concat([df_stream, df_energy], axis=1)
    # df = df.fillna('-')
    # Data_table=pd.concat([Data_table,df], axis=1)
    # print(f"Heater: {inlet_stream['Name']} -> {stream_name}, T: {outlet_temp_C}C")
    return [outlet_stream] , energy_dict


def pump_tool_func(inlet_stream: dict, outlet_pressure_bar: float,eq_name, stream_name) -> dict:
    """Pumps a stream to a specified pressure."""
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Pressure (bar)'] = outlet_pressure_bar
    outlet_stream['Equipment'] = eq_name

    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 5.5}
    # df_stream = process_stream_data(outlet_stream)
    # df_energy = process_energy_stream_data(energy_dict)
    # df = pd.concat([df_stream, df_energy], axis=1)
    # df = df.fillna('-')
    # Data_table = pd.concat([Data_table, df], axis=1)
    # print(f"Pump: {inlet_stream['Name']} -> {stream_name}, P: {outlet_pressure_bar} bar")
    return [outlet_stream], energy_dict


def reactor_tool_func(inlet_stream: dict, conversion: float,eq_name,reaction_stoichiometry:dict, stream_name) -> dict: #reaction_stochio:dict
    """Conversion reactor for benzene + ethylene -> ethylbenzene."""
    # print('''
    #
    # reaction Stochiometry''',conversion)
    #
    # print('Reactor_stochio',reaction_stoichiometry)
    outlet_stream = inlet_stream.copy()
    # inlet_moles = inlet_stream["Mole Fraction"]
    #
    # benzene_in = inlet_moles.get('benzene', 0)
    # ethylene_in = inlet_moles.get('ethylene', 0)
    #
    # moles_benzene_reacted = benzene_in * (conversion / 100)
    # moles_ethylene_reacted = moles_benzene_reacted
    # moles_ethylbenzene_produced = moles_benzene_reacted
    #
    # benzene_out = benzene_in - moles_benzene_reacted
    # ethylene_out = ethylene_in - moles_ethylene_reacted
    # ethylbenzene_out = inlet_moles.get('ethyl benzene', 0) + moles_ethylbenzene_produced
    #
    # new_moles = {
    #     'benzene': benzene_out,
    #     'ethylene': ethylene_out,
    #     'ethyl benzene': ethylbenzene_out
    # }
    #
    # total_flow_out = sum(new_moles.values())

    # outlet_stream['Total Moles'] = new_moles
    outlet_stream['Molar Flowrate (mol/s)'] = 120
    # outlet_stream['Mole Fraction'] = 120
    outlet_stream['Mole Fraction'] ={'Benzene': 0.3, 'Ethylene': 0.3, 'Ethyl Benzene': 0.4}
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Equipment'] = eq_name

    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 834}
    # df_stream = process_stream_data(outlet_stream)
    # df_energy = process_energy_stream_data(energy_dict)
    # df = pd.concat([df_stream, df_energy], axis=1)
    # df = df.fillna('-')
    # Data_table = pd.concat([Data_table, df], axis=1)

    # print(f"Reactor: Conversion = {conversion}%, Benzene reacted = {moles_benzene_reacted:.2f} mol/s")
    return [outlet_stream], energy_dict


def cooler_tool_func(inlet_stream: dict, outlet_temp_C: float,eq_name, stream_name) -> dict:
    """Cools a stream to a specified temperature."""
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = stream_name[0]
    outlet_stream['Temperature (C)'] = outlet_temp_C
    outlet_stream['Equipment'] = eq_name

    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 6001}

    # print(f"Cooler: {inlet_stream['Name']} -> {stream_name}, T: {outlet_temp_C}C")
    return [outlet_stream], energy_dict


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
    outlet_stream1['Equipment'] = eq_name
    outlet_stream2['Equipment'] = eq_name

    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 714}

    # print(f"Flash: {inlet_stream['Name']} -> Vapor + Liquid")
    return [outlet_stream1, outlet_stream2], energy_dict

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

    outlet_stream1['Equipment'] = eq_name
    outlet_stream2['Equipment'] = eq_name
    energy_dict = {
        "Name": f"{eq_name}_energy",
        'Equipment': eq_name,
        "Energy": 215}

    # print(f"Flash: {inlet_stream['Name']} -> Vapor + Liquid")
    return [outlet_stream1, outlet_stream2], energy_dict


# --- Top-Level Tools ---
@tool
def rag_enquiry(content: str) -> str:
    """Answers questions about the ethylbenzene production process from the paper."""
    if RAG_CHAIN:
        return RAG_CHAIN.invoke(content)
    return "Error: RAG chain is not configured."


@tool
def simulation(content: str) -> str:
    """Simulates the ethylbenzene production process step-by-step."""
    # print('---Simulation Tool: Starting Dynamic Process Simulation---')
    Data_table = pd.DataFrame()
    simulation_output = "---Dynamic Simulation Results---\n\n"
    dot = Digraph(comment='Flow Diagram')
    node_dict={'heater':'eq_image\\heat.png',
            'pump': 'eq_image\\Centrifugal Pump.jpg',
            'reactor': 'eq_image\\tank2.jpg',
            'cooler':'eq_image\\cool.png',
            'flash': 'eq_image\\Vertical_Vessel.jpg',
            'distillation':'eq_image\\Packed_Vessel.jpg'}
    # Step 1: Get process information and feed conditions
    try:
        # print("Step 1: Retrieving process information...")

        process_info = RAG_CHAIN.invoke(
            "Consider you are a chemical enginner and you are planning to simulate the ethylbenzene process . collect all the information about the process with all the chemicals and equipment")
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


        # print('Feed conditions:', feed_temp_pres_flow.content)
        # print('Feed composition:', feed_comp.content)

        # Clean and create inlet stream
        feed_comp_clean = clean_string(feed_comp.content)
        feed_cond_clean = feed_temp_pres_flow.content.strip()

        current_stream = get_inlet_stream_tool(feed_cond_clean, feed_comp_clean)
        # print('inlet Feed stream',current_stream)
        simulation_output += f"Initial Feed Stream:\n{json.dumps(current_stream, indent=2)}\n\n"
        currennt_stream_object='Feed_stream'
        dot.node(currennt_stream_object, '', shape='rarrow', labelloc='b', fontsize='10', xlabel=currennt_stream_object)

        in_stream_df = process_stream_data(current_stream)
        df = in_stream_df.fillna('-')
        Data_table = pd.concat([Data_table, df], axis=1)



    except Exception as e:
        return f"Error creating inlet stream: {e}\n\nDebug info:\nFeed conditions: {feed_temp_pres_flow.content}\nFeed comp: {feed_comp.content}"

    # Step 2: Get process steps
    try:
        # print("Step 2: Extracting process steps...")

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

for reaction_stoichiometry follow the JSON structure
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
                # Parse tool call
                tool_call = json.loads(clean_string(tool_selection.content))
                tool_name = tool_call['tool'].lower()
                tool_params = tool_call['params']
                if tool_name =='reactor':
                    # print('step',step_desc)
                    # print('chemcials',feed_comp_clean)
                    reaction_stoichiometry = llm.invoke([
                        SystemMessage(content=f''' consider you are a chemical engineering experert to return the chemical reaction in json structure ,
based on the moles used specify the value and if the compound is a reactant specify it in negative like -1,-2 and for product speciy it in positive like 1 ,2
for json structure follow the compound followed by the number of moles used like 
specify the same name as mentiond in the user specified compound names
if one mole of toluene produce one mole of benzene structure like 
{{'toluene':-1 , 'benzene':1}}

for reaction_stoichiometry follow the JSON structure
Return ONLY valid JSON (no markdown)'''),
                        HumanMessage(content=f'Process info {process_info} . User specified compound names {feed_comp_clean}')
                    ])

                    tool_params['reaction_stoichiometry'] = clean_string(reaction_stoichiometry.content)
                # print('tool_call =  ',tool_call)
                # print('EQ data = ',equipment_and_stream_dict)
                # print(list(equipment_and_stream_dict.keys())[i-1])
                # print( equipment_and_stream_dict[list(equipment_and_stream_dict.keys())[i-1]])
                tool_params['eq_name']=list(equipment_and_stream_dict.keys())[i-1]
                tool_params['stream_name']= equipment_and_stream_dict[list(equipment_and_stream_dict.keys())[i-1]]
                # print('tool params = ', tool_params)
                node_name=list(equipment_and_stream_dict.keys())[i-1]
                # dot.node(node_name, node_name, shape=node_dict[tool_name], labelloc='b', fontsize='10',lp='100, -200')
                dot.node(node_name,'', image=node_dict[tool_name],shape='none',imagescale='true', width='0.2', height='0.5', labelloc='b', fontsize='10',xlabel= node_name)
                           # Added width and height attributes  image=node_dict[tool_name],
                dot.edge(currennt_stream_object, node_name)
                currennt_stream_object=node_name
                tool_func = tools_map[tool_name]
                tool_params['inlet_stream'] = current_stream
                result , energy = tool_func(**tool_params)

                for i in result:
                    df_stream = process_stream_data(i)
                    df_stream=df_stream.fillna('-')
                    Data_table = pd.concat([Data_table, df_stream], axis=1)

                df_energy = process_energy_stream_data(energy)
                df_energy=df_energy.fillna('-')
                # df = pd.concat([df_stream, df_energy], axis=1)
                # df = df.fillna('-')
                Data_table = pd.concat([Data_table, df_energy], axis=1)


                # Handle flash tool (returns list)
                if isinstance(result, list):
                    simulation_output += f"Step {i}: {step_desc}\n"
                    for stream in result:
                        simulation_output += f"  {stream['Name']}:\n{json.dumps(stream, indent=4)}\n"
                    current_stream = result[0]  # Continue with liquid stream[1]
                else:
                    simulation_output += f"Step {i}: {step_desc}\n"
                    simulation_output += f"Output Stream:\n{json.dumps(result, indent=2)}\n\n"
                    current_stream = result[0]

            except Exception as e:
                error_msg = f"Step {i} ERROR: {e}\nTool response: {tool_selection.content}\n"
                print(error_msg)
                simulation_output += error_msg + "\n"


    except Exception as e:
        return f"Error during simulation: {e}"

    print(Data_table)

    Data_table.to_csv('Datatable.csv')
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
    """Routes questions about ethylbenzene process to appropriate sub-tools."""
    sub_response = llm.invoke([
        SystemMessage(content='''You are routing user queries about ethylbenzene production.
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



# --- LangGraph Agent Setup ---

# Primary tools for the main agent
tools = [other_discussion, chemical_discussion, process_enquiry_and_simulation]
tools_by_name = {tool.name: tool for tool in tools}


def agent1(state: AgentState) -> AgentState:
    # print('---AGENT 1: INVOKED (Router)---')
    main_tool_descriptions = """
TOOLS:
- other_discussion: Use this tool for general topics not related to chemical engineering.
- chemical_discussion: Use this tool for general questions about chemicals and chemical engineering, not related to the ethylbenzene process.
- process_enquiry_and_simulation: Use this tool for all questions related to the ethylbenzene process, including simulations and enquiries from the paper.

RESPONSE FORMAT:
To use a tool, you must respond with ONLY the tool name in angle brackets, like <tool_name>. Do not add any other text or explanation. If a tool is relevant, DO NOT provide a direct answer.
"""
    system_prompt_content = f'''
    You are a chemical expert assistant. Your primary task is to correctly route the user's request to one of the available tools.
    {main_tool_descriptions}
    '''
    system_prompt = SystemMessage(content=system_prompt_content)

    # Only pass the system prompt and the latest user message for routing
    latest_user_message = state['messages'][-1]
    all_messages = [system_prompt, latest_user_message]

    response = llm.invoke(all_messages)
    # print(f"LLM Router Response: {response.content}")

    tool_call_match = re.search(r'<(\w+)>', response.content)

    if tool_call_match:
        tool_name = tool_call_match.group(1)
        # print(f"USING TOOL: {tool_name}")
        # LangGraph requires a tool_call structure for the ToolNode
        tool_call = {
            "id": str(uuid.uuid4()),
            "name": tool_name,
            "args": {"content": latest_user_message.content}
        }
        return {'messages': [AIMessage(content="", tool_calls=[tool_call])]}
    else:
        # If no tool is called, the LLM provides a direct response
        return {'messages': [response]}


def should_continue(state: AgentState) -> str:
    # print('---SHOULD CONTINUE: INVOKED (Conditional Edge)---')
    last_message = state['messages'][-1]

    # If the last message is an AIMessage with tool_calls, it means a tool needs to be run.
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # print('---SHOULD CONTINUE: Moving to TOOLS---')
        return "continue"
    else:
        # The agent responded directly, or the tool has already run and the flow ended.
        # print('---SHOULD CONTINUE: ENDING TURN---')
        return "end"


def print_messages(messages):
    """Function to print the messages in a more readable format"""
    if not messages:
        return
    for message in messages:
        if isinstance(message, ToolMessage):
            print(f"\n<< TOOL RESULT >>\n{message.content}\n")
        elif isinstance(message, HumanMessage):
            print(f"\n>> USER: {message.content}")
        elif isinstance(message, SystemMessage):
            # System messages are usually internal for routing, don't show to user
            pass
        elif message.content:
            print(f"\n<< ASSISTANT: {message.content} >>\n")


# Build the LangGraph
graph = StateGraph(AgentState)
graph.add_node('agent', agent1)
# Use ToolNode to automatically execute the function corresponding to the tool call
tool_node = ToolNode(tools=tools)
graph.add_node('tools', tool_node)

# **FIX FOR: ValueError: START cannot be an end node**
# The entry point must flow into a valid node.
graph.add_edge(START, 'agent')

graph.add_conditional_edges(
    'agent',
    should_continue,
    {
        'continue': 'tools',
        'end': END
    }
)
graph.add_edge('tools', END)

app = graph.compile()


def run_document_agent(user_input):
    messages = []

    # while True:
    #     try:
    #         user_input = input('>> What would you like to do next? ')
    #     except EOFError:
    #         break
    #
    #     if user_input.lower() in ['exit', 'quit']:
    #         break

    # Only append the latest user message to the state
    messages.append(HumanMessage(content=user_input))

    # Invoke the graph with the current state (all messages)
    result = app.invoke({'messages': messages})

    # Determine which messages are new (the LLM's response and tool executions)
    new_messages = result['messages'][len(messages):]

    # Print the new messages to the user
    print_messages(new_messages)

    # Update the overall message history with the results of the graph execution
    messages = result['messages']
    print('message = ',messages)
    return messages


if __name__ == '__main__':
    # Initial check if RAG setup succeeded
    if RAG_CHAIN is None:
        print("\nFATAL ERROR: RAG chain initialization failed. Check console for details (e.g., missing PDF file).\n")
    else:
        run_document_agent()



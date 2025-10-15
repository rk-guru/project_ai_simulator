import os
import re
import uuid
import json
from typing import TypedDict, Sequence, Annotated
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode


# --- State Management ---
def add_messages(left: list, right: list):
    """Function to add messages for state management"""
    return left + right


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# --- RAG Setup ---
# Define constants for RAG
# IMPORTANT: You must place the 'The styrene production.pdf' file in the same directory as this script.
PDF_PATH = 'The styrene production.pdf'
# NOTE: Ensure you have Ollama running and have pulled these models:
# For the main LLM: 'ollama pull llama3.1:latest'
# For embeddings: 'ollama pull mxbai-embed-large'
LLM_MODEL = "llama3.1:latest"
EMBEDDING_MODEL = "mxbai-embed-large"
GPU_CONFIG = {'num_gpu': -1}


def setup_rag_chain(pdf_path: str):
    """
    Sets up a RAG chain by loading a PDF, creating a ChromaDB vector store,
    and initializing the LangChain components.
    """
    db_name = os.path.splitext(os.path.basename(pdf_path))[0]
    persist_directory = f"./{db_name}_rag_db"

    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"Creating a new RAG vector store for '{db_name}'...")
        try:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"Vector store created at '{persist_directory}'.")
        except Exception as e:
            print(f"Error creating vector store: {e}")
            print("Please ensure you have the required libraries and the PDF file.")
            return None
    else:
        print(f"Loading existing RAG vector store for '{db_name}' from '{persist_directory}'.")
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    llm = ChatOllama(model=LLM_MODEL)  # ,model_kwargs=GPU_CONFIG)
    #

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


# --- Helper Functions for Simulation (Acting as internal "tools" for the simulation tool) ---
def stream(name: str, temperature: float, pressure: float, chemicals_list: list, chemical_fraction: dict, flow: float):
    """Helper function to define the stream.
    chemical_fraction is actually the dictionary of total moles (mol/s) for each chemical."""
    mole_frac = {}
    total_moles_sum = sum(chemical_fraction.values())

    for chem in chemicals_list:
        if chem in chemical_fraction:
            # Calculate mole fraction
            mole_frac[chem] = chemical_fraction[chem] / total_moles_sum if total_moles_sum > 0 else 0
        else:
            mole_frac[chem] = 0

    stream_dict = {
        'Name': name,
        'Temperature (°C)': temperature,
        'Pressure (bar)': pressure,
        'Molar Flowrate (mol/s)': total_moles_sum,
        'Mole Fraction': mole_frac,
        'Total Moles (mol/s)': chemical_fraction
    }
    print('***' * 50)
    print(f"Stream '{name}' Data Generated")
    return stream_dict


@tool
def create_feed_stream_tool(temperature_C: float, pressure_bar: float, flowrate_kmol_h: float,list_of_chemical:list,
                            chemicals_mole_fraction: str) -> dict:
    """
    A tool to create the initial stream with specified parameters.
    Args:
        temperature_C: The temperature in degrees Celsius.
        pressure_bar: The pressure in bar.
        flowrate_kmol_h: The molar flowrate in kmol/h. (Will be converted to mol/s internally).
        list_of_chemical:list of all the chemicals used in the process
        chemicals_mole_fraction: A JSON string of the chemical components and their MOLE FRACTIONS, e.g., '{"benzene": 0.5, "ethylene": 0.5}'.
    Returns:
        The initial stream dictionary.
    """
    # Convert kmol/h to mol/s
    flowrate_mol_s = flowrate_kmol_h / 3.6

    # CORRECTED: Safely parse the JSON string to get the component mole fractions
    try:
        mole_fractions = json.loads(chemicals_mole_fraction)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in chemicals_mole_fraction: {e}")

    # Calculate total moles per second from mole fraction and total flowrate
    total_moles_per_s = {chem: frac * flowrate_mol_s for chem, frac in mole_fractions.items()}
    print("Initial stream component moles calculated.")

    return stream(
        name='Feed',
        temperature=temperature_C,
        pressure=pressure_bar,
        # Use the keys from the parsed dictionary as the list of chemicals
        chemicals_list=list_of_chemical,#list(mole_fractions.keys()),
        # Pass the calculated total moles (mol/s) for each chemical
        chemical_fraction=total_moles_per_s,
        flow=flowrate_mol_s
    )


def heater_tool(inlet_stream: dict, heater_type: str, condition: float, name=str):
    """Heater is a heating unit where the temperature of the inlet stream is increased
    inlet_stream = stream class is sent as
    heater_type=heater type based on data whether 'outlet_temperature' or 'temperature_difference',
    condition=value of outlet temperature or temperature difference
    name=Name of the outlet stream from the heater
    """
    outlet_stream = inlet_stream.copy()

    # Placeholder for a more complex heat calculation
    # energy = inlet_stream['Molar Flowrate (mol/s)'] * 4.31 * temperature_diff

    # The existing logic seems to assume Kelvin ('Temperature (K)') which is not in the stream dict,
    # but the prompt assumes Celsius ('Temperature (°C)').
    # For simplicity, we'll keep the current arithmetic but use Celsius for base.

    current_temp_C = inlet_stream['Temperature (°C)']

    if heater_type == 'outlet_temperature':
        outlet_temp = condition
        temperature_diff = condition - current_temp_C
    else:
        temperature_diff = condition
        outlet_temp = current_temp_C + condition

    energy = inlet_stream['Molar Flowrate (mol/s)'] * 4.31 * temperature_diff

    outlet_stream = stream(name, outlet_temp, inlet_stream['Pressure (bar)'],
                           list(inlet_stream['Total Moles (mol/s)'].keys()),
                           inlet_stream['Total Moles (mol/s)'], inlet_stream['Molar Flowrate (mol/s)'])
    print(outlet_stream)
    return outlet_stream


@tool
def pump_tool(inlet_stream: dict, pump_condition: str, value: float, name: str):
    """Pump is a pumping unit where the pressure of the inlet stream is increased
    inlet_stream = stream dict is sent
    pump_condition=pump condition based on data whether 'outlet_pressure' or 'pressure_difference' is given in the data,
    value=value of outlet temperature or temperature difference
    name=Name of the outlet stream from the heater
    """
    # The existing logic seems to assume Pascal ('Pressure (Pa)') which is not in the stream dict,
    # but the prompt assumes bar ('Pressure (bar)').
    current_pressure_bar = inlet_stream['Pressure (bar)']

    if pump_condition == 'outlet_pressure':
        outlet_pressure = value
        pressure_diff = value - current_pressure_bar
    else:
        pressure_diff = value
        outlet_pressure = current_pressure_bar + value

    energy = inlet_stream['Molar Flowrate (mol/s)'] * 4.31 * 100

    outlet_stream = stream(name, inlet_stream['Temperature (°C)'], outlet_pressure,
                           list(inlet_stream['Total Moles (mol/s)'].keys()), inlet_stream['Total Moles (mol/s)'],
                           inlet_stream['Molar Flowrate (mol/s)'])
    print(outlet_stream)
    return outlet_stream


@tool
def reactor_tool(inlet_stream: dict, Reaction_stoichiometry: dict, base_compound=str, conversion=float, name=str):
    """Reactor is a conversion reactpor
    stream = reactor inlet stream (containing temperature , pressure , mole flow , mole fraction and other detail)
    Reaction_stoichiometry = in a order structure chemicals involved in dictionary as key and the stoichimetry coefficient as value for reactant its negative and product its positive,
    base_compound=specify the name of the main reactant in the reaction
    conversion=conversion percentage of the reaction
    name= name of the outlet stream from reactor
    """

    print('Reaction data')
    print(inlet_stream, Reaction_stoichiometry, base_compound, conversion, name)
    inlet_moles = inlet_stream['Total Moles (mol/s)']

    benzene_in = inlet_moles.get('benzene', 0)
    ethylene_in = inlet_moles.get('ethylene', 0)

    # Reaction: Benzene + Ethylene -> Ethyl Benzene (1:1:1 stoichiometry)
    moles_benzene_reacted = benzene_in * (conversion / 100)

    # We assume enough ethylene is present to meet the benzene conversion target (based on prompt's definition)
    moles_ethylene_reacted = moles_benzene_reacted
    moles_ethylbenzene_produced = moles_benzene_reacted

    benzene_out = benzene_in - moles_benzene_reacted
    ethylene_out = ethylene_in - moles_ethylene_reacted
    # Get existing ethyl benzene (if any) and add produced amount
    ethylbenzene_out = inlet_moles.get('ethyl benzene', 0) + moles_ethylbenzene_produced

    new_moles = {
        'benzene': max(0, benzene_out),  # ensure non-negative moles
        'ethylene': max(0, ethylene_out),
        'ethyl benzene': ethylbenzene_out
    }

    # Preserve other components if they exist in the stream
    for chem, moles in inlet_moles.items():
        if chem not in new_moles:
            new_moles[chem] = moles

    # Use the stream function to calculate flowrate and mole fractions automatically
    return stream(
        name=name,
        temperature=inlet_stream['Temperature (°C)'],
        pressure=inlet_stream['Pressure (bar)'],
        chemicals_list=list(new_moles.keys()),
        chemical_fraction=new_moles,
        flow=sum(new_moles.values()))


@tool
def cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str) -> dict:
    """A tool for a cooling unit.
    Args:
        inlet_stream: The stream dictionary to be cooled.
        outlet_temp_C: The desired outlet temperature in °C.
        name: The name of the outlet stream.
    Returns:
        The updated stream dictionary.
    """
    # Re-run stream function to generate the new stream dictionary
    return stream(name, outlet_temp_C, inlet_stream['Pressure (bar)'], list(inlet_stream['Total Moles (mol/s)'].keys()),
                  inlet_stream['Total Moles (mol/s)'], inlet_stream['Molar Flowrate (mol/s)'])


@tool
def flash_tool(inlet_stream: dict, name: str) -> list[dict]:
    """A tool for a stream separator that splits a stream into liquid and vapor.
    This is a simplified model that performs a 50/50 split.
    Args:
        inlet_stream: The stream dictionary to be split.
        name: The name of the outlet stream.
    Returns:
        A list containing the vapor and liquid stream dictionaries.
    """
    inlet_moles = inlet_stream['Total Moles (mol/s)']
    inlet_flow = inlet_stream['Molar Flowrate (mol/s)']

    # 50/50 split of flow and total moles
    flow1 = inlet_flow * 0.5
    flow2 = inlet_flow * 0.5

    moles1 = {chem: mol * 0.5 for chem, mol in inlet_moles.items()}
    moles2 = {chem: mol * 0.5 for chem, mol in inlet_moles.items()}

    # Use the stream function to create the new streams
    stream1 = stream(
        name=f'{name} - Vapor',
        temperature=inlet_stream['Temperature (°C)'],
        pressure=inlet_stream['Pressure (bar)'],
        chemicals_list=list(inlet_moles.keys()),
        chemical_fraction=moles1,
        flow=flow1
    )

    stream2 = stream(
        name=f'{name} - Liquid',
        temperature=inlet_stream['Temperature (°C)'],
        pressure=inlet_stream['Pressure (bar)'],
        chemicals_list=list(inlet_moles.keys()),
        chemical_fraction=moles2,
        flow=flow2
    )

    return [stream1, stream2]


# --- Top-Level Tools (for the Main Agent) ---
@tool
def rag_enquiry(content: str) -> str:
    """This tool is for answering questions about the styrene production process as described in the paper.
    It retrieves information from the loaded document."""
    if RAG_CHAIN:
        return RAG_CHAIN.invoke(content)
    return "Error: RAG chain is not configured. Please check the PDF file path."


def parse_llm_function_call(response_content: str, tools_by_name: dict, current_stream: dict | None = None):
    """Parses the LLM's function call string into tool_name and arguments."""
    # Regex to capture tool_name and the argument string inside the parentheses
    match = re.match(r'(\w+)\((.*)\)$', response_content.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"LLM response is not in the required function call format: {response_content}")

    tool_name = match.group(1).strip()
    args_string = match.group(2).strip()

    tool_args = {}
    # Regex to find key=value pairs, handling string values with quotes
    # It must handle single-quoted strings (like JSON string)
    arg_pairs = re.findall(r'(\w+)\s*=\s*(.*?)(?:,\s*|\)$)', args_string + ',')

    for key, value_raw in arg_pairs:
        key = key.strip()
        value = value_raw.strip()

        # Remove surrounding quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        # Attempt to convert to float/int
        try:
            if '.' in value or 'e' in value or 'E' in value:
                tool_args[key] = float(value)
            else:
                tool_args[key] = int(value)
        except ValueError:
            # If conversion fails, treat as string (useful for JSON strings, names, and placeholders)
            tool_args[key] = value

    if tool_name not in tools_by_name:
        raise ValueError(f"Invalid tool name returned: {tool_name}")

    # Special handling for the inlet_stream placeholder in subsequent steps
    if current_stream and tool_args.get('inlet_stream') == 'the_current_stream_dict':
        tool_args['inlet_stream'] = current_stream

    return tool_name, tool_args


def run_process_simulation(initial_stream: dict, process_info: str, tools_by_name: dict) -> str:
    """
    Core simulation function that runs the AI agent in a loop over the process stages.

    Args:
        initial_stream: The starting stream dictionary.
        process_info: The step-by-step description of the process.
        tools_by_name: Dictionary of available simulation tools (raw functions).

    Returns:
        A formatted string containing the complete simulation output.
    """
    current_stream = initial_stream
    simulation_output = "---Dynamic Simulation Results---\n\n"

    simulation_output += f"Initial Feed Stream Created:\n{json.dumps(current_stream, indent=2)}\n\n"

    def dynamic_equipment_agent(step_description: str, current_stream: dict) -> tuple[dict, str]:
        """A sub-agent that selects and runs the correct equipment tool for a given step."""
        llm = ChatOllama(model=LLM_MODEL)  # ,model_kwargs=GPU_CONFIG)
        tool_names = ', '.join(tools_by_name.keys())

        # The prompt guides the LLM to choose the right tool and extract the parameters
        prompt_template = f"""
You are an expert at routing chemical engineering process steps to the correct equipment tool.
Based on the following process step description, select the single best tool to use and extract the arguments for it.

Available tools (only use these): {tool_names}.
- heater_tool(inlet_stream: dict, heater_type: str, condition: float, name: str): Heats a stream, using 'outlet_temperature' or 'temperature_difference' as heater_type.
- pump_tool(inlet_stream: dict, pump_condition: str, value: float, name: str): Pumps a stream, using 'outlet_pressure' or 'pressure_difference' as pump_condition.
- reactor_tool(inlet_stream: dict, Reaction_stoichiometry: dict, base_compound: str, conversion: float, name: str): Converts chemicals in a stream based on a given conversion rate (for the styrene process, this is conversion of benzene).
- cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Cools a stream to a specified temperature.
- flash_tool(inlet_stream: dict, name: str): Splits a stream into liquid and vapor components.

Current Stream Condition: {json.dumps(current_stream, indent=2)}

Process Step Description: {step_description}

Your response **MUST** be **ONLY** a single line containing the exact Python function call syntax.
For 'inlet_stream', always use the placeholder string "the_current_stream_dict".
Example: heater_tool(inlet_stream="the_current_stream_dict", heater_type="outlet_temperature", condition=150.0, name="Heated_Feed")

Response:
"""
        response = llm.invoke(prompt_template.strip()).content

        # Use the centralized parser
        tool_name, tool_args = parse_llm_function_call(response, tools_by_name, current_stream)

        # Execute the raw function (stored in tools_by_name) and get the result
        tool_result = tools_by_name[tool_name](**tool_args)

        # Prepare the output message
        if isinstance(tool_result, list):
            output_msg = f"STEP {i + 1} ({tool_name.replace('_tool', '').upper()}) Output:\n"
            next_stream = None
            for stream_data in tool_result:
                output_msg += f"Stream '{stream_data['Name']}':\n{json.dumps(stream_data, indent=2)}\n"
                # For separation units, we continue with the Liquid stream (often the main product line)
                if 'Liquid' in stream_data['Name']:
                    next_stream = stream_data

            if next_stream is None and tool_result:
                next_stream = tool_result[0]  # Fallback to the first stream
        else:
            output_msg = f"STEP {i + 1} ({tool_name.replace('_tool', '').upper()}) Output Stream:\n{json.dumps(tool_result, indent=2)}\n"
            next_stream = tool_result

        return next_stream, output_msg

    # --- Main Simulation Loop ---
    # Robust Step Extraction: Split by step markers and re-assemble content.
    steps_split = re.split(r'((?:Step \d+:|Step \d+\.)\s*)', process_info)

    processed_steps = []
    # Start from index 1 (the first step header) and iterate by 2 (to get content)
    for i in range(1, len(steps_split) - 1, 2):
        header = steps_split[i].strip()
        content = steps_split[i + 1].strip()
        # Only process if content exists and the header is a valid step marker
        if content and re.match(r'Step \d+[:.]', header):
            processed_steps.append(f"{header} {content}")

    steps = processed_steps

    if not steps:
        return "Could not retrieve valid, numbered process steps from the document to simulate. Please ensure the RAG result contains clear 'Step N:' sections."

    # Loop through each process step and dynamically execute the correct tool
    for i, step_content in enumerate(steps):
        step_description = step_content.strip()
        print(f"\nProcessing: '{step_description}'")

        try:
            # The agent runs the calculation and returns the next stream
            current_stream, step_output = dynamic_equipment_agent(step_description, current_stream)
            simulation_output += step_output + "\n"
        except Exception as e:
            simulation_output += f"\n--- ERROR during simulation step '{step_description}' ---\nError: {e}\n-----------------------------------\n"
            print(f"Error during simulation step '{step_description}': {e}")
            break

    print('---Simulation Tool: Simulation Complete---')
    return simulation_output


@tool
def simulation(content: str) -> str:
    """This tool is for simulating the styrene production process step-by-step.
    It orchestrates calls to internal helper functions based on a detailed process description from RAG."""
    print('---Simulation Tool: Starting Dynamic Process Simulation---')

    # 1. Information Collection
    # Get the complete, step-by-step process description
    print("Step 1a: Retrieving complete process info from RAG...")
    process_info = rag_enquiry(
        "Describe the complete styrene production process step-by-step, listing all equipment and their operating conditions.")

    print('process_info',process_info)

    # Get the initial feed stream data (raw text)
    print("Step 1b: Retrieving initial feed stream data from RAG...")
    feed_stream_info = rag_enquiry(
        "Extract only the key numerical and chemical data (temp in C, pressure in bar, flowrate in kmol/h, components, and mole fractions) for the initial feed stream of the styrene process. The mole fractions MUST be provided as a JSON string: eg = '{\"benzene\": 0.5, \"ethylene\": 0.5}'.")
    print('feed_stream_info',feed_stream_info)
    # 2. Initialization - Set up the initial stream

    # Tool for creation
    creation_tool = create_feed_stream_tool
    print('feed info',creation_tool)
    tools_by_name = {creation_tool.name: creation_tool.func}

    llm = ChatOllama(model=LLM_MODEL)  # ,model_kwargs=GPU_CONFIG)

    # Prompt the LLM to format the feed stream info into a function call
    creation_prompt = f"""
You are an expert at extracting chemical stream parameters from natural language and formatting them into a Python function call.
Your task is to parse the raw stream data provided below and format it into a call to the 'create_feed_stream_tool'.

Tool Signature: 
create_feed_stream_tool(temperature_C: float, pressure_bar: float, flowrate_kmol_h: float, chemicals_mole_fraction: str)

Raw Stream Data: {feed_stream_info}

Your response **MUST** be **ONLY** a single line containing the exact Python function call syntax.
Example: create_feed_stream_tool(temperature_C=95.0, pressure_bar=1.01325, flowrate_kmol_h=9.419, chemicals_mole_fraction='{{"benzene": 0.5, "ethylene": 0.5}}')

Response:
"""

    print("Step 1c: Generating function call for initial stream...")
    creation_response = llm.invoke(creation_prompt.strip()).content

    try:
        # Use the centralized parser
        tool_name, tool_args = parse_llm_function_call(creation_response, tools_by_name)

        # Execute the raw function (we know it's create_feed_stream_tool.func)
        current_stream = tools_by_name[tool_name](**tool_args)

    except Exception as e:
        return f"Error setting up initial stream: Failed to parse or execute function call for stream creation: {e}. Raw LLM output: {creation_response}"

    # 3. Define all Equipment Tools for the main loop
    equipment_tools = [heater_tool, pump_tool, reactor_tool, cooler_tool, flash_tool]
    # Store the raw function (.func) in the dictionary
    tools_by_name_for_loop = {tool.name: tool.func for tool in equipment_tools}

    # 4. Execution (calling the new core function)
    print("Step 2: Starting staged simulation loop via run_process_simulation...")
    return run_process_simulation(current_stream, process_info, tools_by_name_for_loop)


@tool
def other_discussion(content: str) -> str:
    """This function is run when the user enquires anything not related to chemical engineering, process used in the paper or simulation."""
    print('Other chat')
    return 'sorry i can support only to chemical questions'


@tool
def chemical_discussion(content: str) -> str:
    """This is a chemical discussion function if the user wants to enquire anything about chemicals and chemical engineering other than the details in the paper or related to the simulation."""
    discussion_llm = ChatOllama(model=LLM_MODEL)  # , model_kwargs=GPU_CONFIG)  #gpt-oss:20b
    print("Chemical discussion mode activated.")
    messages = [
        SystemMessage(content="You are a helpful and knowledgeable assistant specializing in chemical engineering."),
        HumanMessage(content=content)
    ]
    response = discussion_llm.invoke(messages)
    print(f"🤖 Assistant: {response.content}")
    return response.content


@tool
def process_enquiry_and_simulation(content: str) -> str:
    """This tool is for all questions related to the styrene process, including simulation and paper-based enquiries."""
    sub_llm = ChatOllama(model=LLM_MODEL)  # ,model_kwargs=GPU_CONFIG)
    sub_tool_descriptions = """
TOOLS:
- rag_enquiry: This tool is for answering questions about the styrene production process as described in the paper.
- simulation: This tool is for simulating the styrene production process.

RESPONSE FORMAT:
To use a tool, you must respond with ONLY the tool name in angle brackets, like <tool_name>. Do not add any other text or explanation. If a tool is relevant, DO NOT provide a direct answer.
"""
    sub_system_prompt = SystemMessage(content=f'''
You are a specialized assistant for the styrene production process. Your task is to correctly route the user's request to one of the available tools.
{sub_tool_descriptions}
''')
    supported_messages = [sub_system_prompt, HumanMessage(content=content)]
    sub_response = sub_llm.invoke(supported_messages)
    print('Selected agant 2',sub_response)
    sub_tool_call_match = re.search(r'<(\w+)>', sub_response.content)

    if sub_tool_call_match:
        tool_name = sub_tool_call_match.group(1)
        if tool_name == 'rag_enquiry':
            return rag_enquiry(content)
        elif tool_name == 'simulation':
            return simulation(content)
        else:
            return f"Error: {tool_name} is not a valid tool for this sub-agent."
    else:
        return sub_response.content


# print(process_enquiry_and_simulation('Simulate Styrene Production process'))

# Primary tools for the main agent
tools = [other_discussion, chemical_discussion, process_enquiry_and_simulation]
tools_by_name = {tool.name: tool for tool in tools}
llm = ChatOllama(model=LLM_MODEL)  # ,model_kwargs=GPU_CONFIG)


def Main_agent(state: AgentState) -> AgentState:
    print('---AGENT 1: INVOKED---')
    main_tool_descriptions = """
TOOLS:
- other_discussion: Use this tool for general topics not related to chemical engineering.
- chemical_discussion: Use this tool for general questions about chemicals and chemical engineering, not related to the styrene process.
- process_enquiry_and_simulation: Use this tool for all questions related to the styrene process, including simulations and enquiries from the paper.

RESPONSE FORMAT:
To use a tool, you must respond with ONLY the tool name in angle brackets, like <tool_name>. Do not add any other text or explanation. If a tool is relevant, DO NOT provide a direct answer.
"""
    system_prompt_content = f'''
    You are a chemical expert assistant. Your primary task is to correctly route the user's request to one of the available tools.
    {main_tool_descriptions}
    '''
    system_prompt = SystemMessage(content=system_prompt_content)
    supported_messages = []
    for message in state['messages']:
        if isinstance(message, (HumanMessage, AIMessage, SystemMessage)):
            supported_messages.append(message)
    all_messages = [system_prompt] + supported_messages
    response = llm.invoke(all_messages)
    print(f"LLM Response: {response.content}")
    tool_call_match = re.search(r'<(\w+)>', response.content)

    if tool_call_match:
        tool_name = tool_call_match.group(1)
        print(f"USING TOOL: {tool_name}")
        tool_call = {
            "id": str(uuid.uuid4()),
            "name": tool_name,
            "args": {"content": state['messages'][-1].content}
        }
        return {'messages': [AIMessage(content="", tool_calls=[tool_call])]}
    else:
        return {'messages': [response]}


def should_continue(state: AgentState) -> str:
    print('---SHOULD CONTINUE: INVOKED---')
    last_message = state['messages'][-1]
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        print('---SHOULD CONTINUE: ENDING TURN---')
        return "end"
    else:
        print('---SHOULD CONTINUE: MOVING TO TOOLS---')
        return "continue"


def print_messages(messages):
    """Function to print the messages in a more readable format"""
    if not messages:
        return
    for message in messages:
        if isinstance(message, ToolMessage):
            print(f"TOOL RESULT: {message.content}")
        elif isinstance(message, HumanMessage):
            print(f"USER: {message.content}")
        elif isinstance(message, SystemMessage):
            print(f"SYSTEM: {message.content}")
        else:
            print(f"ASSISTANT: {message.content}")


graph = StateGraph(AgentState)
graph.add_node('agent', Main_agent)
tool_node = ToolNode(tools=tools)
graph.add_node('tools', tool_node)
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


def run_document_agent():
    print("Welcome to the Chemical Expert Assistant!")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("--------------------------------------------------")
    print("To simulate the process, please ask for a simulation and provide the inlet stream data.")
    print(
        "Example prompt: 'Simulate the styrene production process. The inlet stream has a temperature of 25 °C, a pressure of 1 bar, and a flowrate of 100 mol/s. The chemicals involved are benzene and ethylene.'")
    print("--------------------------------------------------")

    messages = []

    while True:
        user_input = input('What would you like to do next? ')
        if user_input.lower() in ['exit', 'quit']:
            break

        messages.append(HumanMessage(content=user_input))

        result = app.invoke({'messages': messages})

        new_messages = result['messages'][len(messages):]
        print_messages(new_messages)

        messages = result['messages']


if __name__ == '__main__':
    if not os.path.exists(PDF_PATH):
        print(f"Error: The PDF file '{PDF_PATH}' was not found. Please place it in the same directory as the script.")
    else:
        run_document_agent()

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

ai_key = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'


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
    llm = ChatOllama(model=LLM_MODEL)

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
    """Helper function to define the stream."""
    mole_frac = {}
    total_moles_sum = sum(chemical_fraction.values())

    for chem in chemicals_list:
        if chem in chemical_fraction:
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
def create_feed_stream_tool(temperature_C: float, pressure_bar: float, flowrate_kmol_h: float,
                            chemicals_mole_fraction: str) -> dict:
    """
    A tool to create the initial stream with specified parameters.
    Args:
        temperature_C: The temperature in degrees Celsius.
        pressure_bar: The pressure in bar.
        flowrate_kmol_h: The molar flowrate in kmol/h. (Will be converted to mol/s internally).
        chemicals_mole_fraction: A JSON string of the chemical components and their mole fractions, e.g., '{"benzene": 0.5, "ethylene": 0.5}'.
    Returns:
        The initial stream dictionary.
    """
    try:
        # Convert kmol/h to mol/s
        flowrate_mol_s = flowrate_kmol_h / 3.6
        chemicals = json.loads(chemicals_mole_fraction)

        # Calculate moles per second from mole fraction and total flowrate
        total_moles_per_s = {chem: frac * flowrate_mol_s for chem, frac in chemicals.items()}

        return stream(
            name='Feed',
            temperature=temperature_C,
            pressure=pressure_bar,
            chemicals_list=list(chemicals.keys()),
            chemical_fraction=total_moles_per_s,
            flow=flowrate_mol_s
        )
    except Exception as e:
        print(f"Error creating stream from arguments: {e}. Returning default stream.")
        # Return a default stream in case of an error
        flow_mol_s = 2.616  # Default based on example calculation
        return stream(
            name='Feed',
            temperature=95.0,
            pressure=1.01325,
            chemicals_list=['benzene', 'ethylene', 'ethyl benzene'],
            chemical_fraction={'benzene': flow_mol_s * 0.5, 'ethylene': flow_mol_s * 0.5, 'ethyl benzene': 0},
            flow=flow_mol_s
        )


@tool
def heater_tool(inlet_stream: dict, outlet_temp_C: float, name: str) -> dict:
    """A tool for a heating unit where the temperature of the inlet stream is increased.
    Args:
        inlet_stream: The stream dictionary to be heated.
        outlet_temp_C: The desired outlet temperature in °C.
        name: The name of the outlet stream.
    Returns:
        The updated stream dictionary.
    """
    # Re-run stream function to generate the new stream dictionary
    return stream(name, outlet_temp_C, inlet_stream['Pressure (bar)'], list(inlet_stream['Total Moles (mol/s)'].keys()),
                  inlet_stream['Total Moles (mol/s)'], inlet_stream['Molar Flowrate (mol/s)'])


@tool
def pump_tool(inlet_stream: dict, outlet_pressure_bar: float, name: str) -> dict:
    """A tool for a pumping unit where the pressure of the inlet stream is increased.
    Args:
        inlet_stream: The stream dictionary to be pumped.
        outlet_pressure_bar: The desired outlet pressure in bar.
        name: The name of the outlet stream.
    Returns:
        The updated stream dictionary.
    """
    # Re-run stream function to generate the new stream dictionary
    return stream(name, inlet_stream['Temperature (°C)'], outlet_pressure_bar,
                  list(inlet_stream['Total Moles (mol/s)'].keys()), inlet_stream['Total Moles (mol/s)'],
                  inlet_stream['Molar Flowrate (mol/s)'])


@tool
def reactor_tool(inlet_stream: dict, conversion: float, name: str) -> dict:
    """A tool for a conversion reactor.
    Args:
        inlet_stream: The reactor inlet stream dictionary.
        conversion: The conversion percentage of the reaction based on benzene.
        name: The name of the outlet stream.
    Returns:
        The updated stream dictionary.
    """
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
    ethylbenzene_out = inlet_moles.get('ethyl benzene', 0) + moles_ethylbenzene_produced

    new_moles = {
        'benzene': max(0, benzene_out),  # ensure non-negative moles
        'ethylene': max(0, ethylene_out),
        'ethyl benzene': ethylbenzene_out
    }

    # Use the stream function to calculate flowrate and mole fractions automatically
    return stream(
        name=name,
        temperature=inlet_stream['Temperature (°C)'],
        pressure=inlet_stream['Pressure (bar)'],
        chemicals_list=list(new_moles.keys()),
        chemical_fraction=new_moles,
        flow=sum(new_moles.values())
    )


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
        llm = ChatOllama(model=LLM_MODEL, temperature=0.7)
        tool_names = ', '.join(tools_by_name.keys())

        # The prompt guides the LLM to choose the right tool and extract the parameters
        prompt_template = f"""
You are an expert at routing chemical engineering process steps to the correct equipment tool.
Based on the following process step description, select the single best tool to use and extract the arguments for it.

Available tools (only use these): {tool_names}.
- heater_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Heats a stream to a specified temperature.
- pump_tool(inlet_stream: dict, outlet_pressure_bar: float, name: str): Pumps a stream to a specified pressure.
- reactor_tool(inlet_stream: dict, conversion: float, name: str): Converts chemicals in a stream based on a given conversion rate (for the styrene process, this is conversion of benzene).
- cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Cools a stream to a specified temperature.
- flash_tool(inlet_stream: dict, name: str): Splits a stream into liquid and vapor components.

Current Stream Condition: {json.dumps(current_stream, indent=2)}

Process Step Description: {step_description}

Your response **MUST** be **ONLY** a single line containing the exact Python function call syntax.
For 'inlet_stream', always use the placeholder string "the_current_stream_dict".
Example: heater_tool(inlet_stream="the_current_stream_dict", outlet_temp_C=150.0, name="Heated_Feed")

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

    # Get the initial feed stream data (raw text)
    print("Step 1b: Retrieving initial feed stream data from RAG...")
    feed_stream_info = rag_enquiry(
        "Extract only the key numerical and chemical data (temp in C, pressure in bar, flowrate in kmol/h, components, and mole fractions) for the initial feed stream of the styrene process. Use a JSON string for the mole fractions: '{\"benzene\": 0.5, \"ethylene\": 0.5}'")

    # 2. Initialization - Set up the initial stream

    # Tool for creation
    creation_tool = create_feed_stream_tool
    tools_by_name = {creation_tool.name: creation_tool.func}

    llm = ChatOllama(model=LLM_MODEL, temperature=0.7)

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
    discussion_llm = ChatOllama(model=LLM_MODEL, temperature=0.7)
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
    sub_llm = ChatOllama(model=LLM_MODEL, temperature=0.7)
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


print(process_enquiry_and_simulation('Simulate Styrene Production process'))

import re
import json
import os
import uuid
from typing import TypedDict, Sequence, Annotated, Union, List, Dict
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

# LangGraph Imports (Crucial for the agent flow)
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

# --- API Key & Model Configuration ---
# NOTE: The API_KEY is provided as a placeholder. In a real environment, use environment variables.
API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'

# Define constants for RAG
PDF_PATH = 'The styrene production2.pdf'
gemini_model = "gemini-2.5-flash-lite"#"gemini-2.5-flash-lite"

# Initialize Google Generative AI components
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
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


# --- RAG Setup ---
def setup_rag_chain(pdf_path: str):
    """
    Sets up a RAG chain by loading a PDF, creating a ChromaDB vector store,
    and initializing the LangChain components.
    """
    db_name = os.path.splitext(os.path.basename(pdf_path))[0]
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
        print(f"Loading existing RAG vector store for '{db_name}' from '{persist_directory}'.")
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


# --- Pydantic Schema for Structured Stream Data Extraction ---
class StreamParameters(BaseModel):
    """Parameters for defining a chemical stream, typically extracted from a user's prompt."""
    temperature_C: float = Field(default=25.0, description="The temperature in degrees Celsius.")
    pressure_bar: float = Field(default=1.0, description="The pressure in bar.")
    flowrate_mol_s: float = Field(default=100.0, description="The molar flowrate in mol/s.")
    chemicals: Dict[str, float] = Field(default={"benzene": 0.5, "ethylene": 0.5, "ethyl benzene": 0},
                                        description="The chemical components and their mole fractions (e.g., {'benzene': 0.5, 'ethylene': 0.5}). Must sum to 1.0.")


# --- Helper Functions for Simulation (Acting as internal "tools" for the simulation tool) ---
def stream(name: str, temperature: float, pressure: float, chemicals_list: list, chemical_fraction: dict, flow: float):
    """Helper function to define the stream structure."""
    mole_frac = {}
    total_moles = flow if flow > 0 else sum(chemical_fraction.values())

    for chem in chemicals_list:
        if chem in chemical_fraction and total_moles > 0:
            mole_frac[chem] = chemical_fraction[chem] / total_moles
        else:
            mole_frac[chem] = 0

    stream_dict = {
        'Name': name,
        'Temperature (°C)': temperature,
        'Pressure (bar)': pressure,
        'Molar Flowrate (mol/s)': total_moles,
        'Mole Fraction': mole_frac,
        'Total Moles': chemical_fraction
    }
    print('*** Stream Data Generated ***')
    return stream_dict


# @tool
# def get_inlet_stream_tool(prompt: str) -> dict:
#     """
#     A tool to get the initial stream data from a user's prompt using an LLM and structured output.
#     Args:
#         prompt: The user's input containing the stream parameters.
#     Returns:
#         The initial stream dictionary.
#     """
#     # Use structured output for reliable parameter extraction
#     structured_llm = llm.with_structured_output(StreamParameters)
#
#     system_prompt = f"You are an expert at extracting chemical stream parameters from natural language. Parse the user's prompt and extract the required parameters for a chemical stream. If a value is missing, use a reasonable default defined in the schema."
#
#     try:
#         # response is now a Pydantic object
#         response: StreamParameters = structured_llm.invoke([
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=prompt)
#         ])
#
#         temp_C = response.temperature_C
#         pressure_bar = response.pressure_bar
#         flowrate_mol_s = response.flowrate_mol_s
#         chemicals = response.chemicals
#
#         # Determine if the LLM returned mole fractions or absolute moles
#         total_fraction = sum(chemicals.values())
#
#         if total_fraction > 0.9 and total_fraction < 1.1:
#             # Assume mole fractions were given, convert to total moles based on flowrate
#             total_moles = {chem: frac * flowrate_mol_s for chem, frac in chemicals.items()}
#             flow = flowrate_mol_s
#         else:
#             # Assume absolute moles were given, use them as is, and update flowrate
#             total_moles = chemicals
#             flow = sum(total_moles.values())
#
#         return stream(
#             name='Feed',
#             temperature=temp_C,
#             pressure=pressure_bar,
#             chemicals_list=list(total_moles.keys()),
#             chemical_fraction=total_moles,
#             flow=flow
#         )
#     except Exception as e:
#         print(f"Error parsing stream data from LLM response: {e}")
#         # Return a default stream in case of an error
#         return stream(
#             name='Feed',
#             temperature=25.0,
#             pressure=1.0,
#             chemicals_list=['benzene', 'ethylene', 'ethyl benzene'],
#             chemical_fraction={'benzene': 50.0, 'ethylene': 50.0, 'ethyl benzene': 0.0},
#             flow=100.0
#         )


@tool
def get_inlet_stream_tool(feed_temp:float, feed_pressure:float , list_of_chemicals:list, inlet_flowrate:float,inlet_composition:dict) -> dict:
    """
    A tool to get the initial stream data from a user's prompt using an LLM and structured output.
    Args:
        feed_temp:temperature of the inlet stream in C if the inlet temperature is not specified consider it as 25C,
        feed_pressure: pressure of the inlet stream in bar or atm . if the inlet pressure is not specified consider it as 1 bar ,
        list_of_chemicals: list of all the chemicals used in the process include inlet , outlet , catalyst and all other  in list format like ['benzene','toluene'],
        inlet_flowrate:total flowrate of the inlet stream in kmol/s , if the inlet flow is not specified consider it as 1  kmol/s,
        inlet_composition: mole fraction of all the chemicals in the inlet stream in dictionary format like {'benzene':0.5,'toluene':0.5},
    Returns:
        The initial stream dictionary.
    """
    # Use structured output for reliable parameter extraction
    # for i in list_of_chemicals:
    mole_fract={
        key: inlet_composition.get(key, 0)
        for key in list_of_chemicals
    }




    return stream(
        name='Feed',
        temperature=feed_temp,
        pressure=feed_pressure,
        chemicals_list=list_of_chemicals,
        chemical_fraction=mole_fract,
        flow=inlet_flowrate
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
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = name
    outlet_stream['Temperature (°C)'] = outlet_temp_C
    print(f"Heater Tool executed: {inlet_stream['Name']} -> {name} @ {outlet_temp_C}°C")
    return outlet_stream


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
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = name
    outlet_stream['Pressure (bar)'] = outlet_pressure_bar
    print(f"Pump Tool executed: {inlet_stream['Name']} -> {name} @ {outlet_pressure_bar} bar")
    return outlet_stream


@tool
def reactor_tool(inlet_stream: dict, conversion: float, name: str) -> dict:
    """A tool for a conversion reactor (Benzene + Ethylene -> Ethyl Benzene).
    Args:
        inlet_stream: The reactor inlet stream dictionary.
        conversion: The conversion percentage of the reaction based on benzene.
        name: The name of the outlet stream.
    Returns:
        The updated stream dictionary.
    """
    outlet_stream = inlet_stream.copy()
    inlet_moles = inlet_stream['Total Moles']

    # Simplified reaction: Benzene + Ethylene -> Ethyl Benzene
    benzene_in = inlet_moles.get('benzene', 0.0)
    ethylene_in = inlet_moles.get('ethylene', 0.0)
    ethylbenzene_in = inlet_moles.get('ethyl benzene', 0.0)

    # Conversion is based on Benzene (limiting reactant if 1:1)
    moles_benzene_reacted = benzene_in * (conversion / 100.0)

    # Stoichiometry 1:1:1
    moles_ethylene_reacted = moles_benzene_reacted
    moles_ethylbenzene_produced = moles_benzene_reacted

    # Account for limiting reactant: cannot consume more ethylene than available
    if moles_ethylene_reacted > ethylene_in:
        moles_ethylene_reacted = ethylene_in
        moles_benzene_reacted = ethylene_in  # reaction limited by ethylene
        moles_ethylbenzene_produced = ethylene_in

    benzene_out = benzene_in - moles_benzene_reacted
    ethylene_out = ethylene_in - moles_ethylene_reacted
    ethylbenzene_out = ethylbenzene_in + moles_ethylbenzene_produced

    new_moles = {
        'benzene': max(0, benzene_out),
        'ethylene': max(0, ethylene_out),
        'ethyl benzene': max(0, ethylbenzene_out)
    }

    # Include other chemicals that might be present but are inert
    for chem, moles in inlet_moles.items():
        if chem not in new_moles:
            new_moles[chem] = moles

    total_flow_out = sum(new_moles.values())

    outlet_stream['Total Moles'] = new_moles
    outlet_stream['Molar Flowrate (mol/s)'] = total_flow_out
    outlet_stream['Mole Fraction'] = {
        chem: moles / total_flow_out for chem, moles in new_moles.items() if total_flow_out > 0
    }
    outlet_stream['Name'] = name
    print(f"Reactor Tool executed: {inlet_stream['Name']} -> {name} with {conversion}% conversion on Benzene.")
    return outlet_stream


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
    outlet_stream = inlet_stream.copy()
    outlet_stream['Name'] = name
    outlet_stream['Temperature (°C)'] = outlet_temp_C
    print(f"Cooler Tool executed: {inlet_stream['Name']} -> {name} @ {outlet_temp_C}°C")
    return outlet_stream


@tool
def flash_tool(inlet_stream: dict, name: str) -> List[dict]:
    """A tool for a stream separator that splits a stream into liquid and vapor.
    This is a simplified model that performs a 50/50 split of the total flow, but uses density/volatility (approximate mole fraction) to influence the split.
    Args:
        inlet_stream: The stream dictionary to be split.
        name: The name of the outlet stream prefix.
    Returns:
        A list containing the vapor and liquid stream dictionaries.
    """
    total_flow = inlet_stream['Molar Flowrate (mol/s)']
    moles_in = inlet_stream['Total Moles']

    # Simplified separation logic: assume light components (Ethylene) prefer vapor, heavy (Ethyl Benzene) prefer liquid.
    # Benzene is intermediate.
    light_split_factor = 0.8  # 80% of light component goes to vapor
    heavy_split_factor = 0.2  # 20% of heavy component goes to vapor

    moles_vapor = {}
    moles_liquid = {}

    for chem, moles in moles_in.items():
        if 'ethylene' in chem.lower():
            vapor_frac = light_split_factor
        elif 'ethyl benzene' in chem.lower():
            vapor_frac = heavy_split_factor
        else:  # Default for Benzene and others
            vapor_frac = 0.5

        moles_vapor[chem] = moles * vapor_frac
        moles_liquid[chem] = moles * (1.0 - vapor_frac)

    total_vapor_flow = sum(moles_vapor.values())
    total_liquid_flow = sum(moles_liquid.values())

    # Create Vapor Stream
    vapor_stream = inlet_stream.copy()
    vapor_stream['Name'] = f'{name} - Vapor'
    vapor_stream['Total Moles'] = moles_vapor
    vapor_stream['Molar Flowrate (mol/s)'] = total_vapor_flow
    vapor_stream['Mole Fraction'] = {
        chem: moles / total_vapor_flow for chem, moles in moles_vapor.items() if total_vapor_flow > 0
    }

    # Create Liquid Stream
    liquid_stream = inlet_stream.copy()
    liquid_stream['Name'] = f'{name} - Liquid'
    liquid_stream['Total Moles'] = moles_liquid
    liquid_stream['Molar Flowrate (mol/s)'] = total_liquid_flow
    liquid_stream['Mole Fraction'] = {
        chem: moles / total_liquid_flow for chem, moles in moles_liquid.items() if total_liquid_flow > 0
    }

    print(
        f"Flash Tool executed: {inlet_stream['Name']} split into Vapor ({total_vapor_flow:.2f} mol/s) and Liquid ({total_liquid_flow:.2f} mol/s).")
    return [vapor_stream, liquid_stream]


# --- Top-Level Tools (for the Main Agent) ---
@tool
def rag_enquiry(content: str) -> str:
    """This tool is for answering questions about the styrene production process as described in the paper.
    It retrieves information from the loaded document."""
    if RAG_CHAIN:
        print("RAG Enquiry Tool activated.")
        return RAG_CHAIN.invoke(content)
    return "Error: RAG chain is not configured. Please check the PDF file path."


# Pydantic schema for process steps structuring
class ProcessStep(BaseModel):
    step_description: str = Field(
        description="A concise description of the process step, including equipment and conditions.")
    outlet_stream_name: str = Field(
        description="The predicted, descriptive name for the main outlet stream of this equipment unit (e.g., Reactor_Effluent, Cooler_Outlet, Flash_Vapor).")

# Pydantic wrapper for the list of process steps (FIX)
class ProcessStepsList(BaseModel):
    """A list container for sequential chemical process steps."""
    steps: List[ProcessStep] = Field(description="The list of process steps to be executed sequentially.")


# Use Union to allow single stream or list of streams from a tool
ToolResult = Union[dict, List[dict]]


def dynamic_equipment_agent(step_description: str, current_stream: dict, outlet_stream_name: str,
                            tools_by_name: dict) -> tuple[ToolResult, str]:
    """A sub-agent that selects and runs the correct equipment tool for a given step."""

    # Pydantic schema for the tool call
    class ToolCall(BaseModel):
        tool_name: str = Field(description="The name of the tool to be executed.")
        tool_args: dict = Field(
            description="A dictionary of arguments for the tool, including outlet_temp_C or outlet_pressure_bar and always setting 'inlet_stream' to the string 'the_current_stream_dict' and 'name' to the required outlet_stream_name.")

    # Use structured output for reliable tool-calling argument extraction
    structured_llm = llm.with_structured_output(ToolCall)
    tool_names = ', '.join(tools_by_name.keys())

    # The prompt guides the LLM to choose the right tool and extract the parameters
    prompt_template = f"""
You are an expert at routing chemical engineering process steps to the correct equipment tool.
Based on the following process step description, select the single best tool to use and extract the arguments for it.
The outlet stream name for this step MUST be: "{outlet_stream_name}".
Your response MUST be a single JSON object that conforms to the ToolCall schema.

Available tools: {tool_names}.
- heater_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Heats a stream to a specified temperature.
- pump_tool(inlet_stream: dict, outlet_pressure_bar: float, name: str): Pumps a stream to a specified pressure.
- reactor_tool(inlet_stream: dict, conversion: float, name: str): Converts chemicals in a stream based on a given conversion rate of Benzene (e.g., conversion=90).
- cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Cools a stream to a specified temperature.
- flash_tool(inlet_stream: dict, name: str): Splits a stream into liquid and vapor components.

Process Step Description: {step_description}

Remember to set 'inlet_stream' to 'the_current_stream_dict' and 'name' to '{outlet_stream_name}' in the tool_args.
"""

    try:
        # FIX: Correctly invoke the LLM with the prompt for structured output
        tool_call_response: ToolCall = structured_llm.invoke([HumanMessage(content=prompt_template.strip())])

        tool_name = tool_call_response.tool_name
        tool_args = tool_call_response.tool_args

        # Replace the placeholder with the actual stream object
        if tool_args.get('inlet_stream') == 'the_current_stream_dict':
            tool_args['inlet_stream'] = current_stream

        # Execute the tool and get the result
        tool_result = tools_by_name[tool_name](**tool_args)

        # Prepare the output message
        if isinstance(tool_result, list):
            output_msg = f"{step_description} - Output:\n"
            for stream_data in tool_result:
                output_msg += f"Stream '{stream_data['Name']}':\n{json.dumps(stream_data, indent=2)}\n"
            # For the simulation continuation, default to the liquid stream if it's a flash/separator
            next_stream = [s for s in tool_result if 'liquid' in s['Name'].lower()]
            next_stream = next_stream[0] if next_stream else tool_result[0]

        else:
            output_msg = f"{step_description} - Output Stream '{tool_result['Name']}':\n{json.dumps(tool_result, indent=2)}\n"
            next_stream = tool_result

        return next_stream, output_msg

    except Exception as e:
        return current_stream, f"Error during tool selection/execution for step '{step_description}': {e}"


@tool
def simulation(content: str) -> str:
    """This tool is for simulating the styrene production process step-by-step.
    It orchestrates calls to internal helper functions based on a detailed process description from RAG."""
    print('---Simulation Tool: Starting Dynamic Process Simulation---')

    simulation_output = "---Dynamic Simulation Results---\n\n"

    # 1. Retrieve detailed process steps from RAG
    print("Step 1: Retrieving complete process info from RAG...")
    process_info = rag_enquiry(
        "Describe the complete styrene production process step-by-step, including all initial stream conditions and equipment details.")

    print('___'*100)
    print('process_info',process_info)

    updated_response = llm.invoke([
                    SystemMessage(content=f'''you are a chemical expert , check and make any changes needed in the process by user and return the process in steps where each equipment is sent as one step like step 1, step 2 and goes on ,
        Follow the conditions like if the stream is consideres as preheater then consider that the inlet stream is at 20C and a heater is used for pre heating and changes the step name to Heater ,
        similary when a stream is pre pressurised or pre prd consider the inlet pressure is 1 bar and a pump is used to pressure the stream and change the step name to Pump'''),
                    HumanMessage(content=f'process infor ={process_info}. and conversations is = {content}')
                ])
    print('---' * 100)
    print('updated_response =', updated_response)

    print("Step 2: Structuring process steps and predicting stream names.")

    # FIX: Use the Pydantic wrapper model for the list output
    structured_llm = llm.with_structured_output(ProcessStepsList)

    structuring_prompt = f"""
    You are an expert chemical process analyst.
    Your task is to take the detailed process description from the RAG and break it down into a list of sequential, executable steps, one step per equipment unit.
    The output MUST be a JSON object containing a 'steps' key which is a list of ProcessStep objects.
    For each step, provide a brief description and a clear, descriptive name for the *main* outlet stream of that equipment unit.

    Detailed Process Description from RAG:
    ---
    {process_info}
    ---
    """
    print('**'*100)
    print('structuring_prompt',structuring_prompt)

    try:
        # The response content will be a Pydantic object (ProcessStepsList)
        structured_steps_list: ProcessStepsList = structured_llm.invoke([HumanMessage(content=structuring_prompt)])
        structured_steps = structured_steps_list.steps # Extract the list
    except Exception as e:
        print(f"Error parsing structured steps from LLM: {e}")
        return "Simulation failed: Could not parse the process steps from the RAG output reliably for execution."

    # 3. Get the initial feed stream from the user's prompt (or default)
    print("Step 3: Getting initial feed stream data.")
    try:
        current_stream = get_inlet_stream_tool.func(prompt=content)
    except Exception as e:
        return f"Error extracting initial stream data from user query: {e}"

    simulation_output += f"Initial Feed Stream Created:\n{json.dumps(current_stream, indent=2)}\n\n"

    # 4. Main simulation loop
    equipment_tools = [heater_tool, pump_tool, reactor_tool, cooler_tool, flash_tool]
    tools_by_name = {tool_func.name: tool_func for tool_func in equipment_tools}

    for i, step_data in enumerate(structured_steps):
        step_description = f"Step {i + 1}: {step_data.step_description}"
        outlet_stream_name = step_data.outlet_stream_name
        print(f"Processing: '{step_description}' -> Out: {outlet_stream_name}")

        try:
            # Call the sub-agent to select and execute the correct tool
            current_stream, step_output = dynamic_equipment_agent(
                step_description,
                current_stream,
                outlet_stream_name,
                tools_by_name
            )
            simulation_output += step_output + "\n"
        except Exception as e:
            simulation_output += f"Error during simulation step '{step_description}': {e}\n"
            print(f"Error during simulation step '{step_description}': {e}")
            break

    print('---Simulation Tool: Simulation Complete---')
    return simulation_output


@tool
def other_discussion(content: str) -> str:
    """This function is run when the user enquires anything not related to chemical engineering, process used in the paper or simulation."""
    print('Other chat')
    return 'Sorry, I can only support questions related to chemical engineering, the styrene process, or simulation.'


@tool
def chemical_discussion(content: str) -> str:
    """This is a chemical discussion function if the user wants to enquire anything about chemicals and chemical engineering other than the details in the paper or related to the simulation."""
    discussion_llm = llm
    print("Chemical discussion mode activated.")
    messages = [
        SystemMessage(
            content="You are a helpful and knowledgeable assistant specializing in chemical engineering. Answer the user's question clearly."),
        HumanMessage(content=content)
    ]
    response = discussion_llm.invoke(messages)
    return response.content


@tool
def process_enquiry_and_simulation(content: str) -> str:
    """This tool is for all questions related to the styrene process, including simulation and paper-based enquiries."""

    # Define a sub-agent to route between RAG and Simulation
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
    sub_response = llm.invoke(supported_messages)

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
        # If the sub-agent doesn't call a tool, it provides a direct answer
        return sub_response.content


# --- LangGraph Agent Setup ---

# Primary tools for the main agent
tools = [other_discussion, chemical_discussion, process_enquiry_and_simulation]
tools_by_name = {tool.name: tool for tool in tools}


def agent1(state: AgentState) -> AgentState:
    print('---AGENT 1: INVOKED (Router)---')
    main_tool_descriptions = """
TOOLS:
- other_discussion: Use this tool for general topics not related to chemical engineering or the process.
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

    # Only pass the system prompt and the latest user message for routing
    latest_user_message = state['messages'][-1]
    all_messages = [system_prompt, latest_user_message]

    response = llm.invoke(all_messages)
    print(f"LLM Router Response: {response.content}")

    tool_call_match = re.search(r'<(\w+)>', response.content)

    if tool_call_match:
        tool_name = tool_call_match.group(1)
        print(f"USING TOOL: {tool_name}")
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
    print('---SHOULD CONTINUE: INVOKED (Conditional Edge)---')
    last_message = state['messages'][-1]

    # If the last message is an AIMessage with tool_calls, it means a tool needs to be run.
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print('---SHOULD CONTINUE: Moving to TOOLS---')
        return "continue"
    else:
        # The agent responded directly, or the tool has already run and the flow ended.
        print('---SHOULD CONTINUE: ENDING TURN---')
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


def run_document_agent():
    print("Welcome to the Chemical Expert Assistant (Styrene Process)!")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("--------------------------------------------------")
    print("Example RAG prompt: 'What is the main reactor type used in the styrene production process?'")
    print(
        "Example Simulation prompt: 'Simulate the process. The feed is 100 mol/s of 60% benzene and 40% ethylene at 25 °C and 1 bar.'")
    print("--------------------------------------------------")

    messages = []

    while True:
        try:
            user_input = input('>> What would you like to do next? ')
        except EOFError:
            break

        if user_input.lower() in ['exit', 'quit']:
            break

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


if __name__ == '__main__':
    # Initial check if RAG setup succeeded
    if RAG_CHAIN is None:
        print("\nFATAL ERROR: RAG chain initialization failed. Check console for details (e.g., missing PDF file).\n")
    else:
        run_document_agent()

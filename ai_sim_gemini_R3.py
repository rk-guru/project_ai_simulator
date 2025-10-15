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
# from number_extractor import extract_integer_from_text

# LangGraph Imports (Crucial for the agent flow)
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode


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
    max_retries=2,)


# --- State Management ---
def add_messages(left: list, right: list):
    """Function to add messages for state management"""
    return left + right


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# # --- RAG Setup ---
# # Define constants for RAG
# # IMPORTANT: You must place the 'The styrene production.pdf' file in the same directory as this script.
# PDF_PATH = 'The styrene production.pdf'
# # NOTE: Ensure you have Ollama running and have pulled these models:
# # For the main LLM: 'ollama pull llama3.1:latest'
# # For embeddings: 'ollama pull mxbai-embed-large'
# LLM_MODEL = "llama3.1:latest" #"deepseek-r1:14b"#
# EMBEDDING_MODEL = "mxbai-embed-large"


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


# --- Helper Functions for Simulation (Acting as internal "tools" for the simulation tool) ---
def stream(name: str, temperature: float, pressure: float, chemicals_list: list, chemical_fraction: dict, flow: float):
    """Helper function to define the stream."""
    mole_frac = {}
    total_moles = sum(chemical_fraction.values()) if not flow else flow

    for chem in chemicals_list:
        if chem in chemical_fraction:
            mole_frac[chem] = chemical_fraction[chem] / total_moles if total_moles > 0 else 0
        else:
            mole_frac[chem] = 0

    stream_dict = {
        'Name': name,
        'Temperature (°C)': temperature,
        'Pressure (bar)': pressure,
        'Molar Flowrate (mol/s)': flow,
        'Mole Fraction': mole_frac,
        'Total Moles': chemical_fraction
    }
    print('***'*100)
    print('Stream Data',stream_dict)
    return stream_dict



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
    return outlet_stream


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
    outlet_stream = inlet_stream.copy()
    inlet_moles = inlet_stream['Total Moles']

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

    outlet_stream['Total Moles'] = new_moles
    outlet_stream['Molar Flowrate (mol/s)'] = total_flow_out
    outlet_stream['Mole Fraction'] = {
        chem: moles / total_flow_out for chem, moles in new_moles.items() if total_flow_out > 0
    }
    outlet_stream['Name'] = name
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
    return outlet_stream


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
    outlet_stream1 = inlet_stream.copy()
    outlet_stream2 = inlet_stream.copy()

    outlet_stream1['Molar Flowrate (mol/s)'] *= 0.5
    outlet_stream2['Molar Flowrate (mol/s)'] *= 0.5

    outlet_stream1['Name'] = f'{name} - Vapor'
    outlet_stream2['Name'] = f'{name} - Liquid'

    return [outlet_stream1, outlet_stream2]


# --- Top-Level Tools (for the Main Agent) ---
@tool
def rag_enquiry(content: str) -> str:
    """This tool is for answering questions about the styrene production process as described in the paper.
    It retrieves information from the loaded document."""
    if RAG_CHAIN:
        return RAG_CHAIN.invoke(content)
    return "Error: RAG chain is not configured. Please check the PDF file path."


@tool
def simulation(content: str) -> str:
    """This tool is for simulating the styrene production process step-by-step.
    It orchestrates calls to internal helper functions based on a detailed process description from RAG."""
    print('---Simulation Tool: Starting Dynamic Process Simulation---')

    simulation_output = "---Dynamic Simulation Results---\n\n"

    # Step 1: Use a tool to get the inlet stream data from the user query
    try:
        print("Step 1: Getting inlet stream data using a tool...")
        # FIX: Directly call the underlying function to avoid the keyword argument error.
        # process_info = RAG_CHAIN.invoke(
        #     "Describe the complete styrene production process step-by-step, including all initial stream conditions and equipment details.")

        'process info working'
        process_info = RAG_CHAIN.invoke(
            "Consider you are a chemical enginner and you are planning to simulate the styrene process . collect all the information about the process with all the chemicals and equipment")
        print('=='*100)
        updated_response = llm.invoke([
            SystemMessage(content=f'''you are a chemical expert , check and make any changes needed in the process by user and return the process in steps where each equipment is sent as one step like step 1, step 2 and goes on ,
Follow the conditions like if the stream is consideres as preheater then consider that the inlet stream is at 20C and a heater is used for pre heating and changes the step name to Heater ,
similary when a stream is pre pressurised or pre prd consider the inlet pressure is 1 bar and a pump is used to pressure the stream and change the step name to Pump'''),
            HumanMessage(content=f'process information  ={process_info}. and conversations is = {content}')
        ])
        print('---'*100)
        number_of_stages = llm.invoke([
            SystemMessage(content='Go through the data follows and give the number of steps involed in the process , return only the number'),
            HumanMessage(content=f' {updated_response}')
        ])
        print('///' * 100)
        equipment_and_stream_dict=llm.invoke([SystemMessage(content = '''consider you are a chemical engineer and you need to name the equipment and the outlet streams
        the equipment names are in the followinf order with number for like for multiple heater name should be Heater_1, Heater_2 . similarly for other equyipments
        for the outlet stream the the name should be equipment name followed by outlet like Heater_1_outlet , pump_1_outlet.
        for distillation column and Flash it have two outlets the name should be Distillation_1_liquid ,Distillation_1_vapor and Flash_1_liquid and Flash_1_vapor 
        
        the final response should be in the dictionary structure with equipment name as key and list of the outlet stream as value like {
        'Heater_1' : [Heater_1_outlet],
        'Distillation_1':[Distillation_1_liquid ,Distillation_1_vapor]
        }
        '''),HumanMessage(content=updated_response.content)])
        print('+++' * 100)
        feed_stream=llm.invoke([
            SystemMessage(
                content='''you are a chemical simulation expert ,collect the feed stream information , list of all chemicals used in the process , list of chemicals in the inlet stream ,
                chemical composition of the inlet stream , inlet temperature , inlet pressure and inlet flowrate '''),
            HumanMessage(content=updated_response.content)
        ])
        print('---' * 100)
        print('feed stream,',feed_stream.content)
        current_stream = get_inlet_stream_tool.func(prompt=feed_stream.content)
        print('*+*' * 100)
        print('current_stream,',current_stream )
        print('===' * 100)
        simulation_output += f"Initial Feed Stream Created:\n{json.dumps(current_stream, indent=2)}\n\n"

    except Exception as e:
        return f"Error getting initial stream data from your query. Error: {e}"

    # Step 2: Use a sub-LLM agent to dynamically call equipment tools
    process_info = rag_enquiry(
        "Describe the complete styrene production process step-by-step, including all initial stream conditions and equipment details.")

    equipment_tools = [heater_tool, pump_tool, reactor_tool, cooler_tool, flash_tool]
    tools_by_name = {tool.name: tool for tool in equipment_tools}

    def dynamic_equipment_agent(step_description: str, current_stream: dict) -> tuple[dict, str]:
        """A sub-agent that selects and runs the correct equipment tool for a given step."""
        # llm = ChatOllama(model=LLM_MODEL, temperature=0.7)
        tool_names = ', '.join(tools_by_name.keys())

        # The prompt guides the LLM to choose the right tool and extract the parameters
        prompt_template = f"""
You are an expert at routing chemical engineering process steps to the correct equipment tool.
Based on the following process step description, select the single best tool to use and extract the arguments for it.
Your response must be a single JSON object.

Available tools: {tool_names}.
- heater_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Heats a stream to a specified temperature.
- pump_tool(inlet_stream: dict, outlet_pressure_bar: float, name: str): Pumps a stream to a specified pressure.
- reactor_tool(inlet_stream: dict, conversion: float, name: str): Converts chemicals in a stream based on a given conversion rate.
- cooler_tool(inlet_stream: dict, outlet_temp_C: float, name: str): Cools a stream to a specified temperature.
- flash_tool(inlet_stream: dict, name: str): Splits a stream into liquid and vapor components.

Process Step Description: {step_description}

JSON Response Format:
{{
    "tool_name": "name_of_the_tool",
    "tool_args": {{
        "inlet_stream": "the_current_stream_dict",
        "name": "a_descriptive_name_for_the_outlet_stream",
        "arg1_name": value1,
        "arg2_name": value2
    }}
}}
Note: 'inlet_stream' should always be present with the value "the_current_stream_dict". The other arguments depend on the tool.
"""
        response = llm.invoke(prompt_template.strip())
        tool_call = json.loads(response.content)
        tool_name = tool_call['tool_name']
        tool_args = tool_call['tool_args']

        # Replace the placeholder with the actual stream object
        if tool_args.get('inlet_stream') == 'the_current_stream_dict':
            tool_args['inlet_stream'] = current_stream

        # Execute the tool and get the result
        tool_result = tools_by_name[tool_name](**tool_args)

        # Prepare the output message
        if isinstance(tool_result, list):
            output_msg = f"{step_description} - Output:\n"
            for stream in tool_result:
                output_msg += f"Stream '{stream['Name']}':\n{json.dumps(stream, indent=2)}\n"
            # We continue the simulation with the liquid stream for this example
            next_stream = [s for s in tool_result if 'Liquid' in s['Name']][0]
        else:
            output_msg = f"{step_description} - Output Stream:\n{json.dumps(tool_result, indent=2)}\n"
            next_stream = tool_result

        return next_stream, output_msg

    # Main simulation loop
    print("Step 2: Retrieving complete process info from RAG...")
    process_info = rag_enquiry(
        "Describe the complete styrene production process step-by-step, listing all equipment and their operating conditions.")
    steps = re.split(r'\d+\.', process_info)[1:]

    if not steps:
        return "Could not retrieve a valid process description from the document to simulate."

    # Loop through each process step and dynamically execute the correct tool
    for i, step in enumerate(steps):
        step_description = f"Step {i + 1}: {step.strip()}"
        print(f"Processing: '{step_description}'")

        try:
            current_stream, step_output = dynamic_equipment_agent(step_description, current_stream)
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
    return 'sorry i can support only to chemical questions'


@tool
def chemical_discussion(content: str) -> str:
    """This is a chemical discussion function if the user wants to enquire anything about chemicals and chemical engineering other than the details in the paper or related to the simulation."""
    discussion_llm = llm #ChatOllama(model=LLM_MODEL, temperature=0.7)
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
    sub_llm = llm #ChatOllama(model=LLM_MODEL, temperature=0.7)
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

# process_enquiry_and_simulation('Simulate Styrene Production process')
#Primary tools for the main agent
tools = [other_discussion, chemical_discussion, process_enquiry_and_simulation]
tools_by_name = {tool.name: tool for tool in tools}
llm = ChatOllama(model=LLM_MODEL, temperature=0.7)


def agent1(state: AgentState) -> AgentState:
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
graph.add_node('agent', agent1)
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

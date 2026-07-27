import os
import uuid
import json
from typing import List, Dict, Any, Optional
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import HumanMessage, AIMessage , SystemMessage
from langchain.tools import tool
from typing import List, Dict, Any
from langchain_core.output_parsers import JsonOutputParser
from ai_tools import process_project_rag, retrieve_rag_documents, DUMMY_FLOW_DIAGRAM_DATA
import pandas as pd
from prompt_db import deep_agent_prompt

async def generate_deep_agent_response(api_key: str, model_name: str, project_id: str, chat: str, chat_history: List[Dict[str, Any]] = None):
    """
    Function: Deep Agent Responder
    Orchestrates the AI response using the project's RAG data from ai_tools.
    """
    # Shared backend for the agent and its tools in this session
    backend = StateBackend()
    print("project_id",project_id)

    # Tools list
    tools = []

    # The RAG tool uses retrieve_rag_documents from ai_tools
    @tool(parse_docstring=True)
    def search_project_files(query: str) -> str:
        """this tool is a rag data extraction tool where the user query or the required information is passed to the rag db

        Args:
            query: Natural language search query.

        Returns:
            retrieved chunks data is returned
        """
        try:
            retrieved_docs = retrieve_rag_documents(api_key, project_id, query)
            print("retrieved_docs",retrieved_docs)
            if not retrieved_docs:
                return "No relevant information found in uploaded files."
        except:
            return "No relevant information found in uploaded files."
        return retrieved_docs#f"Saved {len(saved_paths)} chunks:\n" + "\n".join(saved_paths)

    @tool#(parse_docstring=True)
    def compounds_list() -> list:
        """this tool will return the list of all chemicals available in the db
        which can be used in the simualtions

        Returns:
            list of all chemicals available in the db
            """
        data = pd.read_csv("Open_source_db2.csv")
        return (data.iloc[:,0]).tolist()

    @tool#(parse_docstring=True)
    def get_flow_diagram() -> str:
        """This tool fetches the current flow diagram of the process.
        It returns a list of equipment with their IDs, outlets, and parameters.

        Returns:
            A JSON string representing the flow diagram.
        """
        from ai_tools import get_flow_diagram_from_db
        diagram_data = get_flow_diagram_from_db(project_id)
        print("getting data from flowdiagram",diagram_data)
        return str(json.dumps(diagram_data, indent=2))

    @tool(parse_docstring=True)
    def get_simulation_results() -> str:
        """This tool fetches the latest simulation results table for the current project.
        It returns the calculation results (parameters, values, status) in JSON format.

        Returns:
            A JSON string containing the simulation results table data.
        """
        from ai_tools import get_simulation_results_from_db
        results_data = get_simulation_results_from_db(project_id)
        print("getting simulation results", results_data)
        return str(json.dumps(results_data, indent=2))

    # @tool(parse_docstring=True)
    # def get_pfd_structure(process_data: str) -> str:

    @tool(parse_docstring=True)
    def get_pfd_structure(process_data: str) -> str:
        """Generates the JSON structure required to build a Process Flow Diagram (PFD).

        This tool should be used when the user explicitly requests to generate a PFD
        for a given process.

        Args:
            process_data: The complete set of aggregated input data from the chat,
                RAG, and other sources needed to generate the PFD. This must include
                a list of all chemicals used, all equipment involved, and step-by-step
                instructions containing specific equipment conditions and also specify
                the chemicals used in the process with the composition of each stream
                in mole fraction or flowrate for each stream. Ensure all
                provided data originates from validated sources. Missing or
                unspecified values can be omitted.

        Returns:
            A JSON string representing the flow diagram.
        """
        from equipment_reference import EQUIPMENT_FRONTEND_SCHEMA_JSON
        from prompt_db import flowdiagram_prompt
        print("process_data",process_data)
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.7,
        )
        system=SystemMessage(content=flowdiagram_prompt(str(EQUIPMENT_FRONTEND_SCHEMA_JSON)))
        human=HumanMessage(content=process_data)
        messages=[system,human]

        # parser = JsonOutputParser(pydantic_object=List[Dict[str, Any]])
        # json_string=model.invoke({"messages": messages})
        json_string = model.invoke(messages)
        print("json_string.content",json_string.content)
        # chain = model | parser
        # list_of_dicts = chain.invoke({"messages": messages})
        # print(list_of_dicts)
        return json_string.content


    tools=[search_project_files , compounds_list, get_flow_diagram, get_simulation_results, get_pfd_structure]


    # RAG Status
    from ai_tools import get_rag_dir
    rag_path = get_rag_dir(project_id)
    rag_exists = os.path.exists(rag_path) and os.listdir(rag_path)

    # Define the Analyst Subagent (from ref_script)
    chunk_analyst_subagent = {
        "name": "chunk-analyst",
        "description": "Analyze one retrieved project file chunk. Extract facts and return a concise summary.",
        "system_prompt": "You analyze retrieved project file chunks. Extract facts and return a concise summary under 300 words with key details and source.",
    }

    if rag_exists:
        instructions = (
            "# Project Files Q&A workflow\n"
            "Answer questions using the indexed project files.\n"
            "1. **Plan**: Use write_todos to break complex questions into focused search queries.\n"
            "2. **Search**: Call search_project_files with a query .\n"
            "3. **Analyze**: Delegate each chunk file to the chunk-analyst subagent with task().\n"
            "for question check if the data is already present in the rag information"
            "Do not answer from memory when file evidence is required. Search first."
        )
    else:
        instructions = "You are a helpful AI assistant. No project files have been uploaded, so please answer based on your general knowledge."

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.7,
    )

    agent = create_deep_agent(
        model,
        tools=tools,
        backend=backend,
        system_prompt=deep_agent_prompt,#instructions,
        subagents=[chunk_analyst_subagent] if rag_exists else [],
    )

    # Prepare messages
    messages = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.get('sender') == 'user' else "ai"
            content = msg.get('text', '')
            messages.append(HumanMessage(content=content) if role == 'user' else AIMessage(content=content))

    messages.append(HumanMessage(content=chat))

    # Execute agent
    result = agent.invoke({"messages": messages})

    print("result = ", result)

    # Extraction logic for DeepAgent response
    try:
        # DeepAgent typically returns a list of messages. We want the content of the last AI message.
        last_msg = result["messages"][-1]

        # Handle the specific response structure if it's a list of content chunks
        if hasattr(last_msg, 'content') and isinstance(last_msg.content, list):
            # Try to find the 'text' key in the content chunks
            for chunk in last_msg.content:
                if isinstance(chunk, dict) and 'text' in chunk:
                    response = chunk['text']
                    break
            else:
                response = str(last_msg.content)
        elif hasattr(last_msg, 'content'):
            response = last_msg.content
        else:
            response = str(last_msg)

    except Exception as e:
        print(f"Error parsing agent response: {e}")
        response = "I encountered an error generating a response."

    return response#, DUMMY_FLOW_DIAGRAM_DATA

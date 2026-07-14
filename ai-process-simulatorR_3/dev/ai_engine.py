import os
import re
import json
import ast
from typing import TypedDict, Sequence, Annotated, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
import uuid
import pandas as pd

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda left, right: left + right]

def clean_string(input_string):
    cleaned_string = input_string.replace('```json', '').replace('\n', '').replace('```', '')
    return cleaned_string.strip()

class AIEngine:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=self.api_key
        )
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.7,
        )
        self.rag_chain = None

    def setup_rag_for_project(self, project_id: str, files: list):
        """Sets up RAG for a specific project."""
        if not files:
            return None

        # Use project_id as part of the persist directory to avoid collisions
        persist_directory = f"./chroma_db_{project_id}"

        # If DB exists, load it. Otherwise, create it from uploaded files.
        if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
            docs = []
            for file_info in files:
                try:
                    loader = PyPDFLoader(file_info['filepath'])
                    docs.extend(loader.load())
                except Exception as e:
                    print(f"Error loading PDF {file_info['filepath']}: {e}")

            if not docs:
                return None

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=persist_directory
            )
        else:
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
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

        self.rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return self.rag_chain

    # --- Tools Internal functions ---
    def _get_inlet_stream_tool(self, feed_condition, feed_composition) -> dict:
        feed_condition = ast.literal_eval(feed_condition)
        feed_composition = json.loads(feed_composition)
        feed_temp, feed_pressure, inlet_flowrate = feed_condition[0], feed_condition[1], feed_condition[2]

        mole_comp_dict = {}
        for i, data in feed_composition.items():
            if data["type"] == 'Mole_Fraction':
                mole_comp_dict[i] = data["value"] * inlet_flowrate
            else:
                mole_comp_dict[i] = data["value"]

        mole_frac_dict = {i: val / inlet_flowrate for i, val in mole_comp_dict.items()}
        return {
            'Name': 'Feed',
            'Equipment': 'Feed_stream',
            'Temperature (C)': feed_temp,
            'Pressure (bar)': feed_pressure,
            'Molar Flowrate (mol/s)': inlet_flowrate,
            'Mole Fraction': mole_frac_dict,
        }

    def simulation_logic(self, content: str):
        """
        Modified simulation logic from ai_5.py to return JSON for flow diagram.
        """
        # Step 1: Process Info
        process_info = self.rag_chain.invoke("Consider you are a chemical engineer and you are planning to simulate the ethylbenzene process. collect all the information about the process with all the chemicals and equipment") if self.rag_chain else "General ethylbenzene production process."

        updated_response = self.llm.invoke([
            SystemMessage(content="you are a chemical expert, check and make any changes needed in the process by user and return the process in steps where each equipment is sent as one step like step 1, step 2 and goes on..."),
            HumanMessage(content=f"process information = {process_info}. and conversation is = {content}")
        ])

        feed_temp_pres_flow = self.llm.invoke([
            SystemMessage(content="consider you are a chemical engineer and collect the inlet stream temperature in C, pressure in bar or atm and flowrate in kmol/s. return as a list [temp, pres, flow]. return only the list"),
            HumanMessage(content=updated_response.content)
        ])

        feed_comp = self.llm.invoke([
            SystemMessage(content="Create a JSON object of chemicals: {'ChemName': {'type': 'Mole_Fraction', 'value': 0.1}}. Return only raw JSON."),
            HumanMessage(content=updated_response.content)
        ])

        # Step 2: Extract Steps
        steps_response = self.llm.invoke([
            SystemMessage(content="List each equipment unit in the process as separate numbered steps. Format: Step 1: Heater - heat feed to 200C..."),
            HumanMessage(content=f"Process: {process_info}\nUser query: {content}")
        ])

        equipment_and_stream_dict_resp = self.llm.invoke([
            SystemMessage(content="Return a dictionary with equipment name as key and list of outlet streams as value. Example: {'Heater_1': ['Heater_1_outlet'], 'Distillation_1': ['Distillation_1_liquid', 'Distillation_1_vapor']}. Return raw JSON."),
            HumanMessage(content=steps_response.content)
        ])

        try:
            eq_dict = json.loads(clean_string(equipment_and_stream_dict_resp.content))
            step_lines = [line.strip() for line in steps_response.content.split('\n') if line.strip() and 'Step' in line]

            equipment_list = {}
            connections = []

            # We need to map these to the format the frontend expects
            # This is a simplified version of the logic in ai_5.py for generating the JSON
            for i, step_desc in enumerate(step_lines, 1):
                # Tool selection (simplified)
                tool_selection = self.llm.invoke([
                    SystemMessage(content="Select one tool: ['heater', 'pump', 'reactor', 'cooler', 'flash', 'distillation']. Return JSON: {'tool': 'tool_name', 'params': {}}"),
                    HumanMessage(content=step_desc)
                ])
                tool_call = json.loads(clean_string(tool_selection.content))
                tool_name = tool_call['tool']

                eq_name = list(eq_dict.keys())[i-1] if i <= len(eq_dict) else f"Eq_{i}"
                equipment_list[eq_name] = tool_name.capitalize()

                outlets = eq_dict.get(eq_name, [f"{eq_name}_outlet"])
                connections.append({
                    "equipment": eq_name,
                    "outlet": outlets,
                    "Param": tool_call['params']
                })

            flow_diagram = {
                "Equipment_list": equipment_list,
                "Connection": connections
            }

            return "Simulation complete. Flow diagram generated.", flow_diagram

        except Exception as e:
            print(f"Simulation Error: {e}")
            return f"Error generating simulation: {e}", None

    # --- LangGraph Tools ---
    def get_tools(self):
        @tool
        def rag_enquiry(content: str) -> str:
            """Answers questions about the process from the paper."""
            if self.rag_chain:
                return self.rag_chain.invoke(content)
            return "Error: RAG chain not configured."

        @tool
        def simulation(content: str) -> str:
            """Simulates the process step-by-step."""
            # This tool will be handled specially in the graph to capture the JSON
            return "RUN_SIMULATION"

        @tool
        def chemical_discussion(content: str) -> str:
            """General chemical engineering discussion."""
            response = self.llm.invoke([SystemMessage(content="You are a knowledgeable chemical engineering assistant."), HumanMessage(content=content)])
            return response.content

        @tool
        def other_discussion(content: str) -> str:
            """Non-chemical engineering questions."""
            return "Sorry, I can only support chemical engineering questions."

        return [rag_enquiry, simulation, chemical_discussion, other_discussion]

    def create_graph(self):
        tools = self.get_tools()
        tool_node = ToolNode(tools)

        def agent_node(state: AgentState):
            system_prompt = SystemMessage(content="You are a chemical expert assistant. Route requests to tools: <rag_enquiry>, <simulation>, <chemical_discussion>, <other_discussion>. Respond only with the tool name in angle brackets if a tool is needed.")
            # Only use the last user message for routing logic
            latest_user_message = state['messages'][-1]
            response = self.llm.invoke([system_prompt, latest_user_message])

            tool_call_match = re.search(r'<(\w+)>', response.content)
            if tool_call_match:
                tool_name = tool_call_match.group(1)
                tool_call = {
                    "id": str(uuid.uuid4()),
                    "name": tool_name,
                    "args": {"content": latest_user_message.content}
                }
                return {'messages': [AIMessage(content="", tool_calls=[tool_call])]}
            return {'messages': [response]}

        def should_continue(state: AgentState):
            last_message = state['messages'][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "continue"
            return "end"

        workflow = StateGraph(AgentState)
        workflow.add_node('agent', agent_node)
        workflow.add_node('tools', tool_node)
        workflow.add_edge(START, 'agent')
        workflow.add_conditional_edges('agent', should_continue, {'continue': 'tools', 'end': END})
        workflow.add_edge('tools', END)

        return workflow.compile()

    async def run_chat(self, project_id: str, files: list, chat: str, chat_history: list):
        # 1. Setup RAG
        self.setup_rag_for_project(project_id, files)

        # 2. Prepare state
        messages = []
        for msg in chat_history:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            else:
                messages.append(AIMessage(content=msg['content']))

        messages.append(HumanMessage(content=chat))

        # 3. Run graph
        app = self.create_graph()
        result = app.invoke({'messages': messages})

        final_message = result['messages'][-1]
        reply = final_message.content if hasattr(final_message, 'content') else str(final_message)

        # 4. Check if simulation was called in the tool sequence
        flow_diagram = None
        for msg in result['messages']:
            if isinstance(msg, ToolMessage):
                # If the tool was 'simulation' and the result matches our trigger
                # Note: ToolNode simply returns the output of the tool.
                # Since our 'simulation' tool returns "RUN_SIMULATION", we can detect it.
                if msg.content == "RUN_SIMULATION":
                    text, diagram = self.simulation_logic(chat)
                    reply = text
                    flow_diagram = diagram
                    break

        return reply, flow_diagram

import os
import uuid
import json
from typing import List, Dict, Any, Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.tools import tool
import pandas as pd

RAG_DIR = "RAG"

def get_rag_dir(project_id: str):
    """Returns the absolute path to the RAG directory for a project."""
    return os.path.join(RAG_DIR, project_id)

# --- Equipment Catalog ---
# Derived from frontend EquipmentType definitions
EQUIPMENT_CATALOG = {
    "Streams": ["Feed", "Product"],
    "Basic Units": ["Tank", "Pump", "Mixer", "Splitter"],
    "Heat & Pressure": ["Heater", "Cooler", "Compressor", "Expander", "HeatExchanger"],
    "Separation & Reaction": ["Flash", "DistillationColumn", "Reactor"]
}

# --- Dummy Simulation Data for PDF Generation ---
# This represents the structure of a completed simulation that would be used to generate a report.
DUMMY_SIMULATION_DATA = {
    "project_id": "proj_12345",
    "project_name": "Ethylbenzene Production Plant",
    "nodes": [
        {"id": "feed-1", "type": "Feed", "name": "Fresh Feed", "properties": {"flowrate": 100, "temp": 25, "pressure": 1}},
        {"id": "heater-1", "type": "Heater", "name": "Pre-Heater", "properties": {"outletTemperature": 350, "duty": 1.5e6}},
        {"id": "reactor-1", "type": "Reactor", "name": "Alkylation Reactor", "properties": {"temperature": 400, "pressure": 20, "conversion": 0.95}},
        {"id": "dist-1", "type": "DistillationColumn", "name": "Fractionator", "properties": {"stages": 20, "refluxRatio": 2.5, "topTemp": 180}}
    ],
    "edges": [
        {"id": "e1", "from": "feed-1", "to": "heater-1"},
        {"id": "e2", "from": "heater-1", "to": "reactor-1"},
        {"id": "e3", "from": "reactor-1", "to": "dist-1"}
    ],
    "results": [
        {"equipment": "Pre-Heater", "parameter": "Efficiency", "value": "92%", "status": "Nominal"},
        {"equipment": "Alkylation Reactor", "parameter": "Conversion", "value": "95.4%", "status": "Nominal"},
        {"equipment": "Fractionator", "parameter": "Purity", "value": "99.8%", "status": "Nominal"}
    ]
}

DUMMY_FLOW_DIAGRAM_DATA = [
    {
        "equipment": "Heater",
        "equipment_id": "Heater_1",
        "outlets": ["Flash_2"],
        "params": {"Temp": "350C", "Duty": "1.5MW"}
    },
    {
        "equipment": "Flash",
        "equipment_id": "Flash_2",
        "outlets": ["Reactor_1"],
        "params": {}
    },
    {
        "equipment": "Reactor",
        "equipment_id": "Reactor_1",
        "outlets": [],
        "params": {"Conversion": "95%"}
    }
]

def get_embeddings(api_key: str):
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",#"models/text-embedding-004",
        google_api_key=api_key
    )


def process_project_rag(api_key: str, project_id: str, file_path: str):
    """
    Handles indexing of files for a specific project.
    """
    persist_directory = os.path.join(RAG_DIR, project_id)
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)
        print(f"Created RAG directory for project {project_id}")

    embeddings = get_embeddings(api_key)

    try:
        print(f"Processing file for RAG: {file_path}")
        if file_path.lower().endswith('.pdf'):
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            docs = [Document(page_content=text, metadata={"source": file_path})]

        if not docs:
            print(f"No content extracted from {file_path}")
            return {"status": "failed", "reason": "Empty document"}

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        print(f"Split {file_path} into {len(splits)} chunks.")

        # Use existing store if it exists, otherwise create new
        if os.path.exists(persist_directory) and os.listdir(persist_directory):
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            vector_store.add_documents(splits)
            print(f"Added {len(splits)} chunks to existing RAG store for {project_id}.")
        else:
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"Created new RAG store for {project_id} with {len(splits)} chunks.")

        return {"status": "success", "project_id": project_id}
    except Exception as e:
        print(f"RAG Processing Error for {project_id} on file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        raise e


def get_formatted_flow_diagram(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforms raw nodes and edges from the frontend flow diagram
    into the requested structured format.
    """
    formatted_data = []

    for node in nodes:
        node_id = node.get("id")
        # Find all outlets for this equipment
        outlets = [edge.get("to") for edge in edges if edge.get("from") == node_id]

        formatted_data.append({
            "equipment": node.get("type"),
            "equipment_id": node.get("name") or node_id,
            "outlets": outlets,
            "params": node.get("properties", {})
        })

    return formatted_data

def get_flow_diagram_from_db(project_id: str) -> List[Dict[str, Any]]:
    """
    Fetches the latest flow diagram configuration from the database
    and returns it in the formatted structure.
    """
    try:
        from database import SessionLocal, Simulation
        db = SessionLocal()
        try:
            sim = db.query(Simulation).filter(Simulation.project_id == project_id).order_by(Simulation.id.desc()).first()
            if not sim or not sim.config_json:
                return []

            config = json.loads(sim.config_json)
            nodes = config.get("nodes", [])
            edges = config.get("edges", [])
            return get_formatted_flow_diagram(nodes, edges)
        finally:
            db.close()
    except Exception as e:
        print(f"Error fetching flow diagram from DB: {e}")
        return []

# @tool
def retrieve_rag_documents(api_key: str, project_id: str, query: str, k: int = 5):
    """
    Retrieves relevant documents from the project's RAG store.

    """
    persist_directory = os.path.join(RAG_DIR, project_id)
    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        return []

    embeddings = get_embeddings(api_key)
    vector_store = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    return vector_store.similarity_search(query, k=k)

def process_simulation_config(config_json: Dict[str, Any]):
    """
    Processes the JSON configuration sent from the frontend when 'Run Simulation' is clicked.
    The JSON contains equipment details: name, id, and specifications.
    """
    nodes = config_json.get("nodes", [])
    edges = config_json.get("edges", [])

    processed_config = {
        "equipment_count": len(nodes),
        "connection_count": len(edges),
        "details": []
    }

    for node in nodes:
        # Extract equipment name, id, and properties
        node_info = {
            "id": node.get("id"),
            "name": node.get("name"),
            "type": node.get("type"),
            "specs": node.get("properties", {})
        }
        processed_config["details"].append(node_info)

    print(f"Processed simulation configuration for {len(nodes)} units.")
    return processed_config

@tool
def compounds_list():
    "this tool will return all the available chemical in the db , it will return the list of chemical names"
    data=pd.read_csv("")
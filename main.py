import os
import shutil
import json
import csv
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import init_db, get_db, Project, Message, Simulation, File as DBFile, SessionLocal
from ai_engine_2 import generate_deep_agent_response
from ai_tools import process_project_rag, process_simulation_config ,DUMMY_SIMULATION_DATA ,DUMMY_FLOW_DIAGRAM_DATA, get_formatted_flow_diagram
from langchain_core.messages import HumanMessage ,SystemMessage ,AIMessage
from langchain_core.output_parsers import JsonOutputParser
from simulation import simulation_calculation
import dummy_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = "uploads"
RAG_DIR = "RAG"


if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

init_db()

# Models
class ProjectCreate(BaseModel):
    name: str

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    results: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    message: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    model_name: Optional[str] = "gpt-4"
    api_key: Optional[str] = None

class SimulationRunRequest(BaseModel):
    projectId: str
    project_data: Dict[str, Any]
    api_key: Optional[str] = None

# --- Endpoints ---

@app.post("/projects")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    import uuid
    project_id = str(uuid.uuid4())
    new_project = Project(id=project_id, name=project.name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {"id": new_project.id, "name": new_project.name}

@app.get("/projects")
async def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    result = []
    for p in projects:
        # Get latest simulation for this project
        sim = db.query(Simulation).filter(Simulation.project_id == p.id).order_by(Simulation.id.desc()).first()
        nodes, edges, results = [], [], []
        if sim:
            config = json.loads(sim.config_json) if sim.config_json else {}
            nodes = config.get("nodes", [])
            edges = config.get("edges", [])
            results = json.loads(sim.results_json) if sim.results_json else []

        result.append({
            "id": p.id,
            "name": p.name,
            "messages": [ { "sender": m.role if m.role == 'user' else 'ai', "text": m.content } for m in p.messages ],
            "nodes": nodes,
            "edges": edges,
            "results": results
        })
    return result

@app.get("/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get latest simulation
    sim = db.query(Simulation).filter(Simulation.project_id == project_id).order_by(Simulation.id.desc()).first()
    nodes, edges, results = [], [], []
    if sim:
        config = json.loads(sim.config_json) if sim.config_json else {}
        nodes = config.get("nodes", [])
        edges = config.get("edges", [])
        results = json.loads(sim.results_json) if sim.results_json else []

    return {
        "id": project.id,
        "name": project.name,
        "messages": [ { "sender": m.role if m.role == 'user' else 'ai', "text": m.content } for m in project.messages ],
        "files": [ { "name": f.filename } for f in project.files ],
        "nodes": nodes,
        "edges": edges,
        "results": results
    }

@app.put("/projects/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name:
        project.name = data.name

    # If messages are updated, sync to DB
    if data.messages is not None:
        # Simple sync: clear and re-add
        db.query(Message).filter(Message.project_id == project_id).delete()
        for msg in data.messages:
            role = msg.get('role') or ("user" if msg.get('sender') == 'user' else "ai")
            content = msg.get('content') or msg.get('text', '')
            db.add(Message(project_id=project_id, role=role, content=content))

    # For nodes/edges/results, update the latest simulation record or create a new one
    if data.nodes is not None or data.edges is not None or data.results is not None:
        sim = db.query(Simulation).filter(Simulation.project_id == project_id).order_by(Simulation.id.desc()).first()
        if not sim:
            sim = Simulation(project_id=project_id)
            db.add(sim)

        if data.nodes is not None or data.edges is not None:
            # Use existing config if only one is provided
            current_config = json.loads(sim.config_json) if sim.config_json else {"nodes": [], "edges": []}
            config = {
                "nodes": data.nodes if data.nodes is not None else current_config.get("nodes", []),
                "edges": data.edges if data.edges is not None else current_config.get("edges", [])
            }
            sim.config_json = json.dumps(config)

        if data.results is not None:
            sim.results_json = json.dumps(data.results)

    db.commit()
    return {"message": "Project updated successfully"}

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete files from disk
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)

    # Delete RAG folder
    from ai_tools import get_rag_dir
    rag_dir = get_rag_dir(project_id)
    if os.path.exists(rag_dir):
        shutil.rmtree(rag_dir)

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@app.get("/chemicals")
async def get_chemicals():
    """Fetch the list of chemicals from Open_source_db2.csv"""
    try:
        chemicals = []
        with open("Open_source_db2.csv", mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Name"):
                    chemicals.append(row["Name"])

        # Return unique chemicals sorted alphabetically
        return sorted(list(set(chemicals)))
    except Exception as e:
        print(f"Error reading chemicals CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading chemicals database: {str(e)}")

@app.post("/projects/{project_id}/generate-report")
async def generate_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_dir = os.path.join(UPLOAD_DIR, project_id)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    report_filename = f"Simulation_Report_{project_id}.pdf"
    report_path = os.path.join(project_dir, report_filename)

    # Create a dummy PDF (just a text file with .pdf extension for this dummy implementation)
    with open(report_path, "w") as f:
        f.write(f"DUMMY SIMULATION REPORT\nProject: {project.name}\nID: {project_id}\n\nThis is a dummy PDF report generated automatically.")

    db_file = DBFile(project_id=project_id, filename=report_filename, filepath=report_path)
    db.add(db_file)
    db.commit()

    return {"filename": report_filename, "message": "Report generated successfully"}


@app.post("/projects/{project_id}/upload")
async def upload_file(project_id: str, file: UploadFile = File(...), api_key: Optional[str] = Form(None), db: Session = Depends(get_db)):
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    file_path = os.path.join(project_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_file = DBFile(project_id=project_id, filename=file.filename, filepath=file_path)
    db.add(db_file)
    db.commit()

    # Automatic Ragging if api_key is provided
    print("api_key",api_key)
    if api_key:
        try:
            rag_result = process_project_rag(api_key=api_key, project_id=project_id, file_path=file_path)
            return {"filename": file.filename, "message": "File uploaded and indexed successfully", "rag": rag_result}
        except Exception as e:
            print(f"Automatic ragging failed: {e}")
            return {"filename": file.filename, "message": "File uploaded, but indexing failed", "error": str(e)}

    return {"filename": file.filename, "message": "File uploaded successfully"}

@app.post("/projects/{project_id}/chat")
async def chat(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Get project and its files for RAG
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    files = [{"filepath": f.filepath, "filename": f.filename} for f in project.files]
    print("model",request.api_key,"key",request.model_name)
    print("request.message",request.message)

    # 2. Prepare chat history
    history = []
    if request.chat_history:
        for msg in request.chat_history:
            role = "user" if msg.get('sender') == 'user' else "ai"
            history.append({"role": role, "content": msg.get('text', '')})

    history=history[:-1]

    print("history",history)
    # 3. Generate response using the Deep Agent responder
    try:
        reply = await generate_deep_agent_response(
            api_key=request.api_key,
            model_name=request.model_name,
            project_id=project_id,
            chat=request.message,
            chat_history=history
        )
        parser = JsonOutputParser()
        parsed_dict = parser.parse(reply)
        print("parsed_dict",parsed_dict)


    except Exception as e:
        print(f"Deep Agent response failed: {e}")
        parsed_dict={}
        parsed_dict['text'] = f"AI Engine Error: {str(e)}"
        parsed_dict["flow_diagram"] = None


    # 4. Save to DB
    user_msg = Message(project_id=project_id, role="user", content=request.message)
    ai_msg = Message(project_id=project_id, role="ai", content=parsed_dict['text'])
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()

    return parsed_dict#{
    #     "text": reply,
    #     "flow_diagram": DUMMY_FLOW_DIAGRAM_DATA#flow_diagram
    # }

@app.delete("/simulation/{project_id}")
async def delete_simulation(project_id: str, db: Session = Depends(get_db)):
    db.query(Simulation).filter(Simulation.project_id == project_id).delete()
    db.commit()
    return {"message": "Simulation data deleted successfully"}

@app.get("/projects/{project_id}/flow-diagram")
async def get_flow_diagram(project_id: str, db: Session = Depends(get_db)):
    """Fetch the current flow diagram configuration for a project"""
    # Get the latest simulation record for this project
    sim = db.query(Simulation).filter(Simulation.project_id == project_id).order_by(Simulation.id.desc()).first()

    if not sim or not sim.config_json:
        return {"status": "success", "flow_diagram": []}

    try:
        config = json.loads(sim.config_json)
        nodes = config.get("nodes", [])
        edges = config.get("edges", [])
        formatted_diagram = get_formatted_flow_diagram(nodes, edges)
        return {"status": "success", "flow_diagram": formatted_diagram}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing flow diagram: {str(e)}")

@app.get("/projects/{project_id}/simulation-results")
async def get_simulation_results(project_id: str, db: Session = Depends(get_db)):
    """Fetch the latest simulation results for a project"""
    sim = db.query(Simulation).filter(Simulation.project_id == project_id).order_by(Simulation.id.desc()).first()
    if not sim or not sim.results_json:
        return {"status": "success", "results": []}

    try:
        results = json.loads(sim.results_json)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing results: {str(e)}")

@app.post("/simulation/run")
async def run_simulation(request: SimulationRunRequest, db: Session = Depends(get_db)):
    # 1. Process the frontend configuration into the format expected by simulation.py
    processed_data = process_simulation_config(request.project_data)

    # 2. Run the thermodynamic simulation
    try:
        # simulation_calculation now returns the detailed results table (list of dicts)
        results = simulation_calculation(processed_data)
    except Exception as e:
        print(f"Simulation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    # 3. Save the simulation record (config and results) to the database
    sim = Simulation(
        project_id=request.projectId,
        config_json=json.dumps(request.project_data),
        results_json=json.dumps(results)
    )
    db.add(sim)
    db.commit()

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

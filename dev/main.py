import os
import shutil
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import init_db, get_db, Project, Message, Simulation, File as DBFile, SessionLocal
from .ai_engine import AIEngine
from . import dummy_data

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
    projectId: str
    chat: str
    chat_history: List[Dict[str, Any]]
    model_name: str
    api_key: str

class SimulationRunRequest(BaseModel):
    projectId: str
    project_data: Dict[str, Any]

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
    return [
        {
            "id": p.id,
            "name": p.name,
            "messages": [ { "role": m.role, "content": m.content } for m in p.messages ],
            "nodes": [], # These would be extracted from the last simulation
            "edges": [],
            "results": []
        } for p in projects
    ]

@app.get("/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "name": project.name,
        "messages": [ { "role": m.role, "content": m.content } for m in project.messages ],
        "files": [ { "name": f.filename } for f in project.files ]
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
            db.add(Message(project_id=project_id, role=msg['role'], content=msg['content']))

    # For nodes/edges/results, we can store them as a simulation record
    if data.nodes or data.edges or data.results:
        sim = Simulation(
            project_id=project_id,
            config_json=json.dumps({"nodes": data.nodes, "edges": data.edges}),
            results_json=json.dumps(data.results)
        )
        db.add(sim)

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

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

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
async def upload_file(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    file_path = os.path.join(project_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_file = DBFile(project_id=project_id, filename=file.filename, filepath=file_path)
    db.add(db_file)
    db.commit()

    return {"filename": file.filename, "message": "File uploaded successfully"}

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Dummy Mode: Use dummy_data instead of actual AI engine
    reply = dummy_data.generate_dummy_chat_response(request.chat)
    flow_diagram = dummy_data.generate_dummy_flow_diagram()

    # 3. Save to DB
    user_msg = Message(project_id=request.projectId, role="user", content=request.chat)
    ai_msg = Message(project_id=request.projectId, role="ai", content=reply)
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()

    return {
        "reply": reply,
        "flow_diagram": flow_diagram
    }

@app.post("/simulation/run")
async def run_simulation(request: SimulationRunRequest, db: Session = Depends(get_db)):
    # Use dummy data generator
    results = dummy_data.generate_dummy_simulation_results(request.project_data)

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

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import json
import os
from pathlib import Path
import uuid

from models import (
    init_db, get_session, Project, Node, Edge,
    ChatMessage, SimulationResult, UploadedFile, Chemical
)
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI(title="Chemical Engineering Simulation API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = init_db()


def get_db():
    db = get_session(engine)
    try:
        yield db
    finally:
        db.close()


# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Pydantic Models
class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None


class NodeCreate(BaseModel):
    id: str
    type: str
    name: str
    x: float
    y: float
    properties: dict = {}


class EdgeCreate(BaseModel):
    id: str
    from_node: str
    to_node: str


class MessageCreate(BaseModel):
    id: str
    sender: str
    text: str


class SimulationRun(BaseModel):
    nodes: List[dict]
    edges: List[dict]


# ==================== PROJECT ENDPOINTS ====================

@app.post("/api/projects")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    new_project = Project(name=project.name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "id": new_project.id,
        "name": new_project.name,
        "created_at": new_project.created_at.isoformat(),
        "nodes": [],
        "edges": [],
        "messages": [],
        "results": []
    }


@app.get("/api/projects")
async def get_all_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat()
        }
        for p in projects
    ]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project with all its data"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
        "nodes": [
            {
                "id": n.id,
                "type": n.type,
                "name": n.name,
                "x": n.x,
                "y": n.y,
                "properties": n.properties
            }
            for n in project.nodes
        ],
        "edges": [
            {
                "id": e.id,
                "from": e.from_node,
                "to": e.to_node
            }
            for e in project.edges
        ],
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "text": m.text,
                "timestamp": m.timestamp.isoformat()
            }
            for m in project.messages
        ],
        "results": [
            {
                "id": r.id,
                "parameter": r.parameter,
                "value": r.value,
                "status": r.status
            }
            for r in project.results
        ]
    }


@app.put("/api/projects/{project_id}")
async def update_project(
        project_id: str,
        project_update: dict,
        db: Session = Depends(get_db)
):
    """Update project data"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update project name if provided
    if "name" in project_update:
        project.name = project_update["name"]

    # Update nodes
    if "nodes" in project_update:
        # Delete existing nodes
        db.query(Node).filter(Node.project_id == project_id).delete()
        # Add new nodes
        for node_data in project_update["nodes"]:
            node = Node(
                id=node_data["id"],
                project_id=project_id,
                type=node_data["type"],
                name=node_data["name"],
                x=node_data["x"],
                y=node_data["y"],
                properties=node_data.get("properties", {})
            )
            db.add(node)

    # Update edges
    if "edges" in project_update:
        db.query(Edge).filter(Edge.project_id == project_id).delete()
        for edge_data in project_update["edges"]:
            edge = Edge(
                id=edge_data["id"],
                project_id=project_id,
                from_node=edge_data["from"],
                to_node=edge_data["to"]
            )
            db.add(edge)

    # Update messages
    if "messages" in project_update:
        db.query(ChatMessage).filter(ChatMessage.project_id == project_id).delete()
        for msg_data in project_update["messages"]:
            message = ChatMessage(
                id=msg_data["id"],
                project_id=project_id,
                sender=msg_data["sender"],
                text=msg_data["text"]
            )
            db.add(message)

    # Update results
    if "results" in project_update:
        db.query(SimulationResult).filter(SimulationResult.project_id == project_id).delete()
        for result_data in project_update["results"]:
            result = SimulationResult(
                project_id=project_id,
                parameter=result_data["parameter"],
                value=result_data["value"],
                status=result_data["status"]
            )
            db.add(result)

    db.commit()
    return {"message": "Project updated successfully"}


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and all related data"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete uploaded files from filesystem
    files = db.query(UploadedFile).filter(UploadedFile.project_id == project_id).all()
    for file in files:
        try:
            if os.path.exists(file.filepath):
                os.remove(file.filepath)
        except Exception as e:
            print(f"Error deleting file {file.filepath}: {e}")

    # Delete project (cascade will handle related records)
    db.delete(project)
    db.commit()

    return {"message": "Project and all related data deleted successfully"}


# ==================== SIMULATION ENDPOINTS ====================

@app.post("/api/projects/{project_id}/simulate")
async def run_simulation(
        project_id: str,
        simulation_data: SimulationRun,
        db: Session = Depends(get_db)
):
    """Run simulation and return results"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clear previous results
    db.query(SimulationResult).filter(SimulationResult.project_id == project_id).delete()

    # Generate simulation results based on equipment
    results = []
    for node in simulation_data.nodes:
        node_type = node.get("type")
        node_name = node.get("name")
        properties = node.get("properties", {})

        if node_type == "Reactor":
            results.append({
                "parameter": f"{node_name} Temperature",
                "value": f"{properties.get('temperature', 350)} K",
                "status": "Nominal"
            })
            results.append({
                "parameter": f"{node_name} Conversion",
                "value": "92%",
                "status": "Excellent"
            })
        elif node_type == "DistillationColumn":
            results.append({
                "parameter": f"{node_name} Purity",
                "value": "99.2%",
                "status": "Nominal"
            })
            results.append({
                "parameter": f"{node_name} Duty",
                "value": "2.5 MW",
                "status": "High"
            })
        elif node_type == "Heater":
            results.append({
                "parameter": f"{node_name} Outlet Temp",
                "value": f"{properties.get('outletTemperature', 400)} K",
                "status": "Nominal"
            })
        elif node_type == "Pump":
            results.append({
                "parameter": f"{node_name} Flow",
                "value": "120 L/min",
                "status": "Nominal"
            })
        else:
            results.append({
                "parameter": f"{node_name} Status",
                "value": "Active",
                "status": "Nominal"
            })

    # Save results to database
    for result in results:
        db_result = SimulationResult(
            project_id=project_id,
            parameter=result["parameter"],
            value=result["value"],
            status=result["status"]
        )
        db.add(db_result)

    db.commit()

    # Return results with IDs
    saved_results = db.query(SimulationResult).filter(
        SimulationResult.project_id == project_id
    ).all()

    return {
        "results": [
            {
                "id": r.id,
                "parameter": r.parameter,
                "value": r.value,
                "status": r.status
            }
            for r in saved_results
        ]
    }


# ==================== FILE UPLOAD ENDPOINTS ====================

@app.post("/api/projects/{project_id}/upload")
async def upload_file(
        project_id: str,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Upload a file and associate it with a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create project-specific directory
    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(exist_ok=True)

    # Save file
    file_path = project_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save file info to database
    uploaded_file = UploadedFile(
        project_id=project_id,
        filename=file.filename,
        filepath=str(file_path),
        file_type=file.content_type or "unknown"
    )
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    return {
        "id": uploaded_file.id,
        "filename": uploaded_file.filename,
        "uploaded_at": uploaded_file.uploaded_at.isoformat()
    }


@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str, db: Session = Depends(get_db)):
    """Get all files for a project"""
    files = db.query(UploadedFile).filter(
        UploadedFile.project_id == project_id
    ).all()

    return [
        {
            "id": f.id,
            "filename": f.filename,
            "file_type": f.file_type,
            "uploaded_at": f.uploaded_at.isoformat()
        }
        for f in files
    ]


# ==================== CHEMICAL DATA ENDPOINTS ====================

@app.get("/api/chemicals")
async def get_chemicals(db: Session = Depends(get_db)):
    """Get all available chemicals"""
    chemicals = db.query(Chemical).all()
    return [c.name for c in chemicals]


@app.post("/api/chemicals/import")
async def import_chemicals_from_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Import chemicals from CSV file"""
    content = await file.read()

    # Save temporarily
    temp_path = UPLOAD_DIR / f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        df = pd.read_csv(temp_path)

        # Expected columns: name, formula, cas_number, molecular_weight
        for _, row in df.iterrows():
            chemical = Chemical(
                name=row.get('name'),
                formula=row.get('formula'),
                cas_number=row.get('cas_number'),
                molecular_weight=row.get('molecular_weight')
            )
            # Check if already exists
            existing = db.query(Chemical).filter(
                Chemical.name == chemical.name
            ).first()
            if not existing:
                db.add(chemical)

        db.commit()
        os.remove(temp_path)

        return {"message": f"Successfully imported {len(df)} chemicals"}
    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Error importing CSV: {str(e)}")


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import json
import PyPDF2
import io
import uuid
import os

# Database Setup
DATABASE_URL = "sqlite:///./projects.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Model
class ProjectDB(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    messages = Column(Text, nullable=True)  # JSON string
    nodes = Column(Text, nullable=True)  # JSON string
    edges = Column(Text, nullable=True)  # JSON string
    results = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# Pydantic Models
class Message(BaseModel):
    id: str
    sender: str
    text: str
    isTyping: Optional[bool] = False


class NodeProperties(BaseModel):
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    outletTemperature: Optional[float] = None
    outletPressure: Optional[float] = None
    stages: Optional[int] = None
    condenserType: Optional[str] = None
    refluxRatio: Optional[float] = None


class Node(BaseModel):
    id: str
    type: str
    name: str
    x: float
    y: float
    properties: Optional[Dict[str, Any]] = {}


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias='from')
    to: str


class Result(BaseModel):
    id: int
    parameter: str
    value: str
    status: str


class ProjectData(BaseModel):
    id: str
    name: str
    messages: Optional[List[Message]] = []
    nodes: Optional[List[Node]] = []
    edges: Optional[List[Edge]] = []
    results: Optional[List[Result]] = []


class ProjectCreateRequest(BaseModel):
    name: str


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    messages: Optional[List[Message]] = None
    nodes: Optional[List[Node]] = None
    edges: Optional[List[Edge]] = None
    results: Optional[List[Result]] = None


class ChatRequest(BaseModel):
    project_id: str
    message: str
    conversation_history: Optional[List[Message]] = []


class ChatResponse(BaseModel):
    response: str
    message_id: str


# FastAPI App
app = FastAPI(title="Flowsheet Simulation API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper Functions
def generate_ai_response(user_message: str, project_id: str = None) -> str:
    """Generate AI response - Simple rule-based system"""
    message_lower = user_message.lower()

    if "equipment" in message_lower or "flowsheet" in message_lower or "create" in message_lower:
        return """I can help you create a flowsheet! Please provide the equipment details in this format:"""


    elif "reactor" in message_lower:
        return "Reactors can have these parameters:\n- Temperature (K)\n- Pressure (bar)\n\nReactors typically have 1 input and can have multiple outputs for products and byproducts."

    elif "thank" in message_lower or "thanks" in message_lower:
        return "You're welcome! Let me know if you need any more help with your process simulation! 😊"

    elif "hi" in message_lower or "hello" in message_lower:
        return "Hello! 👋 I'm your process simulation assistant. I can help you create flowsheets, run simulations, and analyze results. What would you like to work on today?"

    else:
        return f"I understand you said: '{user_message}'\n\nI can help you with:\n- Creating flowsheets\n- Adding equipment\n- Running simulations\n- Setting parameters\n\nType 'help' to see all available commands!"


# API Endpoints

@app.get("/")
def root():
    return {
        "message": "Flowsheet Simulation API is running",
        "version": "1.0.0",
        "endpoints": {
            "projects": "/api/projects",
            "create": "/api/project/create",
            "chat": "/api/project/{project_id}/chat"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Project Endpoints

@app.post("/api/project/create", response_model=ProjectData)
def create_project(request: ProjectCreateRequest, db: Session = Depends(get_db)):
    """Create a new project with a unique ID"""
    try:
        project_id = str(uuid.uuid4())

        new_project = ProjectDB(
            id=project_id,
            name=request.name,
            messages=json.dumps([]),
            nodes=json.dumps([]),
            edges=json.dumps([]),
            results=json.dumps([])
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return ProjectData(
            id=new_project.id,
            name=new_project.name,
            messages=[],
            nodes=[],
            edges=[],
            results=[]
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")


@app.put("/api/project/{project_id}/save", response_model=dict)
def save_project(project_id: str, data: ProjectUpdateRequest, db: Session = Depends(get_db)):
    """Save or update a project by ID"""
    try:
        existing = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()

        if not existing:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        # Update only provided fields
        if data.name is not None:
            existing.name = data.name
        if data.messages is not None:
            existing.messages = json.dumps([msg.model_dump() for msg in data.messages])
        if data.nodes is not None:
            existing.nodes = json.dumps([node.model_dump() for node in data.nodes])
        if data.edges is not None:
            existing.edges = json.dumps([edge.model_dump() for edge in data.edges])
        if data.results is not None:
            existing.results = json.dumps([result.model_dump() for result in data.results])

        existing.updated_at = datetime.utcnow()

        db.commit()
        return {
            "status": "success",
            "message": f"Project {project_id} saved successfully",
            "id": project_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving project: {str(e)}")


@app.get("/api/project/{project_id}", response_model=ProjectData)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Retrieve a project by ID"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    return ProjectData(
        id=project.id,
        name=project.name,
        messages=json.loads(project.messages) if project.messages else [],
        nodes=json.loads(project.nodes) if project.nodes else [],
        edges=json.loads(project.edges) if project.edges else [],
        results=json.loads(project.results) if project.results else []
    )


@app.get("/api/projects", response_model=List[Dict[str, Any]])
def get_all_projects(db: Session = Depends(get_db)):
    """Get all projects (metadata only)"""
    projects = db.query(ProjectDB).order_by(ProjectDB.updated_at.desc()).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "node_count": len(json.loads(p.nodes)) if p.nodes else 0,
            "edge_count": len(json.loads(p.edges)) if p.edges else 0
        }
        for p in projects
    ]


@app.delete("/api/project/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and all its data by ID"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    project_name = project.name
    db.delete(project)
    db.commit()

    return {
        "status": "deleted",
        "message": f"Project '{project_name}' (ID: {project_id}) deleted successfully",
        "id": project_id
    }


# Chat Endpoint

@app.post("/api/project/{project_id}/chat", response_model=ChatResponse)
async def chat(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    """Process chat message and return AI response"""
    try:
        # Verify project exists
        project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        user_message = request.message

        # Load existing messages
        existing_messages = json.loads(project.messages) if project.messages else []

        # Generate AI response
        response_text = generate_ai_response(user_message, project_id)

        # Create response message
        response_id = f"ai-{datetime.utcnow().timestamp()}"

        # Update messages in database
        user_msg = {
            "id": f"user-{datetime.utcnow().timestamp()}",
            "sender": "user",
            "text": user_message,
            "isTyping": False
        }
        ai_msg = {
            "id": response_id,
            "sender": "ai",
            "text": response_text,
            "isTyping": False
        }

        existing_messages.extend([user_msg, ai_msg])
        project.messages = json.dumps(existing_messages)
        project.updated_at = datetime.utcnow()
        db.commit()

        return ChatResponse(
            response=response_text,
            message_id=response_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# PDF Upload Endpoint

@app.post("/api/project/{project_id}/upload_pdf")
async def upload_pdf(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and parse PDF file for a specific project"""
    try:
        # Verify project exists
        project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read PDF content
        pdf_content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))

        # Extract text from all pages
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text()

        # Parse extracted text for simulation data
        parsed_data = {
            "equipment_found": [],
            "parameters_found": {},
            "raw_text": extracted_text[:500]
        }

        # Detect equipment names
        equipment_keywords = ["reactor", "pump", "heater", "cooler", "tank", "column", "mixer", "splitter", "flash",
                              "compressor"]
        for keyword in equipment_keywords:
            if keyword.lower() in extracted_text.lower():
                parsed_data["equipment_found"].append(keyword.capitalize())

        return {
            "status": "success",
            "project_id": project_id,
            "filename": file.filename,
            "parsed_data": parsed_data,
            "message": f"PDF processed successfully for project {project_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


# Simulation Endpoint

@app.post("/api/project/{project_id}/simulation/run")
def run_simulation(project_id: str, data: Dict[str, Any], db: Session = Depends(get_db)):
    """Run simulation for a specific project"""
    try:
        # Verify project exists
        project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        equipment_list = data.get("Equipment_list", {})
        connections = data.get("Connection", [])

        # Mock simulation results based on equipment
        results = []
        result_id = 1

        for equip_name, equip_type in equipment_list.items():
            if equip_type.lower() == "reactor":
                results.append(
                    {"id": result_id, "parameter": f"{equip_name} Temperature", "value": "350 K", "status": "Nominal"})
                result_id += 1
                results.append(
                    {"id": result_id, "parameter": f"{equip_name} Conversion", "value": "92%", "status": "Excellent"})
                result_id += 1
            elif equip_type.lower() == "pump":
                results.append(
                    {"id": result_id, "parameter": f"{equip_name} Flow", "value": "120 L/min", "status": "Nominal"})
                result_id += 1
            elif equip_type.lower() == "heater":
                results.append(
                    {"id": result_id, "parameter": f"{equip_name} Duty", "value": "150 kW", "status": "Nominal"})
                result_id += 1

        # Add overall metrics
        results.append({"id": result_id, "parameter": "Total Energy", "value": "5.2 kWh", "status": "High"})

        # Update project results
        project.results = json.dumps(results)
        project.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "project_id": project_id,
            "results": results,
            "message": f"Simulation completed for project {project_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")


# Export Endpoint

@app.get("/api/project/{project_id}/export")
def export_project(project_id: str, db: Session = Depends(get_db)):
    """Export complete project data as JSON"""
    project = db.query(ProjectDB).filter(ProjectDB.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

    return {
        "id": project.id,
        "name": project.name,
        "messages": json.loads(project.messages) if project.messages else [],
        "nodes": json.loads(project.nodes) if project.nodes else [],
        "edges": json.loads(project.edges) if project.edges else [],
        "results": json.loads(project.results) if project.results else [],
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None
    }


# Run Server
if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Flowsheet Simulation API Server...")
    print("📊 Database: SQLite (projects.db)")
    print("🌐 Server: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)#, reload=True)

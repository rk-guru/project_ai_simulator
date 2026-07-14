import os
import csv
import json
import sqlite3
import shutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import google.generativeai as genai
from pypdf import PdfReader

# app = FastAPI()
#
# # Enable CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/chemicals", response_model=List[str])
async def get_chemicals():
    chemicals = []
    if os.path.exists(COMPOUNDS_FILE):
        try:
            with open(COMPOUNDS_FILE, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'Name' in row:
                        chemicals.append(row['Name'])
        except Exception as e:
            print(f"Error reading CSV: {e}")
            # Always return a valid list
            return ["Error reading CSV"]
    else:
        return ["Water", "Ethanol", "Methanol"]  # Remove "(Fallback)" for consistency
    return chemicals


# Database Setup
DB_FILE = "projects.db"
UPLOAD_DIR = "uploads"
COMPOUNDS_FILE = "compounds.csv"

# Configure Gemini
# Ensure you set the API_KEY environment variable when running the server
# e.g., export API_KEY="your_key" && python backend/main.py
# API_KEY = os.environ.get("API_KEY")
API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
if API_KEY:
    genai.configure(api_key=API_KEY)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id TEXT PRIMARY KEY, name TEXT, data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, filename TEXT, filepath TEXT)''')
    conn.commit()
    conn.close()


init_db()


# Models
class ProjectModel(BaseModel):
    id: str
    name: str
    messages: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []


class ChatRequest(BaseModel):
    message: str


# --- Helper Functions ---

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def extract_text_from_file(filepath: str, filename: str) -> str:
    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.pdf':
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif ext in ['.txt', '.csv', '.json', '.md']:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return f"[Unsupported file format: {ext}]"
    except Exception as e:
        return f"[Error reading file {filename}: {str(e)}]"


# --- Endpoints ---

@app.get("/chemicals", response_model=List[str])
async def get_chemicals():
    """Reads chemicals from the CSV file."""
    chemicals = []
    if os.path.exists(COMPOUNDS_FILE):
        try:
            with open(COMPOUNDS_FILE, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if 'Name' in row:
                        chemicals.append(row['Name'])
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return ["Error reading CSV"]
    else:
        return ["Water", "Ethanol", "Methanol (Fallback)"]

    return chemicals


@app.get("/projects", response_model=List[ProjectModel])
async def get_projects():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM projects")
    rows = c.fetchall()
    projects = []
    for row in rows:
        try:
            data = json.loads(row['data'])
            data['id'] = row['id']
            data['name'] = row['name']

            c.execute("SELECT filename FROM files WHERE project_id = ?", (row['id'],))
            files = [{'name': f['filename']} for f in c.fetchall()]
            data['files'] = files

            projects.append(data)
        except json.JSONDecodeError:
            continue
    conn.close()
    return projects


@app.get("/projects/{project_id}", response_model=ProjectModel)
async def get_project(project_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    data = json.loads(row['data'])

    c.execute("SELECT filename FROM files WHERE project_id = ?", (project_id,))
    files = [{'name': f['filename']} for f in c.fetchall()]
    data['files'] = files

    conn.close()
    return data


@app.put("/projects/{project_id}")
async def save_project(project_id: str, project: ProjectModel):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    exists = c.fetchone()

    project_json = project.json()

    if exists:
        c.execute("UPDATE projects SET name = ?, data = ? WHERE id = ?",
                  (project.name, project_json, project_id))
    else:
        c.execute("INSERT INTO projects (id, name, data) VALUES (?, ?, ?)",
                  (project_id, project.name, project_json))

    conn.commit()
    conn.close()
    return {"message": "Project saved successfully"}


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    c.execute("DELETE FROM files WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()

    project_upload_dir = os.path.join(UPLOAD_DIR, project_id)
    if os.path.exists(project_upload_dir):
        shutil.rmtree(project_upload_dir)

    return {"message": "Project deleted successfully"}


@app.post("/projects/{project_id}/upload")
async def upload_file(project_id: str, file: UploadFile = File(...)):
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    file_path = os.path.join(project_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO files (project_id, filename, filepath) VALUES (?, ?, ?)",
              (project_id, file.filename, file_path))
    conn.commit()
    conn.close()

    return {"filename": file.filename, "message": "File uploaded successfully"}


@app.post("/projects/{project_id}/chat")
async def chat_with_project(project_id: str, request: ChatRequest):
    # if not API_KEY:
    #     return {"text": "Error: API_KEY not set on backend server."}

    # 1. Fetch file contents
    project_dir = os.path.join(UPLOAD_DIR, project_id)
    context_text = ""

    if os.path.exists(project_dir):
        files = os.listdir(project_dir)
        for filename in files:
            file_path = os.path.join(project_dir, filename)
            content = extract_text_from_file(file_path, filename)
            context_text += f"\n--- File: {filename} ---\n{content}\n"

    # 2. Construct Prompt
    prompt = f"""
    You are an AI assistant for a Process Simulation tool.

    Context from uploaded files:
    {context_text}

    User Query: {request.message}
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return {"text": response.text}
    except Exception as e:
        print(f"GenAI Error: {e}")
        return {"text": f"Error communicating with AI: {str(e)}"}


@app.post("/projects/{project_id}/run")
async def run_simulation(project_id: str, project_data: ProjectModel):
    nodes = project_data.nodes
    results = []

    id_counter = 1

    for node in nodes:
        props = node.get('properties', {})
        name = node.get('name', 'Unknown')
        n_type = node.get('type', '')

        if n_type == 'Reactor':
            temp = props.get('temperature', 350)
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Temperature",
                "Value": f"{temp} K",
                "Status": "Nominal"
            })
            id_counter += 1
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Conversion",
                "Value": "92.5%",
                "Status": "Excellent"
            })
            id_counter += 1

        elif n_type == 'DistillationColumn':
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Purity",
                "Value": "99.8%",
                "Status": "Nominal"
            })
            id_counter += 1
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Heat Duty",
                "Value": "2.5 MW",
                "Status": "High"
            })
            id_counter += 1

        elif n_type == 'Feed':
            flow = props.get('flowRate', 0)
            compounds = props.get('compounds', [])
            comp_str = ", ".join([f"{c['name']} ({c['moleFraction']})" for c in compounds]) if compounds else "None"

            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Flow Rate",
                "Value": f"{flow} kmol/hr",
                "Status": "Nominal"
            })
            id_counter += 1
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Composition",
                "Value": comp_str,
                "Status": "Info"
            })
            id_counter += 1

        else:
            results.append({
                "id": id_counter,
                "Equipment": name,
                "Parameter": "Status",
                "Value": "Active",
                "Status": "Nominal"
            })
            id_counter += 1

    if not results:
        results = [{"id": 0, "Info": "No equipment to simulate."}]

    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import sqlite3
from pathlib import Path
import PyPDF2
import fitz
from ai_5 import run_document_agent

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads/pdfs'
DATABASE = 'simulation.db'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)


def get_db_connection():
    """Get database connection with foreign keys enabled"""
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Create uploaded_files table with foreign key to projects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            filesize INTEGER,
            extracted_text TEXT,
            page_count INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    ''')

    # Create chat_history table with foreign key to projects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            message TEXT NOT NULL,
            sender TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_pymupdf(pdf_path):
    """Extract text using PyMuPDF (fitz)"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text, len(doc)
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")
        return "", 0


def extract_text_pypdf2(pdf_path):
    """Fallback: Extract text using PyPDF2"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text, len(pdf_reader.pages)
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")
        return "", 0


# =========================
# PROJECT MANAGEMENT ROUTES
# =========================

@app.route("/api/projects", methods=['POST'])
def create_project():
    """Create new project"""
    try:
        data = request.get_json()
        project_id = data.get('id')
        project_name = data.get('name', 'Untitled Project')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, name) VALUES (?, ?)",
            (project_id, project_name)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "project_id": project_id,
            "message": "Project created successfully"
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects", methods=['GET'])
def get_projects():
    """Get all projects"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, created_date, last_modified FROM projects WHERE status = 'active' ORDER BY last_modified DESC"
        )

        projects = []
        for row in cursor.fetchall():
            projects.append({
                "id": row[0],
                "name": row[1],
                "created_date": row[2],
                "last_modified": row[3]
            })

        conn.close()
        return jsonify({"status": "success", "projects": projects}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<project_id>", methods=['DELETE'])
def delete_project(project_id):
    """Delete project (CASCADE will delete all files and chat history)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all files to delete physically
        cursor.execute(
            "SELECT filepath FROM uploaded_files WHERE project_id = ?",
            (project_id,)
        )
        files = cursor.fetchall()

        # Delete physical files
        for file_row in files:
            filepath = file_row[0]
            if os.path.exists(filepath):
                os.remove(filepath)

        # Delete project (CASCADE will delete files and chat records from DB)
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Project and all associated data deleted"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# CHAT ROUTES
# =========================

@app.route("/api/chat", methods=['POST'])
def chat():
    """Handle chat with PDF context"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        project_id = data.get('project_id', '')
        print('user_message',project_id)

        if not project_id:
            return jsonify({"error": "project_id is required"}), 400

        # Get PDF context for this specific project
        pdf_context = ""
        pdf_filename = None

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT extracted_text, original_filename FROM uploaded_files WHERE project_id = ? AND status = 'active' ORDER BY upload_date DESC LIMIT 1",
            (project_id,)
        )
        result = cursor.fetchone()

        if result:
            pdf_context = result[0][:5000] if result[0] else ""
            pdf_filename = result[1]
        print('pdf_filename',pdf_filename)
        # Save user message to chat history
        cursor.execute(
            "INSERT INTO chat_history (project_id, message, sender) VALUES (?, ?, ?)",
            (project_id, user_message, 'user')
        )

        # Generate AI response (pass pdf_context to your AI model)
        ai_response = run_document_agent(user_message, pdf_context)[1].content

        # Save AI response to chat history
        cursor.execute(
            "INSERT INTO chat_history (project_id, message, sender) VALUES (?, ?, ?)",
            (project_id, ai_response, 'ai')
        )

        # Update project last_modified timestamp
        cursor.execute(
            "UPDATE projects SET last_modified = CURRENT_TIMESTAMP WHERE id = ?",
            (project_id,)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "message": ai_response,
            "pdf_filename": pdf_filename,
            "has_pdf_context": bool(pdf_context),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/history/<project_id>", methods=['GET'])
def get_chat_history(project_id):
    """Get chat history for a project"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT message, sender, timestamp FROM chat_history WHERE project_id = ? ORDER BY timestamp ASC",
            (project_id,)
        )

        history = []
        for row in cursor.fetchall():
            history.append({
                "message": row[0],
                "sender": row[1],
                "timestamp": row[2]
            })

        conn.close()
        return jsonify({"status": "success", "history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# FILE UPLOAD ROUTES
# =========================

@app.route("/api/upload-pdf", methods=['POST'])
def upload_pdf():
    """Upload PDF with project validation"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        project_id = request.form.get('project_id', '')

        if not project_id:
            return jsonify({"error": "project_id is required"}), 400

        # Verify project exists, or create it if not
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ? AND status = 'active'", (project_id,))

        if not cursor.fetchone():
            # Auto-create project if it doesn't exist
            cursor.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                (project_id, f"Project {project_id}")
            )
            conn.commit()
            print(f"Auto-created project: {project_id}")

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{original_filename}"
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        file.save(full_path)
        file_size = os.path.getsize(full_path)

        # Extract text
        extracted_text, page_count = extract_text_pymupdf(full_path)
        if not extracted_text:
            extracted_text, page_count = extract_text_pypdf2(full_path)

        # Save to database
        cursor.execute(
            "INSERT INTO uploaded_files (project_id, filename, original_filename, filepath, filesize, extracted_text, page_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, unique_filename, original_filename, full_path, file_size, extracted_text, page_count)
        )

        # Update project timestamp
        cursor.execute(
            "UPDATE projects SET last_modified = CURRENT_TIMESTAMP WHERE id = ?",
            (project_id,)
        )

        conn.commit()
        file_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "status": "success",
            "message": "PDF uploaded successfully",
            "file_id": file_id,
            "filename": original_filename
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/<project_id>", methods=['GET'])
def get_project_files(project_id):
    """Get all files for a project"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, original_filename, filepath, filesize, upload_date FROM uploaded_files WHERE project_id = ? AND status = 'active' ORDER BY upload_date DESC",
            (project_id,)
        )

        files = []
        for row in cursor.fetchall():
            files.append({
                "id": row[0],
                "filename": row[1],
                "original_filename": row[2],
                "filepath": row[3],
                "filesize": row[4],
                "upload_date": row[5]
            })

        conn.close()
        return jsonify({"status": "success", "files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/<int:file_id>", methods=['DELETE'])
def delete_file(file_id):
    """Delete a specific file"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get file path
        cursor.execute("SELECT filepath FROM uploaded_files WHERE id = ?", (file_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({"error": "File not found"}), 404

        filepath = result[0]

        # Delete physical file
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete from database
        cursor.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "File deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# SIMULATION ROUTES
# =========================

@app.route("/api/generate-flowsheet", methods=['POST'])
def generate_flowsheet():
    """Generate flowsheet diagram"""
    data = request.get_json()
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    return jsonify({
        "status": "success",
        "message": "Flowsheet generated",
        "nodes": nodes,
        "edges": edges
    }), 200


@app.route("/api/run-simulation", methods=['POST'])
def run_simulation():
    """Run simulation"""
    data = request.get_json()

    return jsonify({
        "status": "success",
        "message": "Simulation completed successfully",
        "results": [
            {"parameter": "Temperature", "value": "350 K", "status": "Nominal"},
            {"parameter": "Pressure", "value": "1.2 atm", "status": "Normal"}
        ]
    }), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)

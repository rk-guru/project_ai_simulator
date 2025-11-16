from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import asyncio
from datetime import datetime
import uvicorn

# LLM Integration (using LangChain/OpenAI)
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

app = FastAPI(title="Chemical Process Simulation API")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Data Models =====
class EquipmentNode(BaseModel):
    id: str
    name: str
    type: str
    position: Dict[str, float]
    properties: Dict[str, Any]


class EquipmentEdge(BaseModel):
    id: str
    from_node: str
    to_node: str


class FlowsheetData(BaseModel):
    nodes: List[EquipmentNode]
    edges: List[EquipmentEdge]


class ChatMessage(BaseModel):
    message: str
    timestamp: Optional[str] = None


class SimulationRequest(BaseModel):
    flowsheet: FlowsheetData
    run_parameters: Optional[Dict[str, Any]] = {}


# ===== LLM Configuration =====
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    openai_api_key="your-api-key-here"
)

SYSTEM_PROMPT = """You are an expert chemical engineer assistant specializing in process simulation.
When users describe a chemical process, you should:
1. Identify required equipment (reactors, separators, pumps, heat exchangers, etc.)
2. Determine logical connections between equipment
3. Suggest appropriate process parameters
4. Return responses in JSON format for equipment connections.

Format your equipment connection responses as:
{
    "equipment": [
        {"id": "eq1", "name": "Feed Tank", "type": "Tank", "connections": ["eq2"]},
        {"id": "eq2", "name": "Reactor", "type": "Reactor", "connections": ["eq3"]},
        ...
    ]
}
"""

# ===== In-Memory Storage =====
active_sessions = {}
simulation_results = {}


# ===== Helper Functions =====
def parse_llm_equipment_response(llm_response: str) -> Dict:
    """Extract JSON equipment data from LLM response"""
    try:
        # Try to find JSON in the response
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = llm_response[start_idx:end_idx]
            return json.loads(json_str)
        return {"equipment": []}
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return {"equipment": []}


def convert_to_flowsheet_format(equipment_data: Dict) -> FlowsheetData:
    """Convert LLM equipment data to flowsheet format"""
    nodes = []
    edges = []

    equipment_list = equipment_data.get("equipment", [])

    # Generate nodes
    for i, eq in enumerate(equipment_list):
        node = EquipmentNode(
            id=eq.get("id", f"node_{i}"),
            name=eq.get("name", f"Equipment {i}"),
            type=eq.get("type", "Generic"),
            position={"x": 100 + i * 200, "y": 200},  # Auto-layout
            properties=eq.get("properties", {})
        )
        nodes.append(node)

        # Generate edges from connections
        connections = eq.get("connections", [])
        for conn in connections:
            edge = EquipmentEdge(
                id=f"edge_{eq['id']}_{conn}",
                from_node=eq["id"],
                to_node=conn
            )
            edges.append(edge)

    return FlowsheetData(nodes=nodes, edges=edges)


def simulate_process(flowsheet: FlowsheetData, parameters: Dict) -> Dict:
    """
    Run process simulation based on flowsheet configuration
    This is a simplified simulation - replace with actual simulation engine
    (e.g., DWSIM, Cantera, or custom thermodynamic models)
    """
    results = []

    # Process each equipment node
    for node in flowsheet.nodes:
        equipment_type = node.type
        props = node.properties

        # Simulate based on equipment type
        if equipment_type == "Reactor":
            temp = props.get("temperature", 350)
            pressure = props.get("pressure", 1.2)
            results.append({
                "id": len(results) + 1,
                "parameter": f"{node.name} Temperature",
                "value": f"{temp} K",
                "status": "Nominal" if 300 < temp < 400 else "Warning"
            })
            results.append({
                "id": len(results) + 1,
                "parameter": f"{node.name} Pressure",
                "value": f"{pressure} atm",
                "status": "Nominal"
            })

        elif equipment_type == "Pump":
            flow_rate = props.get("flow_rate", 150)
            results.append({
                "id": len(results) + 1,
                "parameter": f"{node.name} Flow Rate",
                "value": f"{flow_rate} L/min",
                "status": "Nominal"
            })

        elif equipment_type == "DistillationColumn":
            purity = props.get("purity", 99.5)
            results.append({
                "id": len(results) + 1,
                "parameter": f"{node.name} Product Purity",
                "value": f"{purity}%",
                "status": "Excellent" if purity > 99 else "Nominal"
            })

        elif equipment_type in ["Tank", "Flash"]:
            temp = props.get("temperature", 300)
            pressure = props.get("pressure", 1.0)
            results.append({
                "id": len(results) + 1,
                "parameter": f"{node.name} Level",
                "value": "85%",
                "status": "Nominal"
            })

    return {"results": results, "timestamp": datetime.now().isoformat()}


# ===== API Endpoints =====

@app.get("/")
async def root():
    return {"message": "Chemical Process Simulation API", "version": "1.0"}


@app.post("/api/chat")
async def chat_endpoint(message: ChatMessage):
    """
    Process user chat messages and return LLM responses with equipment JSON
    """
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message.message)
        ]

        response = llm(messages)
        llm_text = response.content

        # Parse equipment data from response
        equipment_data = parse_llm_equipment_response(llm_text)

        return {
            "response": llm_text,
            "equipment_data": equipment_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flowsheet/generate")
async def generate_flowsheet(message: ChatMessage):
    """
    Generate flowsheet from LLM response
    """
    try:
        # Get LLM response with equipment data
        chat_response = await chat_endpoint(message)
        equipment_data = chat_response["equipment_data"]

        # Convert to flowsheet format
        flowsheet = convert_to_flowsheet_format(equipment_data)

        return {
            "flowsheet": flowsheet.dict(),
            "llm_response": chat_response["response"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flowsheet/save")
async def save_flowsheet(flowsheet: FlowsheetData, session_id: str = "default"):
    """
    Save flowsheet configuration
    """
    active_sessions[session_id] = flowsheet.dict()
    return {"status": "saved", "session_id": session_id}


@app.get("/api/flowsheet/load/{session_id}")
async def load_flowsheet(session_id: str):
    """
    Load saved flowsheet
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"flowsheet": active_sessions[session_id]}


@app.post("/api/simulation/run")
async def run_simulation(request: SimulationRequest):
    """
    Run simulation based on flowsheet and return results table data
    """
    try:
        # Run simulation
        results = simulate_process(request.flowsheet, request.run_parameters)

        # Store results
        session_id = f"sim_{datetime.now().timestamp()}"
        simulation_results[session_id] = results

        return {
            "session_id": session_id,
            "results": results["results"],
            "timestamp": results["timestamp"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/results/{session_id}")
async def get_simulation_results(session_id: str):
    """
    Retrieve simulation results
    """
    if session_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Results not found")

    return simulation_results[session_id]


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with LLM
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Process with LLM
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=message_data["message"])
            ]

            response = llm(messages)
            equipment_data = parse_llm_equipment_response(response.content)

            # Send response back
            await websocket.send_json({
                "type": "llm_response",
                "response": response.content,
                "equipment_data": equipment_data,
                "timestamp": datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")


# ===== Run Server =====
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

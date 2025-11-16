from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid
import datetime
from ai_5 import app

app = FastAPI(title="Chemical Process Simulation API")

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite/React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Chat Models
class ChatMessage(BaseModel):
    text: str
    sender: str  # 'user' or 'ai'
    timestamp: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    timestamp: str


# In-memory chat storage (replace with database in production)
conversations: dict = {}


@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    """
    AI chat endpoint for process simulation assistance
    """
    messages = request.message.lower()
    result = app.invoke({'messages': messages})

    # Determine which messages are new (the LLM's response and tool executions)
    new_messages = result['messages'][len(messages):]

    # Update the overall message history with the results of the graph execution
    response ="hlo"# result['messages']

    # # Simple rule-based responses (replace with LLM integration)
    # if "temperature" in user_message or "temp" in user_message:
    #     response = "I can help you with temperature settings. For most reactors, operating temperatures range from 300-400K. What specific equipment are you working with?"
    #
    # elif "pressure" in user_message:
    #     response = "Pressure is crucial for process optimization. Typical operating pressures range from 1-10 atm depending on your process. Would you like me to calculate optimal pressure for your system?"
    #
    # elif "reactor" in user_message:
    #     response = "Reactors are key units in chemical processes. I can help you design a CSTR, PFR, or batch reactor. What type of reaction are you modeling?"
    #
    # elif "pump" in user_message:
    #     response = "Pumps are used to increase fluid pressure. I can calculate the required pump power based on your pressure requirements and flow rate. What are your specifications?"
    #
    # elif "distillation" in user_message or "column" in user_message:
    #     response = "Distillation columns separate mixtures based on boiling points. Key parameters include number of stages, reflux ratio, and feed location. What mixture are you separating?"
    #
    # elif "help" in user_message:
    #     response = "I can assist with:\n• Equipment sizing and selection\n• Process parameters (temperature, pressure, flow rates)\n• Thermodynamic calculations\n• Flow diagram creation\n• Simulation troubleshooting\n\nWhat would you like help with?"
    #
    # elif "simulate" in user_message or "run" in user_message:
    #     response = "To run a simulation:\n1. Go to the 'Flow Diagram' tab\n2. Add equipment from the palette\n3. Connect them with streams\n4. Set properties for each unit\n5. Click 'Run' button\n\nWould you like me to guide you through this?"
    #
    # else:
    #     response = f"I understand you're asking about: '{request.message}'. I'm here to help with chemical process simulation. Could you provide more details about what you need?"

    return ChatResponse(
        response=response,
        timestamp=datetime.now().isoformat()
    )


# Additional endpoints for chat history
@app.get("/api/chat/history/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        return {"messages": []}
    return {"messages": conversations[conversation_id]}


@app.post("/api/chat/clear/{conversation_id}")
async def clear_chat_history(conversation_id: str):
    """Clear conversation history"""
    if conversation_id in conversations:
        conversations[conversation_id] = []
    return {"status": "cleared"}


# Equipment Type Enum
class EquipmentType(str, Enum):
    FEED = "Feed"
    PRODUCT = "Product"
    HEATER = "Heater"
    COOLER = "Cooler"
    PUMP = "Pump"
    COMPRESSOR = "Compressor"
    EXPANDER = "Expander"
    HEAT_EXCHANGER = "HeatExchanger"
    REACTOR = "Reactor"
    FLASH = "Flash"
    TANK = "Tank"
    DISTILLATION_COLUMN = "DistillationColumn"
    MIXER = "Mixer"
    SPLITTER = "Splitter"


# Pydantic Models
class EquipmentProperties(BaseModel):
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    duty: Optional[float] = None
    stages: Optional[int] = None
    condenserType: Optional[str] = None
    reboilerType: Optional[str] = None
    refluxRatio: Optional[float] = None
    distillateRate: Optional[float] = None


class FlowsheetNode(BaseModel):
    id: str
    name: str
    type: EquipmentType
    x: float
    y: float
    properties: EquipmentProperties


class FlowsheetEdge(BaseModel):
    id: str
    from_node: str  # Changed from 'from' to avoid Python keyword
    to_node: str  # Changed from 'to' to avoid Python keyword


class FlowDiagramRequest(BaseModel):
    nodes: List[FlowsheetNode]
    edges: List[FlowsheetEdge]


class FlowDiagramResponse(BaseModel):
    nodes: List[FlowsheetNode]
    edges: List[FlowsheetEdge]
    validation_errors: List[str] = []


class SimulationResult(BaseModel):
    id: int
    parameter: str
    value: str
    status: str


class EquipmentInfoRequest(BaseModel):
    equipment_id: str
    equipment_type: EquipmentType
    properties: EquipmentProperties


class EquipmentInfoResponse(BaseModel):
    equipment_id: str
    equipment_type: EquipmentType
    calculated_properties: Dict[str, Any]
    warnings: List[str] = []


# In-memory storage (replace with database in production)
flow_diagrams: Dict[str, FlowDiagramResponse] = {}
simulation_results: Dict[str, List[SimulationResult]] = {}


# API Endpoints

@app.get("/")
async def root():
    return {"message": "Chemical Process Simulation API"}


@app.post("/api/flow-diagram/save")
async def save_flow_diagram(diagram: FlowDiagramRequest) -> Dict[str, str]:
    """
    Save flow diagram with nodes (equipment) and edges (connections)
    """
    diagram_id = str(uuid.uuid4())

    # Validate connections
    validation_errors = validate_connections(diagram.nodes, diagram.edges)

    # Store the diagram
    flow_diagrams[diagram_id] = FlowDiagramResponse(
        nodes=diagram.nodes,
        edges=diagram.edges,
        validation_errors=validation_errors
    )

    return {
        "diagram_id": diagram_id,
        "status": "saved" if not validation_errors else "saved_with_warnings",
        "message": f"Flow diagram saved with {len(diagram.nodes)} nodes and {len(diagram.edges)} edges"
    }


@app.get("/api/flow-diagram/{diagram_id}")
async def get_flow_diagram(diagram_id: str) -> FlowDiagramResponse:
    """
    Retrieve saved flow diagram
    """
    if diagram_id not in flow_diagrams:
        raise HTTPException(status_code=404, detail="Flow diagram not found")

    return flow_diagrams[diagram_id]


@app.post("/api/equipment/calculate")
async def calculate_equipment(request: EquipmentInfoRequest) -> EquipmentInfoResponse:
    """
    Process equipment data and calculate derived properties
    """
    warnings = []
    calculated_props = {}

    # Equipment-specific calculations
    if request.equipment_type == EquipmentType.PUMP:
        if request.properties.pressure:
            calculated_props["power_required"] = calculate_pump_power(
                request.properties.pressure
            )

    elif request.equipment_type == EquipmentType.HEATER:
        if request.properties.duty:
            calculated_props["heat_transfer_area"] = calculate_heat_area(
                request.properties.duty
            )

    elif request.equipment_type == EquipmentType.REACTOR:
        if request.properties.temperature and request.properties.pressure:
            calculated_props["conversion"] = calculate_reactor_conversion(
                request.properties.temperature,
                request.properties.pressure
            )

    elif request.equipment_type == EquipmentType.DISTILLATION_COLUMN:
        if request.properties.stages and request.properties.refluxRatio:
            calculated_props["minimum_reflux_ratio"] = calculate_min_reflux(
                request.properties.stages,
                request.properties.refluxRatio
            )
            if request.properties.refluxRatio < calculated_props["minimum_reflux_ratio"]:
                warnings.append("Reflux ratio below minimum - separation may be inadequate")

    return EquipmentInfoResponse(
        equipment_id=request.equipment_id,
        equipment_type=request.equipment_type,
        calculated_properties=calculated_props,
        warnings=warnings
    )


@app.post("/api/simulate/run")
async def run_simulation(diagram: FlowDiagramRequest) -> Dict[str, Any]:
    """
    Run simulation on the flow diagram and generate results
    """
    simulation_id = str(uuid.uuid4())

    # Validate diagram
    validation_errors = validate_connections(diagram.nodes, diagram.edges)

    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Diagram validation failed: {', '.join(validation_errors)}"
        )

    # Simulate each equipment
    results = []
    for node in diagram.nodes:
        equipment_results = simulate_equipment(node)
        results.extend(equipment_results)

    # Store results
    simulation_results[simulation_id] = results

    return {
        "simulation_id": simulation_id,
        "status": "completed",
        "results": results
    }


@app.get("/api/results/{simulation_id}")
async def get_simulation_results(simulation_id: str) -> List[SimulationResult]:
    """
    Retrieve simulation results as table data
    """
    if simulation_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Simulation results not found")

    return simulation_results[simulation_id]


@app.get("/api/equipment/info/{equipment_type}")
async def get_equipment_info(equipment_type: EquipmentType) -> Dict[str, Any]:
    """
    Get required input parameters for specific equipment type
    """
    equipment_requirements = {
        EquipmentType.PUMP: {
            "required_inputs": ["pressure"],
            "optional_inputs": ["efficiency"],
            "outputs": ["power_required", "head"]
        },
        EquipmentType.HEATER: {
            "required_inputs": ["duty"],
            "optional_inputs": ["temperature"],
            "outputs": ["heat_transfer_area", "outlet_temperature"]
        },
        EquipmentType.COOLER: {
            "required_inputs": ["duty"],
            "optional_inputs": ["temperature"],
            "outputs": ["cooling_water_required", "outlet_temperature"]
        },
        EquipmentType.REACTOR: {
            "required_inputs": ["temperature", "pressure"],
            "optional_inputs": ["volume", "residence_time"],
            "outputs": ["conversion", "heat_of_reaction", "product_composition"]
        },
        EquipmentType.DISTILLATION_COLUMN: {
            "required_inputs": ["stages", "refluxRatio", "pressure"],
            "optional_inputs": ["condenserType", "reboilerType"],
            "outputs": ["distillate_composition", "bottoms_composition", "reboiler_duty"]
        },
        EquipmentType.FLASH: {
            "required_inputs": ["temperature", "pressure"],
            "optional_inputs": [],
            "outputs": ["vapor_fraction", "liquid_composition", "vapor_composition"]
        },
        EquipmentType.TANK: {
            "required_inputs": ["temperature", "pressure"],
            "optional_inputs": ["volume"],
            "outputs": ["residence_time", "level"]
        },
    }

    return equipment_requirements.get(
        equipment_type,
        {"required_inputs": [], "optional_inputs": [], "outputs": []}
    )


# Helper Functions

def validate_connections(nodes: List[FlowsheetNode], edges: List[FlowsheetEdge]) -> List[str]:
    """Validate flow diagram connections based on equipment rules"""
    errors = []

    connection_rules = {
        EquipmentType.FEED: {"max_inputs": 0, "max_outputs": 1},
        EquipmentType.PRODUCT: {"max_inputs": 1, "max_outputs": 0},
        EquipmentType.HEATER: {"max_inputs": 1, "max_outputs": 1},
        EquipmentType.COOLER: {"max_inputs": 1, "max_outputs": 1},
        EquipmentType.PUMP: {"max_inputs": 1, "max_outputs": 1},
        EquipmentType.REACTOR: {"max_inputs": 1, "max_outputs": 2},
        EquipmentType.MIXER: {"max_inputs": float('inf'), "max_outputs": 1},
        EquipmentType.SPLITTER: {"max_inputs": 1, "max_outputs": float('inf')},
    }

    node_dict = {node.id: node for node in nodes}

    for node in nodes:
        inputs = [e for e in edges if e.to_node == node.id]
        outputs = [e for e in edges if e.from_node == node.id]

        rules = connection_rules.get(node.type, {"max_inputs": float('inf'), "max_outputs": float('inf')})

        if len(inputs) > rules["max_inputs"]:
            errors.append(f"{node.name} has too many input connections")

        if len(outputs) > rules["max_outputs"]:
            errors.append(f"{node.name} has too many output connections")

    return errors


def simulate_equipment(node: FlowsheetNode) -> List[SimulationResult]:
    """Simulate individual equipment and return results"""
    results = []
    result_id = 1

    if node.type == EquipmentType.REACTOR and node.properties.temperature:
        results.append(SimulationResult(
            id=result_id,
            parameter=f"{node.name} Temperature",
            value=f"{node.properties.temperature} K",
            status="Nominal"
        ))
        result_id += 1

        results.append(SimulationResult(
            id=result_id,
            parameter=f"{node.name} Conversion",
            value="85.3%",
            status="Excellent"
        ))

    elif node.type == EquipmentType.PUMP and node.properties.pressure:
        results.append(SimulationResult(
            id=result_id,
            parameter=f"{node.name} Outlet Pressure",
            value=f"{node.properties.pressure} atm",
            status="Nominal"
        ))

    return results


def calculate_pump_power(pressure: float) -> float:
    """Calculate pump power requirement"""
    return pressure * 0.75  # Simplified calculation


def calculate_heat_area(duty: float) -> float:
    """Calculate heat transfer area"""
    return duty / 500  # Simplified: assuming U*ΔT = 500


def calculate_reactor_conversion(temp: float, pressure: float) -> float:
    """Calculate reactor conversion"""
    return min(95.0, (temp / 350) * (pressure / 1.0) * 85)  # Simplified kinetics


def calculate_min_reflux(stages: int, reflux_ratio: float) -> float:
    """Calculate minimum reflux ratio"""
    return reflux_ratio * 0.6  # Simplified estimate


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

const API_BASE_URL = 'http://localhost:8000';

// Types
export interface FlowDiagramData {
  nodes: FlowsheetNode[];
  edges: FlowsheetEdge[];
}

export interface FlowsheetNode {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  properties: EquipmentProperties;
}

export interface FlowsheetEdge {
  id: string;
  from_node: string;
  to_node: string;
}

export interface EquipmentProperties {
  temperature?: number;
  pressure?: number;
  duty?: number;
  stages?: number;
  condenserType?: string;
  refluxRatio?: number;
  distillateRate?: number;
}

export interface SimulationResult {
  id: number;
  parameter: string;
  value: string;
  status: string;
}

// ... existing imports and interfaces ...

export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  timestamp: string;
}

// Chat API function
export const sendChatMessage = async (
  message: string,
  conversationHistory: ChatMessage[] = []
): Promise<ChatResponse> => {
  const response = await api.post('/api/chat', {
    message: message,
    conversation_history: conversationHistory.map(msg => ({
      text: msg.text,
      sender: msg.sender,
      timestamp: msg.timestamp.toISOString(),
    })),
  });
  return response.data;
};

// Get chat history
export const getChatHistory = async (conversationId: string) => {
  const response = await api.get(`/api/chat/history/${conversationId}`);
  return response.data;
};

// Clear chat history
export const clearChatHistory = async (conversationId: string) => {
  const response = await api.post(`/api/chat/clear/${conversationId}`);
  return response.data;
};


// Helper function for API requests
const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };
  
  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };
  
  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unknown error occurred');
  }
};

// API Functions

// Save flow diagram
export const saveFlowDiagram = async (diagramData: FlowDiagramData) => {
  return await apiRequest('/api/flow-diagram/save', {
    method: 'POST',
    body: JSON.stringify(diagramData),
  });
};

// Get flow diagram
export const getFlowDiagram = async (diagramId: string) => {
  return await apiRequest(`/api/flow-diagram/${diagramId}`, {
    method: 'GET',
  });
};

// Calculate equipment properties
export const calculateEquipment = async (
  equipmentId: string,
  equipmentType: string,
  properties: EquipmentProperties
) => {
  return await apiRequest('/api/equipment/calculate', {
    method: 'POST',
    body: JSON.stringify({
      equipment_id: equipmentId,
      equipment_type: equipmentType,
      properties: properties,
    }),
  });
};

// Run simulation
export const runSimulation = async (diagramData: FlowDiagramData) => {
  return await apiRequest('/api/simulate/run', {
    method: 'POST',
    body: JSON.stringify(diagramData),
  });
};

// Get simulation results
export const getSimulationResults = async (simulationId: string): Promise<SimulationResult[]> => {
  return await apiRequest(`/api/results/${simulationId}`, {
    method: 'GET',
  });
};

// Get equipment info (required inputs/outputs)
export const getEquipmentInfo = async (equipmentType: string) => {
  return await apiRequest(`/api/equipment/info/${equipmentType}`, {
    method: 'GET',
  });
};

export default {
  saveFlowDiagram,
  getFlowDiagram,
  calculateEquipment,
  runSimulation,
  getSimulationResults,
  getEquipmentInfo,
};

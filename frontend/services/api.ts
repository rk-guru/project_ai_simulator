import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interfaces
export interface ChatResponse {
  message: string;
  pdf_filename?: string;
  has_pdf_context?: boolean;
  timestamp: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  file_id: number;
  filename: string;
}

export interface SimulationResponse {
  status: string;
  message: string;
  results: any[];
}

// Chat API
export const sendChatMessage = async (message: string, projectId: string): Promise<ChatResponse> => {
  try {
    const response: AxiosResponse<ChatResponse> = await apiClient.post('/chat', {
      message: message,
      project_id: projectId,
      timestamp: new Date().toISOString(),
    });
    return response.data;
  } catch (error: any) {
    console.error('Chat API Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to send chat message');
  }
};

// Get chat history
export const getChatHistory = async (projectId: string) => {
  try {
    const response = await apiClient.get(`/chat/history/${projectId}`);
    return response.data;
  } catch (error: any) {
    console.error('Get Chat History Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to get chat history');
  }
};

// Upload PDF
export const uploadPDF = async (file: File, projectId: string): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);

    const response: AxiosResponse<UploadResponse> = await axios.post(
      `${API_BASE_URL}/upload-pdf`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  } catch (error: any) {
    console.error('Upload PDF Error:', error);
    throw new Error(error.response?.data?.error || 'Failed to upload PDF');
  }
};

// Get project files
export const getProjectFiles = async (projectId: string) => {
  try {
    const response = await apiClient.get(`/files/${projectId}`);
    return response.data;
  } catch (error: any) {
    console.error('Get Files Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to get files');
  }
};

// Project Management
export const createProject = async (projectId: string, projectName: string) => {
  try {
    const response = await apiClient.post('/projects', {
      id: projectId,
      name: projectName,
    });
    return response.data;
  } catch (error: any) {
    console.error('Create Project Error:', error);
    throw new Error(error.response?.data?.error || 'Failed to create project');
  }
};

export const getProjects = async () => {
  try {
    const response = await apiClient.get('/projects');
    return response.data;
  } catch (error: any) {
    console.error('Get Projects Error:', error);
    throw new Error(error.response?.data?.error || 'Failed to get projects');
  }
};

export const deleteProject = async (projectId: string) => {
  try {
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response.data;
  } catch (error: any) {
    console.error('Delete Project Error:', error);
    throw new Error(error.response?.data?.error || 'Failed to delete project');
  }
};

// Simulation APIs
export const generateFlowDiagram = async (nodes: any[], edges: any[]): Promise<any> => {
  try {
    const response = await apiClient.post('/generate-flowsheet', {
      nodes,
      edges,
    });
    return response.data;
  } catch (error: any) {
    console.error('Generate Flow Diagram Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to generate flow diagram');
  }
};

export const runSimulation = async (data: any): Promise<SimulationResponse> => {
  try {
    const response: AxiosResponse<SimulationResponse> = await apiClient.post('/run-simulation', data);
    return response.data;
  } catch (error: any) {
    console.error('Run Simulation Error:', error);
    throw new Error(error.response?.data?.message || 'Failed to run simulation');
  }
};

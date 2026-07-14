// src/services/api.ts
import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export const api = {
  // Create new project
  async createProject(name: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/project/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create project: ${response.statusText}`);
    }

    return response.json();
  },

  // Save project by ID
  async saveProject(projectId: string, data: Partial<Project>): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}/save`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to save project: ${response.statusText}`);
    }

    return response.json();
  },

  // Get project by ID
  async getProject(projectId: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch project: ${response.statusText}`);
    }

    return response.json();
  },

  // Get all projects
  async getAllProjects(): Promise<Array<{ id: string; name: string; created_at: string; updated_at: string; node_count: number; edge_count: number }>> {
    const response = await fetch(`${API_BASE_URL}/api/projects`);

    if (!response.ok) {
      throw new Error(`Failed to fetch projects: ${response.statusText}`);
    }

    return response.json();
  },

  // Delete project by ID
  async deleteProject(projectId: string): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete project: ${response.statusText}`);
    }

    return response.json();
  },

  // Upload PDF for specific project
  async uploadPDF(projectId: string, file: File): Promise<{ status: string; parsed_data: any; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}/upload_pdf`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to upload PDF: ${response.statusText}`);
    }

    return response.json();
  },

  // Run simulation for specific project
  async runSimulation(projectId: string, data: { Equipment_list: Record<string, string>; Connection: any[] }): Promise<{ status: string; results: any[] }> {
    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}/simulation/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Simulation failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Export project data
  async exportProject(projectId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/project/${projectId}/export`);

    if (!response.ok) {
      throw new Error(`Failed to export project: ${response.statusText}`);
    }

    return response.json();
  }
};
